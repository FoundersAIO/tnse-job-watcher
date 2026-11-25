# TNSE Job Watcher

Checks the [True North careers page](https://www.tnse.com/join-our-team/) every 5 minutes on GitHub Actions and pings Discord whenever anything on the page changes (full-time, casual, Hargrave St. Market, student placements), showing exactly what was added or removed.

## Setup (about 5 minutes)

1. **Make a private repo** on GitHub (e.g. `tnse-job-watcher`) and upload everything in this folder, including the `.github` folder.
2. **Make a Discord webhook:** In your server go to Server Settings → Integrations → Webhooks → New Webhook, pick a channel, then Copy Webhook URL.
3. **Add it as a secret:** In the repo go to Settings → Secrets and variables → Actions → New repository secret. Name it `DISCORD_WEBHOOK` and paste the URL as the value.
4. **Test it:** Go to Actions → Watch TNSE jobs → Run workflow and tick "Send a test Discord alert". You should get a ping.
5. **Do the first real run:** Run the workflow again without the box ticked. This saves the current page as the baseline, and from then on it runs every 30 minutes by itself.

## Options
- **Pause it:** Actions → Watch TNSE jobs → ⋯ → Disable workflow.

## Notes
- GitHub's schedule isn't exact, so 5-minute runs can arrive several minutes late, or occasionally get skipped, at busy times.
- Public repos get unlimited Actions minutes. If you make the repo private, change the cron to every 30 minutes to stay inside the free 2,000 minutes a month.
- If a run fails, GitHub emails you, so check the Actions log.
