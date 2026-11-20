"""Streamlit UI for the Multi-Agent Research System.

Run with:  streamlit run app.py

This file only wraps `run_research_pipeline()` from pipeline.py. All agent,
tool and chain logic stays in agents.py / tools.py / pipeline.py.
"""

import os
import re
import sys
import time
import traceback
from pathlib import Path

import hmac

import streamlit as st
from dotenv import load_dotenv

# Make sure imports and the .env file resolve relative to this file,
# no matter which directory `streamlit run` is launched from.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
load_dotenv(APP_DIR / ".env")

st.set_page_config(
    page_title="Multi-Agent Research System",
    page_icon="🔎",
    layout="wide",
)


# ----------------------------------------------------------------------------
# Authentication
# ----------------------------------------------------------------------------

USERNAME = os.getenv("APP_USERNAME")
PASSWORD = os.getenv("APP_PASSWORD")

# Check whether credentials are configured
if not USERNAME or not PASSWORD:
    st.error("Application credentials are not configured.")
    st.stop()

# Initialize authentication state for this user's session
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Display login page if the user is not authenticated
if not st.session_state["authenticated"]:

    st.title("🔐 Login")
    st.write("Please enter your credentials to access the application.")

    with st.form("login_form"):
        entered_username = st.text_input("Username")
        entered_password = st.text_input(
            "Password",
            type="password"
        )

        login_submitted = st.form_submit_button(
            "Login",
            type="primary",
            use_container_width=True
        )

    if login_submitted:
        username_valid = hmac.compare_digest(
            entered_username,
            USERNAME
        )
        password_valid = hmac.compare_digest(
            entered_password,
            PASSWORD
        )

        if username_valid and password_valid:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid username or password.")

    # Stop execution here until the user logs in
    st.stop()

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

SCORE_RE = re.compile(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", re.IGNORECASE)


def parse_feedback(text: str) -> dict:
    """Split the critic's fixed-format output into score / strengths /
    improvements / verdict. Falls back gracefully if the format differs."""
    parsed = {"score": None, "strengths": None, "improve": None, "verdict": None}
    if not isinstance(text, str):
        return parsed

    m = SCORE_RE.search(text)
    if m:
        parsed["score"] = float(m.group(1))

    s = re.search(r"Strengths:\s*(.*?)(?=Areas to Improve:|One line verdict:|$)",
                  text, re.IGNORECASE | re.DOTALL)
    i = re.search(r"Areas to Improve:\s*(.*?)(?=One line verdict:|$)",
                  text, re.IGNORECASE | re.DOTALL)
    v = re.search(r"One line verdict:\s*(.*)$", text, re.IGNORECASE | re.DOTALL)

    parsed["strengths"] = s.group(1).strip() if s else None
    parsed["improve"] = i.group(1).strip() if i else None
    parsed["verdict"] = v.group(1).strip() if v else None
    return parsed


def keys_status() -> dict:
    """Only reports whether keys exist. Never displays their values."""
    return {
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "TAVILY_API_KEY": bool(os.getenv("TAVILY_API_KEY")),
    }


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()[:50] or "report"


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------

with st.sidebar:

    if st.button("Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

    st.divider()
    
    st.header("About")
    st.write(
        "A four-stage pipeline powered by LangChain:\n\n"
        "1. **Search Agent** finds recent sources\n"
        "2. **Reader Agent** scrapes the best one\n"
        "3. **Writer Chain** drafts the report\n"
        "4. **Critic Chain** reviews and scores it"
    )
    st.divider()
    st.subheader("Configuration")
    for name, ok in keys_status().items():
        st.write(("✅ " if ok else "❌ ") + name + (" loaded" if ok else " missing"))
    st.caption("Keys are read from your `.env` file and are never shown here.")

# ----------------------------------------------------------------------------
# Header + input
# ----------------------------------------------------------------------------

st.title("🔎 Multi-Agent Research System")
st.caption(
    "Enter a topic and a team of AI agents will search the web, read the best "
    "source, write a structured report, and have it critically reviewed."
)

with st.form("research_form", clear_on_submit=False):
    topic = st.text_area(
        "Research topic",
        placeholder="e.g. Recent advances in solid-state batteries",
        height=100,
    )
    submitted = st.form_submit_button(
        "🚀 Start Research", type="primary", use_container_width=True
    )

# ----------------------------------------------------------------------------
# Run the pipeline
# ----------------------------------------------------------------------------

if submitted:
    topic = topic.strip()
    if not topic:
        st.warning("Please enter a research topic first.")
    else:
        st.session_state.pop("result", None)
        st.session_state.pop("error", None)

        with st.status("Running multi-agent research pipeline...", expanded=True) as status:
            st.write(
                "🔍 Search agent → 📄 Reader agent → ✍️ Writer chain → 🧐 Critic chain"
            )
            st.write("This can take a minute or two. Please keep this tab open.")
            started = time.time()
            try:
                # Imported here so config/import errors (e.g. missing API key)
                # show up in the UI instead of crashing the whole app.
                from pipeline import run_research_pipeline

                result = run_research_pipeline(topic)

                if not isinstance(result, dict):
                    raise TypeError(
                        f"run_research_pipeline returned {type(result).__name__}, "
                        "expected a dict."
                    )

                st.session_state["result"] = result
                st.session_state["topic"] = topic
                st.session_state["elapsed"] = time.time() - started
                status.update(label="Research complete", state="complete", expanded=False)
            except Exception as exc:  # noqa: BLE001
                st.session_state["error"] = (exc, traceback.format_exc())
                status.update(label="Pipeline failed", state="error", expanded=True)

# ----------------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------------

if "error" in st.session_state:
    exc, tb = st.session_state["error"]
    st.error(f"The research pipeline failed: **{type(exc).__name__}**: {exc}")
    st.caption(
        "Common causes: missing/invalid API keys in `.env`, no network access, "
        "an unavailable model name, or an API rate limit."
    )
    with st.expander("Technical details"):
        st.code(tb)

# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------

if "result" in st.session_state:
    result = st.session_state["result"]
    shown_topic = st.session_state.get("topic", "")
    feedback_text = result.get("feedback", "")
    fb = parse_feedback(feedback_text)

    st.divider()
    st.subheader(f"Results: {shown_topic}")

    # Summary metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Critic score", f"{fb['score']:g} / 10" if fb["score"] is not None else "N/A")
    c2.metric("Report length", f"{len((result.get('report') or '').split()):,} words")
    c3.metric("Run time", f"{st.session_state.get('elapsed', 0):.0f} s")

    tab_report, tab_review, tab_sources = st.tabs(
        ["📝 Final Report", "🧐 Critic Review", "🗂️ Raw Research"]
    )

    with tab_report:
        report = result.get("report")
        if report:
            st.markdown(report)
            st.download_button(
                "⬇️ Download report (.md)",
                data=report,
                file_name=f"{slugify(shown_topic)}_report.md",
                mime="text/markdown",
            )
        else:
            st.info("The pipeline did not return a report.")

    with tab_review:
        if not feedback_text:
            st.info("The pipeline did not return critic feedback.")
        else:
            if fb["score"] is not None:
                st.progress(min(max(fb["score"] / 10, 0.0), 1.0), text=f"Score: {fb['score']:g}/10")
            if fb["verdict"]:
                st.info(f"**Verdict:** {fb['verdict']}")
            if fb["strengths"] or fb["improve"]:
                left, right = st.columns(2)
                with left:
                    st.markdown("#### ✅ Strengths")
                    st.markdown(fb["strengths"] or "_Not provided_")
                with right:
                    st.markdown("#### 🔧 Areas to Improve")
                    st.markdown(fb["improve"] or "_Not provided_")
            else:
                # Critic didn't follow the expected format; show it as-is.
                st.markdown(feedback_text)

    with tab_sources:
        with st.expander("🔍 Search agent results", expanded=False):
            st.markdown(result.get("search_results") or "_No search results returned._")
        with st.expander("📄 Reader agent: scraped content", expanded=False):
            st.markdown(result.get("scraped_content") or "_No scraped content returned._")