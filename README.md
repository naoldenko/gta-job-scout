# GTA Job Scout

A starter web app + scheduled agent for discovering newly posted engineering and R&D jobs in Toronto / the GTA and emailing new matches.

## Default search profile
- Titles: Engineer, Process Engineer, Research Assistant, Research and Development Engineer, Chemical Engineer
- Area: Toronto, Ontario (used as the API's geographic anchor; expand/adjust in the Adzuna dashboard or config if needed)
- Work mode: on-site / hybrid preference
- Employment: full-time and contract
- Timing: flexible / casual search; default lookback is 7 days
- Notifications: email when new listing IDs appear

## Important limitations
- This starter uses the Adzuna Jobs API. You must obtain API credentials and configure SMTP to receive email.
- The API's coverage, freshness, and work-mode labels vary. Some listings don't clearly specify hybrid/on-site; those are not reliably classifiable from the public listing text.
- This is a discovery/notification tool, not an application bot. Always verify role details on the employer's application page.
- The scheduled GitHub Actions workflow is included, but GitHub-hosted runners are ephemeral. The database is uploaded as an artifact after each run, but the workflow does not automatically restore that artifact before the next run. For reliable long-term deduplication, use a persistent host/database or add a restore step. A simpler alternative is to run the agent on a small always-on machine.
- Search terms are sent to Adzuna. Review their API terms before use.

## 1. Run the dashboard locally
Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in `.env`. Register at https://developer.adzuna.com/.

Start the web app:

```bash
streamlit run app.py
```

Use the sidebar to customize preferences and **Search for jobs now** to query the API.

## 2. Configure email
For Gmail, set `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, your sender/username, and an app password in `SMTP_PASSWORD` (if required by your account). Do not commit `.env` or credentials to Git.

Test by running:

```bash
python agent.py
```

The first run records listings as seen and emails them. Later runs email only listings with previously unseen IDs, provided the database persists.

## 3. Run daily with GitHub Actions
1. Create a private GitHub repository and upload these project files.
2. Open **Settings → Secrets and variables → Actions → New repository secret**.
3. Add `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `NOTIFICATION_EMAIL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USERNAME`, and `SMTP_PASSWORD`.
4. Under **Actions**, enable workflows and run **Daily GTA job search** manually once.
5. Scheduled runs are daily. GitHub may delay scheduled workflows, and they require the repository to remain active.

For persistent deduplication, deploy the script to a host with persistent disk or database. The included workflow artifact is a backup, not an automatic database restore.

## 4. Customize
Edit `config.json` or use the dashboard. `work_modes` is a preference field; due to inconsistent listing metadata, the current MVP retains listings with missing mode data rather than risk missing a suitable role. Review the work arrangement on the employer's site.
