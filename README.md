# TNSE Job Watcher

Checks the [True North careers page](https://www.tnse.com/join-our-team/) every 30 minutes on GitHub Actions and pings Discord when the **Full-Time Employment Opportunities** section changes.

## Setup (about 5 minutes)

1. **Make a private repo** on GitHub (e.g. `tnse-job-watcher`) and upload everything in this folder, including the `.github` folder.
2. **Make a Discord webhook:** In your server go to Server Settings → Integrations → Webhooks → New Webhook, pick a channel, then Copy Webhook URL.
3. **Add it as a secret:** In the repo go to Settings → Secrets and variables → Actions → New repository secret. Name it `DISCORD_WEBHOOK` and paste the URL as the value.
4. **Test it:** Go to Actions → Watch TNSE jobs → Run workflow and tick "Send a test Discord alert". You should get a ping.
5. **Do the first real run:** Run the workflow again without the box ticked. This saves the current page as the baseline, and from then on it runs every 30 minutes by itself.

## Options
- **Watch every section** (casual, Hargrave St. Market, student placements): Settings → Secrets and variables → Actions → Variables tab, then add `WATCH_ALL` = `true`.
- **Pause it:** Actions → Watch TNSE jobs → ⋯ → Disable workflow.

## Notes
- GitHub's schedule isn't exact, so runs can arrive 5–15 minutes late at busy times.
- Each run takes under a minute. That's about 1,500 minutes a month, which is inside the free 2,000 minutes for private repos.
- If a run fails, GitHub emails you, so check the Actions log.
