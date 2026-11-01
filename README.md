# Daily NSE Stock Scanner — no AI

Start with **START_HERE.md**. You do not need Python installed on your computer.

This package runs on GitHub Actions and sends a daily Telegram shortlist. It uses
four selected, unchanged PKScreener screening functions with a small adapter;
it is not the complete upstream PKScreener application. The upstream functions
are pinned to commit `ab4212355e2442e7c8f5430d53fa3f56ea5af3b8` and retained under
its MIT licence. Calculations use TA-Lib. No AI package, AI subscription, broker
account or automatic trading is involved.

## Files

- `scanner.py`: download, validate, calculate and send results.
- `pk_rules.py`: selected upstream screening functions and adapter.
- `config.json`: editable thresholds.
- `requirements.txt`: four pinned Python libraries.
- `workflow-template.yml`: copy its text to `.github/workflows/daily-scan.yml`.
- `START_HERE.md`: complete browser-based instructions.
- `PKSCREENER_LICENSE.txt`: upstream copyright and licence.
- `VALIDATION.md`: what was tested and what still requires your account.

## Default rules

All of these must pass:

1. PKScreener's bullish breakout check on 21 bars (latest plus 20 previous).
2. Latest close strictly above the prior 20-session highest high.
3. Latest volume at least 1.5 times the previous 20-session average, and also
   pass PKScreener's volume check (whose moving average includes the latest bar).
4. Exact RSI(14) between 55 and 75, inclusive, and PKScreener's RSI check.
5. Close > EMA20 > EMA50; close > EMA200.
6. Average previous-20-session close x volume / 10,000,000 >= 10 crore.
   This is a traded-value proxy, not exchange-reported turnover.
7. At least two of these additional confirmations:
   - RSI rising within the permitted range.
   - ADX(14) >25 and +DI > -DI.
   - Close above upper Bollinger Band after recent contraction: minimum
     bandwidth in the previous 10 sessions below the 20th percentile of the
     previous 120 sessions; bands are 20 periods and 2 standard deviations.
   - Latest COMPLETED weekly close above a rising weekly EMA20.

A recent 20/50 EMA bullish crossover is shown as extra information; it is not
mandatory. Fibonacci is not included in this breakout strategy. It needs a
separate, explicitly defined pullback strategy. No backtested profitability
claim is made.

## Data and operation

- Universe: current Nifty 500 constituent CSV; it can contain more than 500
  symbols around corporate actions. Only matching official NSE EQ rows qualify.
- Latest OHLCV: official NSE final UDiFF bhavcopy for the requested date.
- History: Yahoo Finance, two years, adjusted OHLC normalised to current price
  units. Volume comes from the provider, with latest volume replaced by NSE.
- At least 210 usable daily bars are required. New listings can be excluded.
- At least 90% of eligible histories must be usable, counting genuine short
  histories as known exclusions. Otherwise no normal shortlist is sent.
- Requests retry automatically. If the official file is unavailable, the run
  fails clearly instead of reporting no matches or using an old date silently.
- Exchange holidays can cause this conservative unavailable-data message.
- Scheduled at 18:15 and 19:15 IST weekdays. A date-specific success cache
  normally suppresses the second alert when the first succeeds. Cache eviction
  or message-delivery uncertainty can occasionally produce duplicate alerts.
- Manual runs deliberately resend results. Matching stocks are reported every
  day; this version does not remove stocks mentioned on previous dates.
- CSVs are saved as GitHub artifacts for 7 days, not committed into the repo.
- Only Telegram bot token and private chat ID are required secrets.
- A public repository exposes source code and its Actions logs/results. It must
  not contain personal portfolios, credentials or confidential information.

Free data services can block cloud IP addresses or change response formats.
This must be tested on your GitHub account. Hosting is not a guarantee that
market data will always be accessible.

## Local command, if ever needed

Python 3.12:

```bash
python -m pip install -r requirements.txt
python scanner.py --dry-run
```

Without `--dry-run`, the script expects `TELEGRAM_BOT_TOKEN` and
`TELEGRAM_CHAT_ID` in its environment and sends alerts. `--date YYYY-MM-DD`
selects an earlier trading date within available history. `--force` resends even
if that date has a local success marker. Do not use dates in the future.
