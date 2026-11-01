"""Rule-based daily NSE breakout scan. No AI, broker login or trade execution."""
import argparse
import concurrent.futures
import datetime as dt
import io
import json
import os
from pathlib import Path
import time
from urllib.parse import quote
from zoneinfo import ZoneInfo
import zipfile

import numpy as np
import pandas as pd
import requests
import talib
from pk_rules import PKRules

ROOT = Path(__file__).resolve().parent
IST = ZoneInfo('Asia/Kolkata')
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'}


def download(url, attempts=3, timeout=30):
    for attempt in range(attempts):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            if attempt + 1 == attempts:
                # Do not include URLs or credentials in an error message.
                raise RuntimeError('Data download failed after retries') from None
            time.sleep(3 * (attempt + 1))


def telegram(method, payload):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    if not token:
        raise RuntimeError('Add the TELEGRAM_BOT_TOKEN repository secret')
    try:
        r = requests.post(f'https://api.telegram.org/bot{token}/{method}',
                          json=payload, timeout=30)
        obj = r.json()
        if not r.ok or not obj.get('ok'):
            raise ValueError()
        return obj['result']
    except Exception:
        raise RuntimeError('Telegram request failed; check your token, chat ID and whether you pressed Start') from None


def send_message(text, chat_id=None):
    chat = chat_id or os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not chat:
        raise RuntimeError('Add the TELEGRAM_CHAT_ID repository secret')
    for start in range(0, len(text), 3500):
        if start:
            time.sleep(1.1)
        telegram('sendMessage', {'chat_id': chat, 'text': text[start:start+3500],
                                'link_preview_options': {'is_disabled': True}})


def setup_telegram():
    updates = telegram('getUpdates', {'timeout': 0, 'limit': 100})
    chats = {u['message']['chat']['id'] for u in updates
             if u.get('message', {}).get('chat', {}).get('type') == 'private'}
    if len(chats) != 1:
        raise RuntimeError('Send /start to your NEW bot now, then rerun setup. Setup requires exactly one private chat in its pending updates. Use a dedicated new bot.')
    chat = chats.pop()
    send_message(f'Your stock scanner connection works.\n\nYour chat ID is:\n{chat}\n\nIn GitHub, add a repository secret named TELEGRAM_CHAT_ID with that number. Then run the workflow in scan mode. This confirms the connection only. Add the second secret so daily scans can deliver results.', chat)
    print('Telegram setup message delivered. Read your chat ID inside Telegram; it is not printed in public logs.')


def target_date(explicit=None):
    now = dt.datetime.now(IST)
    if explicit:
        day = dt.date.fromisoformat(explicit)
        if day > now.date():
            raise ValueError('The scan date cannot be in the future')
        return day
    day = now.date()
    if now.hour < 18:
        day -= dt.timedelta(days=1)
    while day.weekday() > 4:
        day -= dt.timedelta(days=1)
    return day


def parse_market_caps(blob, day, minimum_crore):
    """NSE PR archive mcap file is in RUPEES, not crore. Filter strictly > threshold."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = next((n for n in z.namelist() if Path(n).name.lower() == f'mcap{day:%d%m%Y}.csv'), None)
        if name is None:
            raise ValueError('NSE PR archive has no market-cap file for the target date')
        caps = pd.read_csv(io.BytesIO(z.read(name)))
    caps.columns = caps.columns.str.strip()
    required = {'Trade Date','Symbol','Series','Category','Market Cap(Rs.)'}
    if not required.issubset(caps.columns):
        raise ValueError('Unexpected NSE market-cap file columns')
    dates = pd.to_datetime(caps['Trade Date'].astype(str).str.strip(), format='%d %b %Y', errors='coerce')
    if dates.isna().any() or not dates.dt.date.eq(day).all():
        raise ValueError('NSE market-cap file date does not match target date')
    for col in ['Symbol','Series','Category']:
        caps[col] = caps[col].fillna('').astype(str).str.strip()
    # Listed normal-equity companies. Permitted-only, SME and other series are
    # outside this version's explicitly defined universe.
    caps = caps[caps.Series.eq('EQ') & caps.Category.eq('Listed')].copy()
    if caps.empty or caps.Symbol.duplicated().any():
        raise ValueError('Empty or duplicate listed-EQ market-cap universe')
    rupees = pd.to_numeric(caps['Market Cap(Rs.)'].astype(str).str.replace(',','',regex=False),errors='coerce')
    caps['market_cap_crore'] = rupees / 10_000_000
    meta = {'universe':'NSE-listed EQ shares','market_cap_date':str(day),
            'minimum_market_cap_crore':minimum_crore,'market_cap_rule':'strictly greater than',
            'listed_EQ_in_report':len(caps),
            'missing_or_invalid_market_cap':int((caps.market_cap_crore.isna() | caps.market_cap_crore.le(0)).sum()),
            'at_or_below_threshold':int(caps.market_cap_crore.le(minimum_crore).sum())}
    eligible = caps[caps.market_cap_crore.gt(minimum_crore)].copy()
    if eligible.empty:
        raise ValueError('No companies passed the market-cap universe filter; scan stopped')
    meta['above_market_cap_threshold'] = len(eligible)
    return eligible.set_index('Symbol'), meta


def load_inputs(day, offline=None):
    cfg = json.loads((ROOT/'config.json').read_text())
    threshold = float(cfg.get('minimum_market_cap_crore',500))
    if threshold <= 0:
        raise ValueError('minimum_market_cap_crore must be positive')
    if offline:
        folder = Path(offline)
        bhav = pd.read_csv(folder / f'nse-bhav-{day:%Y%m%d}.csv')
        blob = (folder / f'nse-pr-{day:%Y%m%d}.zip').read_bytes()
    else:
        url = f'https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip'
        try:
            data = download(url,attempts=4)
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                name = next(n for n in z.namelist() if n.lower().endswith('.csv'))
                bhav = pd.read_csv(io.BytesIO(z.read(name)))
            pr_url = f'https://nsearchives.nseindia.com/archives/equities/bhavcopy/pr/PR{day:%d%m%y}.zip'
            blob = download(pr_url,attempts=4)
        except Exception:
            raise RuntimeError(f'No usable official NSE final-price and market-cap files for {day}. This can be a holiday, publication delay or blocked connection. No stale-date or unfiltered-universe scan was substituted. Retry later.') from None
    required = {'TradDt','TckrSymb','SctySrs','OpnPric','HghPric','LwPric','ClsPric','TtlTradgVol'}
    if not required.issubset(bhav.columns) or not bhav.TradDt.eq(str(day)).all():
        raise ValueError('NSE final-price file columns or dates failed validation')
    caps,meta = parse_market_caps(blob,day,threshold)
    bhav = bhav[bhav.SctySrs.eq('EQ')].set_index('TckrSymb')
    if bhav.index.duplicated().any():
        raise ValueError('Duplicate NSE EQ rows; scan stopped')
    bhav = bhav.join(caps[['market_cap_crore']],how='left')
    bhav.attrs['universe_metadata'] = meta
    return caps.index.tolist(), bhav


def get_history(symbol, offline=None):
    if offline:
        return json.loads((Path(offline)/'market-cache'/f'{symbol}.json').read_text())
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol + ".NS", safe="")}?range=2y&interval=1d'
    obj = json.loads(download(url))
    result = obj['chart']['result'][0]
    if not result.get('timestamp'):
        raise ValueError('No daily candles')
    return result


def calculate(symbol, obj, official, day, cfg):
    index = pd.to_datetime(obj['timestamp'], unit='s', utc=True).tz_convert(IST).normalize().tz_localize(None)
    raw = pd.DataFrame(obj['indicators']['quote'][0], index=index)
    raw = raw[~raw.index.duplicated(keep='last')].sort_index()
    raw = raw.loc[:str(day)]
    if raw.empty:
        raise ValueError('No history through target date')
    current = pd.Timestamp(day)
    # A missing latest candle can be supplied by the official NSE final file.
    for key, col in [('open','OpnPric'),('high','HghPric'),('low','LwPric'),('close','ClsPric'),('volume','TtlTradgVol')]:
        raw.loc[current,key] = float(official[col])
    adj_array = obj['indicators'].get('adjclose', [{}])[0].get('adjclose')
    if adj_array is None:
        raise ValueError('Adjusted close history unavailable')
    adj = pd.Series(adj_array, index=index)
    adj = adj[~adj.index.duplicated(keep='last')].sort_index().loc[:str(day)]
    # Normalise historic adjusted OHLC to target-date price units.
    # For an explicitly older date, Yahoo already knows later dividends: preserve
    # its adjustment ratio when available; use ratio 1 only for its latest candle.
    existing_ratio = float(adj.get(current, np.nan)) / float(raw.loc[current,'close'])
    last_yahoo_day = index.max()
    if current == last_yahoo_day or not np.isfinite(existing_ratio):
        if current < last_yahoo_day and not np.isfinite(existing_ratio):
            raise ValueError('Cannot safely normalise adjusted history for an older date')
        adj.loc[current] = float(raw.loc[current,'close'])
    raw = raw.dropna(subset=['open','high','low','close','volume'])
    if len(raw) < cfg['min_daily_bars']:
        return None, f'insufficient history ({len(raw)} bars)'
    if not (raw.close.gt(0).all() and raw.volume.ge(0).all()):
        raise ValueError('Invalid price or volume')
    factor = adj.reindex(raw.index) / raw.close
    if factor.isna().any() or (factor<=0).any():
        raise ValueError('Incomplete adjusted history')
    factor /= factor.iloc[-1]
    df = raw.copy()
    for col in ['open','high','low','close']:
        df[col] *= factor
    # Ignore fully empty exchange-holiday placeholders, but reject partially
    # missing recent candles rather than silently shortening the lookback.
    earlier = pd.DataFrame(obj['indicators']['quote'][0], index=index).loc[:str(day)]
    earlier = earlier[~earlier.index.duplicated(keep='last')].iloc[:-1]
    partially_missing = earlier.isna().any(axis=1) & ~earlier.isna().all(axis=1)
    if partially_missing.tail(210).any():
        raise ValueError('Partly missing recent history')
    c,h,l,v = df.close,df.high,df.low,df.volume.astype(float)
    for period in [20,50,200]:
        df[f'ema{period}'] = talib.EMA(c,period)
    df['RSI'] = talib.RSI(c,14)
    df['VolMA'] = talib.SMA(v,20)
    pk = PKRules(); screen = {}; saved = {}
    desc = df.iloc[::-1]
    pk_bo = pk.findBreakoutValue(desc.head(21),screen,saved,20,alreadyBrokenout=True)
    pk_volume = pk.validateVolume(desc,screen,saved,cfg['volume_multiple'],10000)[0]
    pk_rsi = pk.validateRSI(desc,screen,saved,cfg['rsi_min'],cfg['rsi_max'])
    latest = df.iloc[-1]
    level = float(h.iloc[-21:-1].max())
    vm = float(v.iloc[-1]/v.iloc[-21:-1].mean())
    cash = float((c*v).iloc[-21:-1].mean()/1e7)
    trend = bool(latest.close>latest.ema20>latest.ema50 and latest.close>latest.ema200)
    rsi = float(latest.RSI)
    rsi_range = cfg['rsi_min']<=rsi<=cfg['rsi_max']
    rsi_rising = bool(rsi_range and rsi>df.RSI.iloc[-2])
    adx = float(talib.ADX(h,l,c,14).iloc[-1])
    adx_ok = bool(adx>cfg['adx_threshold'] and talib.PLUS_DI(h,l,c,14).iloc[-1]>talib.MINUS_DI(h,l,c,14).iloc[-1])
    upper,mid,lower = talib.BBANDS(c,20,2,2)
    width = (upper-lower)/mid
    squeeze = bool(width.iloc[-11:-1].min()<width.iloc[-121:-1].quantile(.2))
    bb_ok = bool(c.iloc[-1]>upper.iloc[-1] and squeeze)
    # W-FRI creates a future Friday label during Mon-Thu. Discard that partial week.
    weekly = c.resample('W-FRI').last().dropna()
    weekly = weekly[weekly.index<=current]
    we = talib.EMA(weekly,20)
    weekly_ok = bool(len(we)>21 and weekly.iloc[-1]>we.iloc[-1]>we.iloc[-2])
    confirmations = sum([rsi_rising,adx_ok,bb_ok,weekly_ok])
    crossed = ((df.ema20>df.ema50)&(df.ema20.shift()<=df.ema50.shift())).iloc[-6:].any()
    passed = bool(pk_bo and pk_volume and pk_rsi and rsi_range and
                  latest.close>level and vm>=cfg['volume_multiple'] and trend and
                  cash>=cfg['min_average_traded_value_crore'] and
                  confirmations>=cfg['minimum_additional_confirmations'])
    return {'symbol':symbol,'date':str(day),'market_cap_crore':round(float(official['market_cap_crore']),2),'close':round(float(latest.close),2),
            'breakout_level':round(level,2),'volume_multiple':round(vm,2),
            'PK_volume_multiple':saved.get('volume'),'RSI14':round(rsi,2),'ADX14':round(adx,2),
            'ema20':round(float(latest.ema20),2),'ema50':round(float(latest.ema50),2),
            'ema200':round(float(latest.ema200),2),'average_traded_value_crore':round(cash,2),
            'PK_breakout':bool(pk_bo),'PK_volume':bool(pk_volume),'PK_RSI':bool(pk_rsi),
            'uptrend':trend,'RSI_rising':rsi_rising,'ADX_confirmation':adx_ok,
            'Bollinger_squeeze_breakout':bb_ok,'completed_week_confirmation':weekly_ok,
            'recent_EMA_crossover':bool(crossed),'confirmations':confirmations,'qualified':passed,
            'chart':f'https://www.tradingview.com/chart/?symbol=NSE%3A{quote(symbol,safe="")}'}, None


def write_outputs(rows, issues, meta):
    out = ROOT/'output'; out.mkdir(exist_ok=True)
    all_rows = pd.DataFrame(rows)
    selected = all_rows[all_rows.qualified].sort_values(['confirmations','volume_multiple'],ascending=False) if not all_rows.empty else pd.DataFrame()
    all_rows.to_csv(out/'all-screened.csv',index=False)
    selected.to_csv(out/'qualified.csv',index=False)
    pd.DataFrame(issues,columns=['symbol','reason']).to_csv(out/'excluded.csv',index=False)
    (out/'run-summary.json').write_text(json.dumps(meta,indent=2))
    return selected


def scan(args):
    cfg = json.loads((ROOT/'config.json').read_text())
    day = target_date(args.date)
    state = ROOT/'.scan-state'/f'{day}.success'
    if state.exists() and not args.force:
        print(f'{day} already completed successfully. No duplicate scheduled notification.')
        return
    if not args.dry_run and (not os.environ.get('TELEGRAM_BOT_TOKEN') or not os.environ.get('TELEGRAM_CHAT_ID')):
        raise RuntimeError('First add both Telegram repository secrets and run setup mode')
    symbols,bhav = load_inputs(day,args.offline)
    eligible = [s for s in symbols if s in bhav.index]
    issues = [(s,'not in official NSE EQ series for this date') for s in symbols if s not in bhav.index]
    rows=[];failed=0;ok_downloads=0
    def fetch(sym):
        try:return sym,get_history(sym,args.offline),None
        except Exception as e:return sym,None,type(e).__name__
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg['download_workers']) as pool:
        for count,(sym,obj,error) in enumerate(pool.map(fetch,eligible),1):
            if error:
                failed+=1;issues.append((sym,'history download unavailable'));continue
            ok_downloads+=1
            try:
                row,reason=calculate(sym,obj,bhav.loc[sym],day,cfg)
                if row:rows.append(row)
                else:issues.append((sym,reason))
            except Exception as e:
                failed+=1;issues.append((sym,str(e)))
            if count%50==0: print(f'Processed {count}/{len(eligible)} eligible symbols',flush=True)
    # Valid historical calculations plus genuine short-history exclusions count
    # as coverage; network and malformed-data errors do not.
    short=sum('insufficient history' in reason for _,reason in issues)
    coverage=(len(rows)+short)/max(len(eligible),1)
    meta={'date':str(day),'universe':len(symbols),'eligible_EQ':len(eligible),'screened':len(rows),
          'excluded':len(issues),'coverage':round(coverage,4),'source_latest':'NSE final UDiFF bhavcopy',
          'source_history':'Yahoo Finance adjusted OHLC','universe_filter':bhav.attrs['universe_metadata'],'PKScreener_commit':'ab4212355e2442e7c8f5430d53fa3f56ea5af3b8',
          'rules':cfg}
    selected=write_outputs(rows,issues,meta)
    if coverage<cfg['minimum_history_download_coverage']:
        raise RuntimeError(f'Incomplete scan: only {coverage:.0%} of eligible histories usable. Partial output saved; no normal shortlist sent. Retry later.')
    lines=[f'NSE technical scan — {day}',f"Universe: NSE-listed EQ shares | Market cap > Rs {cfg.get('minimum_market_cap_crore',500):g} crore",f'Eligible above cap: {len(symbols)}',f'Screened: {len(rows)} | Excluded: {len(issues)} | Qualified: {len(selected)}',
           'PKScreener-based rules; daily closing data. No AI.','']
    if selected.empty:lines.append('No stocks qualified under the configured rules.')
    else:
        limit = int(cfg.get('telegram_max_stocks',0))
        display = selected if limit <= 0 else selected.head(limit)
        for row in display.to_dict('records'):
            flags=[]
            if row['Bollinger_squeeze_breakout']:flags.append('Bollinger squeeze')
            if row['ADX_confirmation']:flags.append('ADX confirmation')
            if row['recent_EMA_crossover']:flags.append('recent EMA cross')
            lines += [f"{row['symbol']}: Rs {row['close']:,.2f} | Breakout Rs {row['breakout_level']:,.2f}",
                      f"Market cap Rs {row['market_cap_crore']:,.0f} crore | Volume {row['volume_multiple']:.2f}x | RSI {row['RSI14']:.1f} | ADX {row['ADX14']:.1f}",
                      'Extras: '+(', '.join(flags) if flags else 'see CSV for confirmations'),row['chart'],'']
        if limit > 0 and len(selected)>limit:lines.append('More matches are available in the GitHub qualified.csv artifact.')
    lines+=['All matching stocks are reported daily; this version does not suppress a stock across different dates.',
            'Chart-review candidates, not automatic buy orders.']
    message='\n'.join(lines)
    print(message)
    if not args.dry_run:
        send_message(message)
        state.parent.mkdir(exist_ok=True);state.write_text('completed')
    print('Scan completed.' + (' Telegram was not contacted (dry run).' if args.dry_run else ' Telegram delivery confirmed.'))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--date',help='Optional YYYY-MM-DD trading date')
    p.add_argument('--setup-telegram',action='store_true')
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--force',action='store_true')
    p.add_argument('--offline',help='Internal validation directory containing saved market inputs')
    args=p.parse_args()
    try:
        if args.setup_telegram:setup_telegram()
        else:scan(args)
    except Exception as exc:
        message='Stock scanner did not complete: '+str(exc)
        print(message)
        if not args.dry_run and not args.setup_telegram and os.environ.get('TELEGRAM_CHAT_ID'):
            try:send_message(message)
            except Exception:print('Failure notification could not be delivered; check GitHub Actions logs.')
        raise SystemExit(1) from None

if __name__=='__main__':main()
