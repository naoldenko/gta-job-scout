import os, json, sqlite3, smtplib, html, time
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "jobs.sqlite3"
CONFIG_PATH = ROOT / "config.json"

DEFAULT_CONFIG = {
    "titles": ["Engineer", "Process Engineer", "Research Assistant", "Research and Development Engineer", "Chemical Engineer"],
    "locations": ["Toronto, ON", "Greater Toronto Area, Canada"],
    "employment_types": ["Full-time", "Contract"],
    "work_modes": ["On-site", "Hybrid"],
    "max_days_old": 7,
    "notification_email": ""
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            return {**DEFAULT_CONFIG, **data}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, indent=2))

class JobAgent:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.app_id = os.getenv("ADZUNA_APP_ID", "").strip()
        self.app_key = os.getenv("ADZUNA_APP_KEY", "").strip()
        self.init_db()

    def init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT,
                created TEXT, url TEXT, contract_type TEXT, description TEXT,
                first_seen TEXT
            )""")

    def search_jobs(self):
        if not self.app_id or not self.app_key:
            raise RuntimeError("Set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env. Register for API credentials at https://developer.adzuna.com/")
        all_jobs, seen = [], set()
        for title in self.config["titles"]:
            # Adzuna Canada country code is ca; Toronto is the geographic anchor.
            params = {
                "app_id": self.app_id, "app_key": self.app_key,
                "what": title, "where": "Toronto, Ontario",
                "results_per_page": 50, "content-type": "application/json",
                "sort_by": "date", "max_days_old": self.config.get("max_days_old", 7)
            }
            url = "https://api.adzuna.com/v1/api/jobs/ca/search/1?" + urlencode(params)
            req = Request(url, headers={"User-Agent": "GTAJobScout/1.0"})
            with urlopen(req, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
            for raw in payload.get("results", []):
                jid = str(raw.get("id") or raw.get("redirect_url") or "")
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                description = raw.get("description", "")
                title_text = raw.get("title", "")
                contract = raw.get("contract_type") or ""
                category = (raw.get("category") or {}).get("label", "")
                location = (raw.get("location") or {}).get("display_name", "Toronto, ON")
                # Use listing signals where available. Avoid excluding jobs whose listing omits work mode.
                text_blob = (title_text + " " + description + " " + category).lower()
                mode = "Hybrid" if any(k in text_blob for k in ["hybrid", "on-site", "onsite", "in office", "in-person"]) else "Unspecified"
                contract_label = "Contract" if ("contract" in (contract + " " + text_blob)) else "Full-time"
                if self.config.get("employment_types") and contract_label not in self.config["employment_types"]:
                    # Do not discard unclear employment labels; keep only if no clear contradictory label.
                    if contract:
                        continue
                all_jobs.append({
                    "job_id": jid, "title": title_text,
                    "company": (raw.get("company") or {}).get("display_name", "Not listed"),
                    "location": location, "created": raw.get("created", ""),
                    "url": raw.get("redirect_url", ""), "contract_type": contract_label,
                    "description": description, "work_mode": mode
                })
            time.sleep(0.15)
        return sorted(all_jobs, key=lambda j: j.get("created", ""), reverse=True)

    def filter_new_jobs(self, jobs):
        fresh = []
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            for j in jobs:
                exists = conn.execute("SELECT 1 FROM jobs WHERE job_id=?", (j["job_id"],)).fetchone()
                if not exists:
                    fresh.append(j)
                    conn.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                        j["job_id"], j["title"], j["company"], j["location"], j["created"],
                        j["url"], j["contract_type"], j["description"], now
                    ))
        return fresh

    def send_notifications(self, jobs):
        recipient = os.getenv("NOTIFICATION_EMAIL", self.config.get("notification_email", "")).strip()
        sender = os.getenv("SMTP_FROM", "").strip()
        host = os.getenv("SMTP_HOST", "").strip()
        username = os.getenv("SMTP_USERNAME", "").strip()
        password = os.getenv("SMTP_PASSWORD", "").strip()
        port = int(os.getenv("SMTP_PORT", "587"))
        if not (recipient and sender and host and username and password):
            print("Email skipped: configure NOTIFICATION_EMAIL, SMTP_FROM, SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD.")
            return False
        msg = EmailMessage()
        msg["Subject"] = f"GTA Job Scout: {len(jobs)} new job match(es)"
        msg["From"], msg["To"] = sender, recipient
        lines = ["New job listings matching your search:\n"]
        for j in jobs:
            lines += [
                f"{j['title']} — {j['company']}",
                f"Location: {j['location']} | Type: {j['contract_type']} | Posted: {j.get('created','Not listed')}",
                f"Apply / view: {j.get('url','')}",
                ""
            ]
        lines.append("Review the listing details before applying. Work-mode information can be missing or inaccurate.")
        msg.set_content("\n".join(lines))
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        return True

    def run_daily(self):
        jobs = self.search_jobs()
        fresh = self.filter_new_jobs(jobs)
        print(f"Search returned {len(jobs)} jobs; {len(fresh)} new.")
        if fresh:
            self.send_notifications(fresh)

if __name__ == "__main__":
    JobAgent().run_daily()
