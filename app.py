import os
import streamlit as st
from dotenv import load_dotenv
from agent import JobAgent, load_config, save_config

load_dotenv()
st.set_page_config(page_title="GTA Job Scout", page_icon="🔎", layout="wide")
st.title("🔎 GTA Job Scout")
st.caption("A lightweight job-search agent for engineering and R&D roles in Toronto and the GTA.")

config = load_config()
with st.sidebar:
    st.header("Search preferences")
    titles = st.text_area("Job titles (one per line)", "\n".join(config["titles"]), height=130)
    locations = st.text_area("Locations (one per line)", "\n".join(config["locations"]), height=80)
    employment = st.multiselect("Employment types", ["Full-time", "Contract"], default=config["employment_types"])
    work_modes = st.multiselect("Work arrangement", ["On-site", "Hybrid"], default=config["work_modes"])
    max_age = st.selectbox("Include jobs posted within", [1, 3, 7, 14, 30], index=[1,3,7,14,30].index(config.get("max_days_old", 7)), format_func=lambda x: f"{x} days")
    email_to = st.text_input("Notification recipient", value=config.get("notification_email", ""))
    if st.button("Save preferences", type="primary"):
        config.update({
            "titles": [x.strip() for x in titles.splitlines() if x.strip()],
            "locations": [x.strip() for x in locations.splitlines() if x.strip()],
            "employment_types": employment,
            "work_modes": work_modes,
            "max_days_old": max_age,
            "notification_email": email_to.strip(),
        })
        save_config(config)
        st.success("Preferences saved locally.")

col1, col2, col3 = st.columns(3)
col1.metric("Target area", "Toronto + GTA")
col2.metric("Work mode", "On-site / Hybrid")
col3.metric("Search cadence", "Daily via GitHub Actions")

st.info("This starter app uses the Adzuna Jobs API. Add your API credentials to `.env` to enable live search. The scheduled workflow can email new matches after you configure repository secrets.")

if st.button("Search for jobs now", type="primary"):
    try:
        agent = JobAgent(config)
        with st.spinner("Searching configured job sources…"):
            jobs = agent.search_jobs()
            fresh = agent.filter_new_jobs(jobs)
        if jobs:
            st.success(f"Found {len(jobs)} matching listings; {len(fresh)} are new to the tracker.")
            st.dataframe([{
                "Title": j.get("title", ""),
                "Company": j.get("company", ""),
                "Location": j.get("location", ""),
                "Posted": j.get("created", ""),
                "Employment": j.get("contract_type", ""),
                "Link": j.get("url", ""),
            } for j in jobs], use_container_width=True, hide_index=True)
            if fresh and st.button("Send email for new matches"):
                sent = agent.send_notifications(fresh)
                st.success("Notification email sent." if sent else "Email not sent. Check SMTP settings in .env.")
        else:
            st.warning("No results returned. Check API credentials or try broader titles.")
    except Exception as e:
        st.error(f"Search failed: {e}")

st.subheader("How matching works")
st.markdown("""
- Searches each job title in Toronto and the Greater Toronto Area.
- Keeps full-time and contract opportunities, prioritizing on-site/hybrid roles where the listing provides work-mode details.
- Deduplicates listings so the daily agent can notify only about newly discovered jobs.
- Does not apply to jobs automatically; you review each listing and decide whether to apply.
""")
