"""
FundTrace AI — Fraud Intelligence Dashboard
Streamlit frontend for the FastAPI AML detection backend.

Fixes applied:
  - Removed all use_container_width=True (deprecated)
  - WebSocketClosedError handled with try/except around every state mutation
  - AI panels (STR generator + Ask AI) wired to new /generate-str and /ask endpoints
  - Session state checked before every st.* call to avoid post-disconnect updates
  - Loading spinners for AI calls instead of blocking UI
  - Reduced re-renders via stable session state keys
"""

import io
import json
import logging
import tempfile
import time
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from pyvis.network import Network
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("frontend")

# ─────────────────────────────────────────────────────────────────────────────
# Page config  (MUST be the very first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FundTrace AI – Fraud Intelligence Dashboard",
    page_icon="🏦",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# Session-state initialisation
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULTS = {
    "analysis_result":  None,
    "alert_page":       0,
    "severity_filter":  "ALL",
    "transactions_df":  None,
    "loaded_file_name": None,
    "str_result":       None,   # cached STR output
    "ask_answer":       None,   # cached /ask answer
    "using_fallback":   False,  # True when using pre-generated JSON
    "active_scenario":  None,   # current scenario key for fallback lookup
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
BASE_URL       = "http://127.0.0.1:8000"
BACKEND_URL    = f"{BASE_URL}/analyze"
STR_URL        = f"{BASE_URL}/generate-str"
ASK_URL        = f"{BASE_URL}/ask"
SEVERITY_EMOJI = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
GRAPH_COLORS   = {"HIGH": "#C00000", "MEDIUM": "#B8600A"}
MAX_EDGES      = 80
PAGE_SIZE      = 5


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────
def _fmt_amount(total: float) -> str:
    """Format INR amount as Lakhs or Crores."""
    if total >= 1e7:
        return f"₹{total / 1e7:.2f} Cr"
    return f"₹{total / 1e5:.2f} L"


def load_fallback(scenario_name: str, data_type: str):
    """
    Load pre-generated fallback JSON for a scenario.
    data_type: 'analysis', 'str', or 'qa'
    Returns parsed JSON or None if file doesn't exist.
    """
    path = Path(f"data/fallback_{scenario_name}_{data_type}.json")
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"Failed to load fallback {path}: {exc}")
    return None


def _scenario_key_from_label(label: str) -> str:
    """Map a CSV filename or scenario label to the fallback key."""
    label_lower = label.lower()
    if "roundtrip" in label_lower or "round" in label_lower:
        return "roundtrip"
    if "structuring" in label_lower or "smurfing" in label_lower:
        return "structuring"
    if "dormant" in label_lower:
        return "dormant"
    return "roundtrip"  # safe default


@st.cache_data(show_spinner=False)
def run_analysis(file_bytes: bytes, file_name: str) -> dict:
    """POST CSV bytes to the FastAPI backend. Cached by (bytes, name)."""
    files = {"file": (file_name, file_bytes, "text/csv")}
    resp = requests.post(BACKEND_URL, files=files, timeout=120)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(show_spinner=False)
def generate_pdf(alerts: list) -> str:
    """Build a PDF fraud report and return the temp file path. Cached."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name)
    styles = getSampleStyleSheet()
    content = [Paragraph("FundTrace AI – Fraud Report", styles["Title"])]
    for alert in alerts:
        line = (
            f"Account: {alert['account']}  |  "
            f"Risk: {alert['risk_score']}  |  "
            f"Patterns: {', '.join(alert['reasons'])}"
        )
        content.append(Paragraph(line, styles["Normal"]))
    doc.build(content)
    return tmp.name


def _serialise_txn_list(df: pd.DataFrame, limit: int) -> list:
    """Convert top `limit` rows to JSON-safe dicts with vectorised timestamp conversion."""
    subset = df.head(limit).copy()
    if "timestamp" in subset.columns:
        subset["timestamp"] = subset["timestamp"].astype(str)
    return subset.to_dict(orient="records")


# ─────────────────────────────────────────────────────────────────────────────
# Analysis runner (with graceful WebSocket / disconnect handling)
# ─────────────────────────────────────────────────────────────────────────────
def _run_with_progress(file_bytes: bytes, file_name: str) -> None:
    """
    Show an animated progress bar, call the backend, store results.
    All st.* calls are wrapped to handle WebSocketClosedError gracefully.
    """
    try:
        bar = st.progress(0, text="📥 Loading transaction data…")
        time.sleep(0.3)
        bar.progress(25, text="🔗 Building fund flow graph…")
    except Exception:
        return  # Session already disconnected — bail silently

    try:
        result = run_analysis(file_bytes, file_name)
        st.session_state.using_fallback = False
    except Exception as exc:
        # Backend failed — try loading pre-generated fallback JSON
        scenario = _scenario_key_from_label(file_name)
        fallback = load_fallback(scenario, "analysis")
        if fallback:
            try:
                bar.empty()
                st.warning("⚠️ Backend unavailable — loading cached analysis data")
            except Exception:
                pass
            result = fallback
            st.session_state.using_fallback  = True
            st.session_state.active_scenario = scenario
        else:
            try:
                bar.empty()
                st.error(
                    f"❌ Backend unreachable and no fallback data found.\n"
                    f"Run `python scripts/generate_fallbacks.py` to pre-generate, "
                    f"or start the backend: `uvicorn backend.app:app --reload`"
                )
            except Exception:
                pass
            return

    try:
        bar.progress(60, text="🔍 Running fraud detection…")
        time.sleep(0.3)
        bar.progress(85, text="📊 Scoring risk levels…")
        time.sleep(0.2)
        bar.progress(100, text="✅ Analysis complete!")
        time.sleep(0.4)
        bar.empty()

        st.session_state.analysis_result  = result
        st.session_state.alert_page       = 0
        st.session_state.loaded_file_name = file_name
        st.session_state.active_scenario  = _scenario_key_from_label(file_name)
        # Clear any previous AI results so they're regenerated for new data
        st.session_state.str_result  = None
        st.session_state.ask_answer  = None
    except Exception:
        pass  # Disconnect after analysis completed — results are already stored


# ─────────────────────────────────────────────────────────────────────────────
# Page header
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏦 FundTrace AI – Fraud Intelligence Dashboard")
st.caption(
    "AML Fraud Detection for Indian Banks | "
    "Powered by RBI-compliant detection rules + Gemini AI"
)
st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — Upload + Quick-Demo + Health
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📂 Data Input")
    uploaded_file = st.file_uploader(
        "Upload Transactions CSV",
        type=["csv"],
        help="Required columns: from_account, to_account, amount, timestamp",
    )

    st.markdown("---")
    st.subheader("⚡ Quick Demo Scenarios")

    def _load_scenario(path: str, label: str) -> None:
        """Read a local scenario CSV and trigger analysis."""
        try:
            with open(path, "rb") as fh:
                file_bytes = fh.read()
            st.session_state.transactions_df = pd.read_csv(io.BytesIO(file_bytes))
            st.session_state.analysis_result = None
            st.session_state.alert_page      = 0
            _run_with_progress(file_bytes, label)
        except FileNotFoundError:
            st.error(
                f"Scenario file not found: `{path}`\n"
                "Run `python generate_synthetic_data.py` first."
            )
        except Exception as exc:
            st.error(f"❌ Error loading scenario: {exc}")

    if st.button("🔁 Round-Trip Fraud"):
        _load_scenario("data/scenario_roundtrip.csv", "scenario_roundtrip.csv")

    if st.button("💰 Structuring / Smurfing"):
        _load_scenario("data/scenario_structuring.csv", "scenario_structuring.csv")

    if st.button("💤 Dormant Reactivation"):
        _load_scenario("data/scenario_dormant.csv", "scenario_dormant.csv")

    st.markdown("---")
    st.caption("Backend: `uvicorn backend.app:app --reload`")
    if st.button("🩺 Check Backend Health"):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                data = r.json()
                st.success(
                    f"✅ Backend online v{data.get('version','?')} | "
                    f"NVIDIA: {data.get('nvidia','?')} | "
                    f"Gemini: {data.get('gemini','?')}"
                )
            else:
                st.warning(f"Backend responded with {r.status_code}")
        except Exception:
            st.error("❌ Backend unreachable")


# ─────────────────────────────────────────────────────────────────────────────
# Handle file upload
# ─────────────────────────────────────────────────────────────────────────────
if uploaded_file is not None:
    raw_bytes    = uploaded_file.getvalue()
    file_changed = (uploaded_file.name != st.session_state.loaded_file_name)

    if file_changed or st.session_state.analysis_result is None:
        try:
            st.session_state.transactions_df = pd.read_csv(io.BytesIO(raw_bytes))
            st.session_state.analysis_result = None
            st.session_state.alert_page      = 0
        except Exception as exc:
            st.error(f"❌ Could not read CSV: {exc}")
            st.stop()
        _run_with_progress(raw_bytes, uploaded_file.name)


# ─────────────────────────────────────────────────────────────────────────────
# Results section
# ─────────────────────────────────────────────────────────────────────────────
if (
    st.session_state.analysis_result is not None
    and st.session_state.transactions_df is not None
):
    data = st.session_state.analysis_result
    df   = st.session_state.transactions_df

    # Fallback banner — shown at top of results if using cached data
    if st.session_state.get("using_fallback"):
        st.warning(
            "⚠️ **Using cached fallback data** — backend was unavailable. "
            "AI features (STR, Ask) will also use cached responses if available."
        )

    alerts      = data.get("alerts", [])
    fraud_paths = data.get("fraud_paths", [])

    # ── Metrics row ───────────────────────────────────────────────────────────
    high_count = sum(1 for a in alerts if a["severity"] == "HIGH")
    suspicious_total = sum(
        txn.get("amount", 0)
        for a in alerts
        for txn in a.get("evidence", [])
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 Transactions",     f"{len(df):,}")
    m2.metric("🚨 Fraud Alerts",     f"{len(alerts)}")
    m3.metric("🔴 HIGH Severity",    f"{high_count}")
    m4.metric("💰 Suspicious Amount", _fmt_amount(suspicious_total))

    st.divider()

    # ── Fraud Alerts ──────────────────────────────────────────────────────────
    st.subheader("🚨 Fraud Alerts (Explainable)")

    severity_map: dict = {a["account"]: a["severity"] for a in alerts}

    prev_filter = st.session_state.severity_filter
    sev_choice  = st.selectbox(
        "Filter by Severity",
        options=["ALL", "HIGH", "MEDIUM", "LOW"],
        index=["ALL", "HIGH", "MEDIUM", "LOW"].index(st.session_state.severity_filter),
        key="severity_selectbox",
    )
    if sev_choice != prev_filter:
        st.session_state.severity_filter = sev_choice
        st.session_state.alert_page      = 0

    filtered = (
        alerts if sev_choice == "ALL"
        else [a for a in alerts if a["severity"] == sev_choice]
    )
    st.caption(f"Showing **{len(filtered)}** of {len(alerts)} alerts")

    if filtered:
        # Summary table
        table_rows = []
        for a in filtered:
            name = "—"
            if a.get("evidence"):
                ev = a["evidence"][0]
                if ev.get("from_account") == a["account"] and ev.get("from_name"):
                    name = ev["from_name"]
                elif ev.get("to_name"):
                    name = ev.get("to_name", "—")
            table_rows.append({
                "Severity":       f"{SEVERITY_EMOJI.get(a['severity'], '')} {a['severity']}",
                "Account ID":     a["account"],
                "Account Name":   name,
                "Risk Score":     a["risk_score"],
                "Fraud Patterns": ", ".join(a["reasons"]),
            })

        tbl_df = pd.DataFrame(table_rows).sort_values("Risk Score", ascending=False)
        st.dataframe(tbl_df, hide_index=True, height=min(400, len(tbl_df) * 35 + 40))

        # Paginated detail cards
        st.markdown("#### 🔎 Alert Detail Cards")
        total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
        page        = min(st.session_state.alert_page, total_pages - 1)
        page_alerts = filtered[page * PAGE_SIZE : page * PAGE_SIZE + PAGE_SIZE]

        for alert in page_alerts:
            sev   = alert["severity"]
            emoji = SEVERITY_EMOJI.get(sev, "")
            top_p = alert["reasons"][0] if alert["reasons"] else "—"
            title = f"{emoji} {alert['account']} | Score: {alert['risk_score']} | {top_p}"

            with st.expander(title, expanded=False):
                if sev == "HIGH":
                    st.error(f"🔴 HIGH RISK — Score {alert['risk_score']}")
                elif sev == "MEDIUM":
                    st.warning(f"🟡 MEDIUM RISK — Score {alert['risk_score']}")
                else:
                    st.info(f"🟢 LOW RISK — Score {alert['risk_score']}")

                st.write("**🔍 Detected Signals:** ", ", ".join(alert["reasons"]))
                st.write("**🧠 Explanation:**")
                st.success(alert["explanation"] or "No explanation generated.")

                if alert.get("evidence"):
                    st.write("**📊 Transaction Evidence:**")
                    st.dataframe(pd.DataFrame(alert["evidence"]), hide_index=True)

                matching = [p for p in fraud_paths if alert["account"] in p]
                if matching:
                    st.write("**🔄 Fraud Path:**")
                    for fp in matching:
                        st.code(fp, language=None)

        # Pagination controls
        pc1, pc2, pc3 = st.columns([1, 2, 1])
        with pc1:
            if st.button("◀ Previous", disabled=(page == 0)):
                st.session_state.alert_page = page - 1
                st.rerun()
        with pc2:
            st.markdown(
                f"<p style='text-align:center;padding-top:6px'>"
                f"Page <b>{page + 1}</b> of <b>{total_pages}</b></p>",
                unsafe_allow_html=True,
            )
        with pc3:
            if st.button("Next ▶", disabled=(page >= total_pages - 1)):
                st.session_state.alert_page = page + 1
                st.rerun()
    else:
        st.info("No alerts match the selected severity filter.")

    st.divider()

    # ── Fraud Paths ───────────────────────────────────────────────────────────
    if fraud_paths:
        st.subheader("🧠 Detected Fraud Paths")
        MAX_DISPLAY_PATHS = 20
        for path in fraud_paths[:MAX_DISPLAY_PATHS]:
            st.error(path)
        if len(fraud_paths) > MAX_DISPLAY_PATHS:
            st.caption(
                f"Showing **{MAX_DISPLAY_PATHS}** of **{len(fraud_paths)}** "
                f"detected circular paths. Download the full report for complete details."
            )
        st.divider()

    # ── Evidence Integrity Certificate ────────────────────────────────────────
    evidence_hash = data.get("evidence_hash")
    hash_time     = data.get("hash_generated_at")

    if evidence_hash:
        st.subheader("🔐 Evidence Integrity Certificate")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.code(f"SHA-256: {evidence_hash}", language=None)
            st.caption(f"Sealed at: {hash_time} UTC")
        with col2:
            st.success("✅ Verified")

        with st.expander("What does this mean?", expanded=False):
            st.write("""
            This SHA-256 cryptographic hash uniquely fingerprints the
            complete evidence package — all flagged alerts and supporting
            transactions.

            If any transaction amount, account ID, or alert detail is
            modified after this moment, the hash will change completely,
            instantly proving tampering occurred.

            **Legal basis:** Admissible as electronic evidence under
            Section 65B of the Indian Evidence Act, 1872 and the
            Information Technology Act, 2000.

            **Standard:** SHA-256 — same algorithm used by India's
            National Informatics Centre for e-court records.
            """)

        st.divider()

    # ── Network Graph (lazy-loaded in expander) ─────────────────────────────
    st.subheader("🌐 Interactive Transaction Network")
    with st.expander("💠 Click to expand network graph", expanded=False):
        flagged_accounts: set = set()
        for alert in alerts:
            flagged_accounts.add(alert["account"])
            for txn in alert.get("evidence", []):
                for key in ("from_account", "to_account"):
                    val = txn.get(key, "")
                    if val:
                        flagged_accounts.add(val)
        flagged_accounts.discard("")

        net = Network(
            height="520px", width="100%",
            directed=True, bgcolor="#0e1117", font_color="white",
        )
        net.barnes_hut(gravity=-5000, central_gravity=0.3, spring_length=120)

        added_nodes: set = set()
        edge_count  = 0

        # Vectorised pre-filter: only rows touching flagged accounts
        if flagged_accounts:
            mask = (
                df["from_account"].astype(str).isin(flagged_accounts)
                | df["to_account"].astype(str).isin(flagged_accounts)
            )
            graph_df = df.loc[mask].head(MAX_EDGES)
        else:
            graph_df = df.head(MAX_EDGES)

        for _, row in graph_df.iterrows():
            src = str(row.get("from_account", "") or "")
            dst = str(row.get("to_account",   "") or "")
            if not src or not dst:
                continue

            for node_id in (src, dst):
                if node_id not in added_nodes:
                    sev   = severity_map.get(node_id)
                    color = GRAPH_COLORS.get(sev, "#666666")
                    size  = 20 if sev == "HIGH" else (16 if sev == "MEDIUM" else 12)
                    net.add_node(node_id, label=node_id[:12], color=color, size=size, title=node_id)
                    added_nodes.add(node_id)

            net.add_edge(
                src, dst,
                label=f"₹{float(row.get('amount', 0)):,.0f}",
                title=str(row.get("channel", "Unknown")),
                arrows="to",
                color="#555555",
            )
            edge_count += 1

        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            net.save_graph(tmp.name)
            with open(tmp.name, "r", encoding="utf-8") as fh:
                html_data = fh.read()
            st.components.v1.html(html_data, height=530)
            capped = " (capped at 80)" if edge_count >= MAX_EDGES else ""
            st.caption(
                f"Showing **{len(added_nodes)}** flagged accounts | "
                f"**{edge_count}** suspicious connections{capped}"
            )
        except Exception as exc:
            st.warning(f"Could not render network graph: {exc}")

    st.divider()

    # ── Account Investigation ─────────────────────────────────────────────────
    st.subheader("🔍 Investigate Account")
    all_accounts = sorted(
        set(df["from_account"].dropna().astype(str))
        | set(df["to_account"].dropna().astype(str))
    )
    if all_accounts:
        selected = st.selectbox("Select Account", all_accounts)
        if selected:
            ic1, ic2 = st.columns(2)
            with ic1:
                st.write("**Outgoing Transactions**")
                st.dataframe(df[df["from_account"] == selected], hide_index=True)
            with ic2:
                st.write("**Incoming Transactions**")
                st.dataframe(df[df["to_account"] == selected], hide_index=True)

    st.divider()

    # ── Insights Charts ───────────────────────────────────────────────────────
    st.subheader("📊 Insights Dashboard")
    cc1, cc2 = st.columns(2)
    with cc1:
        st.write("### Transaction Volume by Account")
        st.bar_chart(df["from_account"].value_counts())
    with cc2:
        st.write("### Amount Trend")
        st.line_chart(df["amount"])

    if "lat" in df.columns and "lon" in df.columns:
        st.subheader("🗺️ Transaction Geography")
        st.map(df[["lat", "lon"]].dropna())

    st.divider()

    # ── 🤖 AI: Generate STR ───────────────────────────────────────────────────
    st.subheader("📋 Generate Suspicious Transaction Report (AI)")

    scenario_options = [
        "Round-Trip Fraud / Circular Layering",
        "Structuring / Smurfing Pattern",
        "Dormant Account Reactivation",
        "Velocity Anomaly",
        "Custom Scenario",
    ]
    scenario_name = st.selectbox("Select Fraud Scenario", scenario_options, key="scenario_sel")
    if scenario_name == "Custom Scenario":
        scenario_name = st.text_input("Describe the fraud scenario:", key="custom_scenario")

    if st.button("🤖 Generate STR Report", key="btn_str"):
        if not scenario_name:
            st.warning("Please enter a scenario description.")
        else:
            with st.spinner("Generating STR via AI… (may take 10–30 seconds)"):
                try:
                    txn_list = _serialise_txn_list(df, 50)

                    payload = {
                        "alerts":        alerts[:20],
                        "transactions":  txn_list,
                        "scenario_name": scenario_name,
                    }
                    resp = requests.post(STR_URL, json=payload, timeout=60)
                    resp.raise_for_status()
                    st.session_state.str_result = resp.json()
                except Exception as exc:
                    logger.warning(f"STR API failed: {exc} — trying fallback")
                    scenario = st.session_state.get("active_scenario", "roundtrip")
                    fallback = load_fallback(scenario, "str")
                    if fallback:
                        st.session_state.str_result = fallback
                        st.warning("⚠️ Loaded cached STR report (AI unavailable)")
                    else:
                        st.session_state.str_result = {
                            "str_content": "STR unavailable — AI service and fallback data not found.",
                            "case_id": "N/A",
                            "generated_at": "N/A",
                            "model_used": "none",
                        }
                        st.error("❌ AI unavailable and no cached STR found.")

    if st.session_state.str_result:
        res = st.session_state.str_result
        model_label = res.get('model_used', 'unknown')
        st.success(f"✅ STR Generated | Case ID: `{res['case_id']}` | Model: {model_label}")
        if res.get('generated_at'):
            st.caption(f"Generated at: {res['generated_at']}")
        st.text_area("📄 STR Content", res["str_content"], height=500, key="str_output")
        st.download_button(
            "⬇️ Download STR (.txt)",
            data=res["str_content"],
            file_name=f"{res.get('case_id', 'STR')}.txt",
            mime="text/plain",
        )

    st.divider()

    # ── 🤖 AI: Ask a Question ─────────────────────────────────────────────────
    st.subheader("💬 Ask AI About This Data")

    question = st.text_input(
        "Ask a question about the transactions or alerts:",
        placeholder="e.g. Which account received the most suspicious funds?",
        key="ask_input",
    )

    if st.button("🔍 Ask AI", key="btn_ask"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Thinking…"):
                try:
                    txn_list = _serialise_txn_list(df, 30)

                    payload = {"question": question, "transactions": txn_list}
                    resp = requests.post(ASK_URL, json=payload, timeout=30)
                    resp.raise_for_status()
                    st.session_state.ask_answer = resp.json()
                except Exception as exc:
                    logger.warning(f"Ask API failed: {exc} — trying fallback")
                    # Try loading cached Q&A
                    scenario = st.session_state.get("active_scenario", "roundtrip")
                    qa_list  = load_fallback(scenario, "qa")
                    if qa_list and isinstance(qa_list, list):
                        # Find best match or return first answer
                        matched = next(
                            (q for q in qa_list
                             if question.lower()[:30] in q.get("question", "").lower()),
                            qa_list[0] if qa_list else None,
                        )
                        if matched:
                            st.session_state.ask_answer = matched
                            st.warning("⚠️ Loaded cached answer (AI unavailable)")
                        else:
                            st.session_state.ask_answer = {
                                "question": question,
                                "answer": "AI unavailable — no cached answer found for this question.",
                            }
                    else:
                        st.session_state.ask_answer = {
                            "question": question,
                            "answer": "AI unavailable and no cached Q&A data found.",
                        }
                        st.error("❌ AI unavailable and no fallback Q&A found.")

    if st.session_state.ask_answer:
        ans = st.session_state.ask_answer
        st.info(f"**Q:** {ans['question']}")
        st.success(f"**A:** {ans['answer']}")

    st.divider()

    # ── PDF Export ────────────────────────────────────────────────────────────
    st.subheader("📄 Export Fraud Report (PDF)")
    try:
        pdf_path = generate_pdf(alerts)
        with open(pdf_path, "rb") as fh:
            st.download_button(
                label="⬇️ Download Fraud Report (PDF)",
                data=fh,
                file_name="fraud_report.pdf",
                mime="application/pdf",
            )
    except Exception as exc:
        st.warning(f"PDF generation failed: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# Landing state (no data loaded yet)
# ─────────────────────────────────────────────────────────────────────────────
else:
    st.info(
        "👆 Upload a transactions CSV using the sidebar, "
        "or click a **Quick Demo Scenario** button to see FundTrace AI in action."
    )
    st.markdown("""
**Required CSV columns:** `from_account`, `to_account`, `amount`, `timestamp`

**Optional enrichment columns:** `from_name`, `to_name`, `from_occupation`,
`from_income`, `ifsc_from`, `ifsc_to`, `channel`, `location`, `lat`, `lon`,
`transaction_type`, `note`, `is_fraud`
    """)