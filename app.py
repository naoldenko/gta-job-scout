import html
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from agent import JobAgent, load_config, save_config

ROOT = Path(__file__).resolve().parent

load_dotenv()
st.set_page_config(
    page_title="GTA Job Scout",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css():
    css = (ROOT / "static" / "liquid_glass.css").read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


inject_css()
config = load_config()

with st.sidebar:
    st.markdown("### Search preferences")
    titles = st.text_area("Job titles (one per line)", "\n".join(config["titles"]), height=130)
    locations = st.text_area("Locations (one per line)", "\n".join(config["locations"]), height=80)
    employment = st.multiselect(
        "Employment types",
        ["Full-time", "Contract"],
        default=config["employment_types"],
    )
    work_modes = st.multiselect(
        "Work arrangement",
        ["On-site", "Hybrid"],
        default=config["work_modes"],
    )
    max_age = st.selectbox(
        "Include jobs posted within",
        [1, 3, 7, 14, 30],
        index=[1, 3, 7, 14, 30].index(config.get("max_days_old", 7)),
        format_func=lambda x: f"{x} days",
    )

st.markdown(
    """
    <section class="hero-glass">
      <div class="eyebrow">Engineering · R&amp;D · Toronto / GTA</div>
      <h1>GTA Job Scout</h1>
      <p>A lightweight discovery agent for newly posted engineering and research roles. Search live, and track unseen listings.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="stat-grid">
      <article class="stat-card">
        <div class="label">Target area</div>
        <div class="value">Toronto + GTA</div>
      </article>
      <article class="stat-card">
        <div class="label">Work mode</div>
        <div class="value">On-site / Hybrid</div>
      </article>
    </div>
    """,
    unsafe_allow_html=True,
)

search = st.button("Search for jobs now", type="primary")

if search:
    try:
        agent = JobAgent(config)
        with st.spinner("Searching configured job sources…"):
            jobs = agent.search_jobs()
            fresh = agent.filter_new_jobs(jobs)
        if jobs:
            st.success(f"Found {len(jobs)} matching listings; {len(fresh)} are new to the tracker.")
            fresh_ids = {j["job_id"] for j in fresh}
            for j in jobs:
                title = html.escape(j.get("title") or "Untitled role")
                company = html.escape(j.get("company") or "Not listed")
                location = html.escape(j.get("location") or "")
                posted = html.escape(str(j.get("created") or "Date not listed"))
                employment_type = html.escape(j.get("contract_type") or "")
                url = html.escape(j.get("url") or "", quote=True)
                badge = '<span class="chip">New</span>' if j.get("job_id") in fresh_ids else ""
                link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">Open listing</a>' if url else ""
                st.markdown(
                    f"""
                    <article class="job-card">
                      <h3>{title} {badge}</h3>
                      <div class="job-meta">
                        <span>{company}</span>
                        <span>{location}</span>
                        <span>{posted}</span>
                        <span class="chip">{employment_type}</span>
                      </div>
                      {link}
                    </article>
                    """,
                    unsafe_allow_html=True,
                )
            if fresh and st.button("Send email for new matches"):
                sent = agent.send_notifications(fresh)
                st.success("Notification email sent." if sent else "Email not sent. Check SMTP settings in .env.")
        else:
            st.warning("No results returned. Check API credentials or try broader titles.")
    except Exception as e:
        st.error(f"Search failed: {e}")

st.markdown('<h2 class="section-title">How matching works</h2>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="how-grid">
      <article class="how-card">
        <div class="num">01</div>
        <h3>Search the GTA</h3>
        <p>Queries each job title against Toronto and the Greater Toronto Area.</p>
      </article>
      <article class="how-card">
        <div class="num">02</div>
        <h3>Filter the fit</h3>
        <p>Keeps full-time and contract roles, preferring on-site and hybrid listings when mode is stated.</p>
      </article>
      <article class="how-card">
        <div class="num">03</div>
        <h3>You decide</h3>
        <p>Does not apply automatically. Review each listing on the employer’s page before applying.</p>
      </article>
    </div>
    """,
    unsafe_allow_html=True,
)
