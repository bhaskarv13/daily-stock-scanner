# Set up your free daily stock scanner

Prepared 31 October 2026. Estimated setup: 25–45 minutes plus download time.
You need a computer browser, a GitHub account and Telegram on your phone.
You do not need to install Python, Git or an AI application on your computer.

## 1. Extract this package

Download `Daily_Stock_Scanner_Setup.zip`. On Windows, right-click it and choose
**Extract All**. On Mac, double-click it. Open the extracted folder containing
`scanner.py`, `pk_rules.py`, `config.json`, `requirements.txt` and the other files.
Do not upload the ZIP itself to GitHub: GitHub cannot run the files inside it.

## 2. Create a free GitHub account and repository

1. Visit https://github.com and sign up, or sign in.
2. Verify your email if requested.
3. Click **+** near the top-right, then **New repository**. Alternatively open
   https://github.com/new.
4. Repository name: `daily-stock-scanner`.
5. Choose **Public**. Standard GitHub-hosted Actions runners are free for public
   repositories. Private repositories have an included usage allowance instead.
6. Tick **Add a README file**.
7. Click **Create repository**.

A repository is simply your online project folder. Public means other people can
see its code and run logs. Put no passwords, personal holdings or private data in
its files. Telegram credentials will go into GitHub Secrets in step 5.

## 3. Upload the project files

1. In the repository's **Code** tab, click **Add file → Upload files**.
2. Drag the extracted FILES into the upload area. Upload the contents of the
   folder, not an extra enclosing folder and not the ZIP.
3. Scroll down. Use the commit message `Add daily stock scanner`.
4. Choose **Commit directly to the main branch**, if shown.
5. Click **Commit changes**. Replacing the initial blank README is fine.
6. Confirm `scanner.py`, `pk_rules.py`, `config.json`, `requirements.txt` and
   `workflow-template.yml` appear directly on the Code page.

A commit means save this version of your files. You have not activated the
schedule yet; the template needs to be installed in step 6.

## 4. Create your own Telegram bot

1. Open the official bot https://t.me/BotFather in Telegram.
2. Press **Start**, then send `/newbot`.
3. Give the bot a display name, such as `VSR Stock Alerts`.
4. Choose a unique username ending in `bot`, such as
   `vsr_stock_alerts_123_bot`. Choose a different suffix if it is taken.
5. BotFather replies with a **bot token**, a long password-like string containing
   a colon. Keep it private. Do not paste it into code, chat messages to others,
   screenshots or public GitHub files.
6. Tap the link to YOUR new bot in BotFather's reply.
7. Press **Start** and send `/start` to your new bot. Keep the bot unshared during
   setup so the connection test can identify your own conversation unambiguously.

This is an ordinary Telegram automation bot. It does not use AI and does not
place stock trades. Creating a bot does not let it message you until you start it.

## 5. Save the bot token in GitHub Secrets

1. Return to your GitHub repository.
2. Click **Settings** (repository settings, not your profile settings).
3. In the left sidebar choose **Secrets and variables → Actions**.
4. Select **Secrets** if there are Secrets and Variables tabs.
5. Click **New repository secret**.
6. Name: `TELEGRAM_BOT_TOKEN` (exact spelling).
7. Secret: paste the token from BotFather.
8. Click **Add secret**.

GitHub hides secret values after saving. This is normal. You can replace the value
later. We will add the second secret, your chat ID, after the connection test.

## 6. Install the daily workflow

A workflow is the instruction sheet that tells GitHub when and how to run Python.

1. Return to the repository's **Code** tab.
2. Open `workflow-template.yml`.
3. Click **Raw** or copy its complete text using the file's copy button. You can
   alternatively open the downloaded template in Notepad or TextEdit as plain text.
4. Return to **Code → Add file → Create new file**.
5. In the filename box type EXACTLY:
   `.github/workflows/daily-scan.yml`
6. Paste the entire template into the editor without adding Markdown backticks.
7. Click **Commit changes**, then confirm saving to `main`.
8. Open **Actions**. If GitHub asks you to enable workflows, enable them.

The Code page should now have a `.github` folder containing `workflows`, which
contains `daily-scan.yml`. A root-level `workflow-template.yml` alone does not run.
The workflow is scheduled now, but successful daily delivery needs the chat-ID
secret from the next step. Finish setup before expecting daily results.

## 7. Run the Telegram connection test and obtain your chat ID

1. Go to **Actions** in your repository.
2. Select **Daily Stock Scanner** in the left sidebar.
3. Click **Run workflow**. Keep branch **main**.
4. Change **mode** to `setup-telegram`.
5. Leave **scan_date** blank.
6. Click the green **Run workflow** button.
7. Wait for the run to appear, then click it. The first run installs libraries and
   can take several minutes. A green tick means success.
8. Open your bot chat in Telegram. You should receive a connection-test message
   containing your numeric **chat ID**.
9. Back in GitHub, go to **Settings → Secrets and variables → Actions → New
   repository secret**.
10. Name: `TELEGRAM_CHAT_ID`.
11. Secret: paste only the number your bot sent. Click **Add secret**.

You should now have TWO repository secrets. Do not confuse the bot token with the
chat ID. Your own chat ID is sent privately to Telegram, not printed in public
Actions logs. Use a new dedicated bot; setup refuses to guess between multiple
private chats. If the test says it found no conversation, send `/start` to YOUR
bot again and rerun setup immediately.

## 8. Run your first stock scan

1. Go to **Actions → Daily Stock Scanner → Run workflow**.
2. Keep branch **main**.
3. Select **mode = scan**.
4. Leave **scan_date** blank. The program chooses the latest completed weekday;
   before 6 p.m. IST it uses the previous weekday. On a weekend it uses Friday.
   This is not a full exchange-holiday calendar.
5. Click **Run workflow** and open the new run.
6. Wait until completion. The full scan may take roughly 10–30 minutes, depending
   on market-data downloads. The job has a 40-minute safety limit.
7. Check Telegram for the dated shortlist, screened count and excluded count.
8. If no stocks pass, you should get an explicit **No stocks qualified** message.

If the selected weekday was an exchange holiday, the scanner reports that the
NSE final file is unavailable. It does not silently use an older date. Rerun
manually and enter the actual previous trading date in `YYYY-MM-DD` form.
For example, the historical sample in this package uses `2026-10-30`.

## 9. View and download all results

1. Open the completed run in **Actions**.
2. Scroll down to **Artifacts**.
3. Download the `stock-scan-...` artifact and extract it.
4. Open `qualified.csv` in Excel for the matching stocks.
5. `all-screened.csv` contains all calculated stock results.
6. `excluded.csv` explains unavailable histories, short histories and exclusions.
7. `run-summary.json` records the date, coverage and thresholds.

Artifacts are retained for seven days; download files you want to keep longer.
A successful second scheduled run may skip because the first already delivered,
so that skipped run may have no new artifact. Open the first run for the files.
The included sample, if present, is explicitly historical and is not a live list.

## 10. Understand the daily schedule

The template runs Monday–Friday at approximately:

- **6:15 p.m. IST:** main scan.
- **7:15 p.m. IST:** retry if the earlier run did not complete successfully.

Your computer and phone do not need to stay switched on. Telegram delivers the
notification when your phone is online. A successful-date marker normally stops
repeat scheduled delivery for the same date. Manual runs deliberately resend.
Matching stocks are reported every day, even if mentioned on previous dates.

GitHub can delay or occasionally drop scheduled jobs. Public-repository schedules
are disabled after 60 days without repository activity. Each month, edit a short
note in README.md, for example `Reviewed on 2026-11-30`, and commit it. Simply
reading the repository is not a reliable substitute for activity.

Keep GitHub failure-email notifications enabled in your profile notification
settings. An abrupt GitHub outage/timeout cannot always send a Telegram error.
If you receive no message by the evening, check Actions. Do not treat silence as
meaning that no stocks qualified.

## 11. Change rules later

Open `config.json` in GitHub, click the pencil icon, change the desired number,
then commit. Start with the supplied settings. Increasing volume_multiple from
1.5 to 2.0 makes the volume rule stricter. ADX and Bollinger confirmations are
optional additions to the combined score; ADX >25 is not mandatory in this setup.
See README.md for the complete exact strategy and weekly-candle handling.
The source code for the more complex rules is intentionally separate from the
simple thresholds. Editing thresholds does not require changing workflow times.

## 12. Stop, resume or troubleshoot

To stop: **Actions → Daily Stock Scanner → ... → Disable workflow**.
To resume: open the workflow again and choose **Enable workflow**.

| What you see | What to do |
|---|---|
| No Run workflow button | Confirm the exact `.github/workflows/daily-scan.yml` path and that it is committed on `main`; refresh Actions. |
| No workflow at all | You may have uploaded the ZIP or placed files inside an extra folder. Follow steps 3 and 6. |
| Telegram setup found no conversation | Send `/start` to your new bot, then rerun `setup-telegram`. |
| Telegram request failed | Check both secrets, and confirm you pressed Start on the correct bot. Regenerate the token in BotFather if exposed or incorrect. |
| Missing TELEGRAM_CHAT_ID | Complete step 7. |
| Data download failed / HTTP block / low coverage | Retry later. A provider may block GitHub's IP addresses. Do not weaken data validation to force a list. If persistent, this needs a different feed/host. |
| NSE final file unavailable | It may be a holiday, a delayed publication or blocked access. Retry; for a manual holiday run choose the previous trading date. |
| Red failure during library installation | Open the failed step and copy the non-secret error text for troubleshooting. |
| Green tick but no fresh list at 7:15 | The 6:15 scan may already have delivered. Read the log for the duplicate-skip message. |
| Qualified file empty | Read the dated Telegram result and coverage. A complete scan can legitimately return no matches. |
| Schedule stopped after long inactivity | Re-enable the workflow and commit a real README update. |
| Two identical messages | Cache eviction or a delivery retry can rarely duplicate an alert; manual runs always resend. |
| Job ran for 40 minutes then stopped | GitHub timed it out. Check download failures, retry and investigate persistent provider blocks. |

Never send your token to anyone for troubleshooting. Share only redacted error
text. Screenshots must hide tokens, secrets and personal account details.

## Cost and privacy

Use a PUBLIC repository and a STANDARD `ubuntu-latest` runner, as supplied. The
standard public-runner compute is free under GitHub's current terms. Artifact and
cache storage have separate limits, so this package keeps result retention short.
There is no AI subscription and no broker connection. Free-market-data access is
not a guaranteed service and may need replacement if providers block requests.
No hosting configuration has been created in your account merely by downloading
this package; you must finish the steps and verify a successful run.

## Official references

- GitHub account/repository: https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository
- Upload files: https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository
- Repository secrets: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
- Manual run: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow
- Schedule limitations: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- GitHub billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- Bot creation: https://core.telegram.org/bots/tutorial
- PKScreener: https://github.com/pkjmesra/PKScreener
