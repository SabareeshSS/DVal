from datetime import datetime
import streamlit as st
from main import (
    run_document_validation,
    save_approval_gate,
    get_installed_ollama_models,
)

# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Rental Agreement Validator",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS — fully theme-aware, dark + light mode safe
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: #0F172A !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] .stMarkdown {
    color: #CBD5E1 !important;
}
[data-testid="stSidebar"] strong {
    color: #F1F5F9 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #4A6CF7, #6A3DE8) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.2rem !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    width: 100% !important;
    transition: opacity 0.2s, transform 0.1s !important;
    box-shadow: 0 4px 14px rgba(74,108,247,0.35) !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stFileUploader label {
    color: #94A3B8 !important;
    font-size: 0.8rem !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: #1E293B !important;
    border-radius: 8px !important;
    border: 1.5px dashed #334155 !important;
    padding: 0.5rem !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] {
    background: #1E293B !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: #F1F5F9 !important;
    background: #1E293B !important;
}

/* Sidebar divider */
[data-testid="stSidebar"] hr {
    border-color: #1E293B !important;
    margin: 0.8rem 0 !important;
}

/* Workflow step dots */
.wf-step {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.35rem 0;
    font-size: 0.83rem;
    color: #94A3B8;
}
.wf-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #4A6CF7;
    flex-shrink: 0;
}

/* ═══════════════════════════════════════════════════════════════
   HEADER BANNER
═══════════════════════════════════════════════════════════════ */
.app-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 50%, #1E293B 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 1.4rem;
    border: 1px solid #1E3A5F;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.app-header-icon { font-size: 3rem; line-height: 1; }
.app-header h1 {
    color: #F1F5F9 !important;
    font-size: 1.85rem;
    font-weight: 800;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.02em;
}
.app-header p {
    color: #64B5F6 !important;
    margin: 0;
    font-size: 0.92rem;
    font-weight: 400;
}

/* ═══════════════════════════════════════════════════════════════
   SECTION TITLES
═══════════════════════════════════════════════════════════════ */
.sec-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-color);
    margin: 2rem 0 1rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #4A6CF7;
}

/* ═══════════════════════════════════════════════════════════════
   AGENT CARDS
═══════════════════════════════════════════════════════════════ */
.agent-card {
    border-radius: 14px;
    padding: 1.4rem 1.5rem;
    height: 100%;
    border: 1px solid rgba(255,255,255,0.06);
    position: relative;
    overflow: hidden;
}
.agent-card-tenant   { background: linear-gradient(145deg, #0F2744, #0D1B2A); }
.agent-card-landlord { background: linear-gradient(145deg, #1A1A2E, #16213E); }
.agent-card-insurer  { background: linear-gradient(145deg, #0D2137, #0A1628); }

.agent-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.agent-card-tenant::before   { background: linear-gradient(90deg, #4A6CF7, #60A5FA); }
.agent-card-landlord::before { background: linear-gradient(90deg, #8B5CF6, #A78BFA); }
.agent-card-insurer::before  { background: linear-gradient(90deg, #06B6D4, #22D3EE); }

.agent-card-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #F1F5F9 !important;
    margin-bottom: 0.7rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.agent-card-desc {
    font-size: 0.78rem;
    color: #94A3B8 !important;
    margin: 0.5rem 0 0.8rem 0;
    line-height: 1.5;
}
.agent-card-stat {
    font-size: 0.82rem;
    color: #CBD5E1 !important;
    margin: 0;
}
.agent-card-stat strong {
    color: #F1F5F9 !important;
}

/* ═══════════════════════════════════════════════════════════════
   STATUS BADGES
═══════════════════════════════════════════════════════════════ */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.25rem 0.8rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin-bottom: 0.8rem;
}
.badge-ok         { background: #064E3B; color: #6EE7B7 !important; border: 1px solid #065F46; }
.badge-overridden { background: #1E3A5F; color: #93C5FD !important; border: 1px solid #1D4ED8; }
.badge-failed     { background: #450A0A; color: #FCA5A5 !important; border: 1px solid #7F1D1D; }
.badge-skipped    { background: #422006; color: #FCD34D !important; border: 1px solid #78350F; }
.badge-unknown    { background: #1E293B; color: #94A3B8 !important; border: 1px solid #334155; }

/* ═══════════════════════════════════════════════════════════════
   METRICS ROW
═══════════════════════════════════════════════════════════════ */
.metric-card {
    background: #1E293B;
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    text-align: center;
    border: 1px solid #334155;
}
.metric-card-value {
    font-size: 2rem;
    font-weight: 800;
    color: #F1F5F9 !important;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.metric-card-label {
    font-size: 0.75rem;
    color: #64748B !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.metric-passed  .metric-card-value { color: #34D399 !important; }
.metric-failed  .metric-card-value { color: #F87171 !important; }
.metric-skipped .metric-card-value { color: #FBBF24 !important; }
.metric-override .metric-card-value { color: #60A5FA !important; }

/* ═══════════════════════════════════════════════════════════════
   DECISION BANNERS
═══════════════════════════════════════════════════════════════ */
.decision-banner {
    border-radius: 14px;
    padding: 1.5rem 1.8rem;
    margin-top: 0.5rem;
    border: 1px solid;
}
.decision-approved {
    background: linear-gradient(135deg, #052E16, #064E3B);
    border-color: #065F46;
}
.decision-rejected {
    background: linear-gradient(135deg, #2D0A0A, #450A0A);
    border-color: #7F1D1D;
}
.decision-title {
    font-size: 1.15rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.decision-approved .decision-title { color: #6EE7B7 !important; }
.decision-rejected .decision-title { color: #FCA5A5 !important; }
.decision-reason {
    font-size: 0.88rem;
    line-height: 1.65;
}
.decision-approved .decision-reason { color: #A7F3D0 !important; }
.decision-rejected .decision-reason { color: #FECACA !important; }
.decision-ts {
    font-size: 0.75rem;
    margin-top: 0.7rem;
    opacity: 0.6;
}
.decision-approved .decision-ts { color: #6EE7B7 !important; }
.decision-rejected .decision-ts { color: #FCA5A5 !important; }

/* ═══════════════════════════════════════════════════════════════
   OVERRIDE LOG
═══════════════════════════════════════════════════════════════ */
.log-wrap {
    background: #0F172A;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    border: 1px solid #1E293B;
}
.log-entry {
    display: flex;
    align-items: flex-start;
    gap: 0.8rem;
    padding: 0.7rem 0;
    border-bottom: 1px solid #1E293B;
}
.log-entry:last-child { border-bottom: none; }
.log-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #4A6CF7;
    margin-top: 0.35rem;
    flex-shrink: 0;
}
.log-action {
    font-size: 0.8rem;
    font-weight: 700;
    color: #93C5FD !important;
}
.log-stage {
    font-size: 0.78rem;
    color: #64748B !important;
}
.log-comment {
    font-size: 0.8rem;
    color: #CBD5E1 !important;
    margin-top: 0.15rem;
    font-style: italic;
}
.log-ts {
    font-size: 0.72rem;
    color: #475569 !important;
    margin-top: 0.15rem;
}

/* ═══════════════════════════════════════════════════════════════
   APPROVAL GATE
═══════════════════════════════════════════════════════════════ */
.gate-wrap {
    background: #0F172A;
    border-radius: 14px;
    padding: 1.6rem 1.8rem;
    border: 1px solid #1E293B;
    margin-top: 0.5rem;
}
.gate-intro {
    font-size: 0.88rem;
    color: #94A3B8 !important;
    line-height: 1.6;
    margin-bottom: 1.2rem;
}

/* Radio label fix */
[data-testid="stRadio"] label {
    color: var(--text-color) !important;
    font-size: 0.88rem !important;
}
[data-testid="stRadio"] > div {
    gap: 0.5rem !important;
}

/* Textarea */
[data-testid="stTextArea"] textarea {
    background: #1E293B !important;
    color: #F1F5F9 !important;
    border: 1.5px solid #334155 !important;
    border-radius: 10px !important;
    font-size: 0.88rem !important;
}
[data-testid="stTextArea"] textarea::placeholder {
    color: #475569 !important;
}
[data-testid="stTextArea"] label {
    color: #94A3B8 !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
}

/* Primary form button */
[data-testid="stForm"] .stButton > button[kind="primaryFormSubmit"],
[data-testid="stForm"] button[type="submit"] {
    background: linear-gradient(135deg, #4A6CF7, #6A3DE8) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 1.4rem !important;
    box-shadow: 0 4px 14px rgba(74,108,247,0.4) !important;
    transition: opacity 0.2s !important;
}
[data-testid="stForm"] .stButton > button[kind="primaryFormSubmit"]:hover {
    opacity: 0.88 !important;
}

/* ═══════════════════════════════════════════════════════════════
   CONFIRMATION BANNER
═══════════════════════════════════════════════════════════════ */
.confirm-approved {
    background: linear-gradient(135deg, #052E16, #064E3B);
    border: 1px solid #065F46;
    border-radius: 14px;
    padding: 1.4rem 1.8rem;
    color: #6EE7B7 !important;
    font-size: 1rem;
    font-weight: 700;
}
.confirm-rejected {
    background: linear-gradient(135deg, #2D0A0A, #450A0A);
    border: 1px solid #7F1D1D;
    border-radius: 14px;
    padding: 1.4rem 1.8rem;
    color: #FCA5A5 !important;
    font-size: 1rem;
    font-weight: 700;
}
.confirm-note {
    font-size: 0.85rem;
    font-weight: 400;
    margin-top: 0.5rem;
    opacity: 0.85;
}

/* ═══════════════════════════════════════════════════════════════
   EMPTY STATE
═══════════════════════════════════════════════════════════════ */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    background: #0F172A;
    border-radius: 16px;
    border: 1.5px dashed #1E293B;
    margin-top: 1rem;
}
.empty-state-icon { font-size: 3.5rem; margin-bottom: 1rem; }
.empty-state-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #CBD5E1 !important;
    margin-bottom: 0.5rem;
}
.empty-state-sub {
    font-size: 0.88rem;
    color: #475569 !important;
    line-height: 1.6;
}
.empty-state-sub strong { color: #64748B !important; }

/* ═══════════════════════════════════════════════════════════════
   EXPANDER OVERRIDES
═══════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    color: #CBD5E1 !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}
[data-testid="stExpander"] summary:hover {
    color: #F1F5F9 !important;
}
[data-testid="stExpander"] p,
[data-testid="stExpander"] li,
[data-testid="stExpander"] span {
    color: #CBD5E1 !important;
    font-size: 0.85rem !important;
}

/* ═══════════════════════════════════════════════════════════════
   PROGRESS BAR TEXT
═══════════════════════════════════════════════════════════════ */
[data-testid="stStatusWidget"] {
    color: #CBD5E1 !important;
}

/* ═══════════════════════════════════════════════════════════════
   METRIC WIDGET NATIVE
═══════════════════════════════════════════════════════════════ */
[data-testid="stMetric"] {
    background: #1E293B;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    border: 1px solid #334155;
}
[data-testid="stMetricLabel"] {
    color: #64748B !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
    color: #F1F5F9 !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
}

/* Global link colour */
a { color: #60A5FA !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session State
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "validation_result":  None,
    "approval_payload":   None,
    "validation_started": False,
    "pdf_bytes":          None,
    "pdf_name":           None,
    "pipeline_state":     None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

_OK_SET = {"OK", "OK_OVERRIDDEN"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def status_badge(status: str) -> str:
    mapping = {
        "OK":            ("badge-ok",         "✔ PASSED"),
        "OK_OVERRIDDEN": ("badge-overridden",  "⚡ OVERRIDDEN"),
        "FAILED":        ("badge-failed",      "✘ FAILED"),
        "SKIPPED":       ("badge-skipped",     "⊘ SKIPPED"),
    }
    cls, label = mapping.get(status, ("badge-unknown", status or "UNKNOWN"))
    return f"<span class='badge {cls}'>{label}</span>"


def _reset():
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1.2rem 0 0.8rem">
        <div style="font-size:2.4rem;margin-bottom:0.4rem">📋</div>
        <div style="font-size:1rem;font-weight:800;color:#F1F5F9">Rental Agreement</div>
        <div style="font-size:0.75rem;color:#475569;margin-top:0.2rem">
            Multi-Agent Validator
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown(
        "<p style='font-size:0.78rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:.06em;margin-bottom:.4rem'>"
        "📂 Upload Document</p>",
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "PDF", type=["pdf"], label_visibility="collapsed"
    )

    st.markdown(
        "<p style='font-size:0.78rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:.06em;"
        "margin-bottom:.4rem;margin-top:.8rem'>"
        "🤖 AI Model</p>",
        unsafe_allow_html=True,
    )
    model_options = get_installed_ollama_models()
    model_name = st.selectbox(
        "Model", label_visibility="collapsed",
        options=model_options if model_options else ["llama3.2:latest"],
        index=0,
    )
    if not model_options:
        st.markdown(
            "<p style='font-size:0.75rem;color:#F59E0B;margin-top:.3rem'>"
            "⚠️ No Ollama models detected.</p>",
            unsafe_allow_html=True,
        )

    st.divider()
    run_button = st.button("🚀  Run Validation Workflow", type="primary")

    st.divider()
    st.markdown(
        "<p style='font-size:0.78rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:.06em;margin-bottom:.5rem'>"
        "Pipeline Stages</p>",
        unsafe_allow_html=True,
    )
    for step in [
        ("📄", "PDF Extraction"),
        ("👤", "Tenant Validation"),
        ("🏠", "Landlord Compliance"),
        ("🛡️", "Insurer Validation"),
        ("⚖️", "Decision Agent"),
        ("🔏", "Human Approval Gate"),
    ]:
        st.markdown(
            f"<div class='wf-step'>"
            f"<div class='wf-dot'></div>"
            f"<span>{step[0]} {step[1]}</span></div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="app-header">
    <div class="app-header-icon">📋</div>
    <div>
        <h1>Rental Agreement Validator</h1>
        <p>Multi-agent AI pipeline &nbsp;·&nbsp; Tenant &nbsp;·&nbsp;
           Landlord &nbsp;·&nbsp; Insurer &nbsp;·&nbsp; Human Approval Gate</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Run Button Handler
# ---------------------------------------------------------------------------
if run_button:
    if uploaded_file is None:
        st.error("⚠️ Please upload a PDF rental agreement before running.")
    else:
        st.session_state.pdf_bytes          = uploaded_file.read()
        st.session_state.pdf_name           = uploaded_file.name
        st.session_state.validation_started = True
        st.session_state.validation_result  = None
        st.session_state.approval_payload   = None
        st.session_state.pipeline_state     = None
        st.rerun()

# ---------------------------------------------------------------------------
# Pipeline Execution Block
# ---------------------------------------------------------------------------
if st.session_state.validation_started and st.session_state.validation_result is None:

    st.markdown(
        "<div class='sec-title'>⚙️ Running Validation Pipeline</div>",
        unsafe_allow_html=True,
    )

    with st.status("Initialising pipeline…", expanded=True) as live:
        progress_bar = st.progress(0)

        def progress_callback(pct: int, msg: str) -> None:
            live.update(label=msg)
            progress_bar.progress(pct, text=msg)

        try:
            result = run_document_validation(
                pdf_bytes         = st.session_state.pdf_bytes,
                filename          = st.session_state.pdf_name,
                model_name        = model_name,
                progress_callback = progress_callback,
                initial_state     = st.session_state.pipeline_state,
            )
            st.session_state.validation_result = result
            st.session_state.pipeline_state    = {
                k: v for k, v in result.items() if k != "result"
            }
            progress_bar.progress(100, text="✅ All agents complete!")
            live.update(label="✅ Validation pipeline complete!", state="complete")

        except Exception as exc:
            live.update(label=f"❌ Pipeline failed: {exc}", state="error")
            st.error(f"❌ Processing failed: {exc}")
            st.session_state.validation_started = False
            st.stop()

    st.rerun()

# ---------------------------------------------------------------------------
# Results Display
# ---------------------------------------------------------------------------
if st.session_state.validation_result is not None:
    result = st.session_state.validation_result["result"]

    t_status = result.get("tenant_status",   "UNKNOWN")
    l_status = result.get("landlord_status", "UNKNOWN")
    i_status = result.get("insurer_status",  "UNKNOWN")
    decision = result.get("decision",        "REJECTED")
    reason   = result.get("reason",          "No reason provided.")
    proc_at  = result.get("processed_at",    "")

    # ── Agent Cards ──────────────────────────────────────────────────────
    st.markdown(
        "<div class='sec-title'>📊 Validation Stage Results</div>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3, gap="medium")

    # — Tenant —
    with col1:
        det     = result.get("details", {}).get("tenant", {})
        missing = det.get("missing", [])
        found   = det.get("found",   [])
        st.markdown(f"""
        <div class="agent-card agent-card-tenant">
            <div class="agent-card-title">👤 Tenant Agent</div>
            {status_badge(t_status)}
            <div class="agent-card-desc">
                Verifies all required clauses are present and adequately addressed.
            </div>
            <div class="agent-card-stat">
                <strong>{len(found)}</strong> clause(s) found &nbsp;·&nbsp;
                <strong>{len(missing)}</strong> missing
            </div>
        </div>""", unsafe_allow_html=True)
        with st.expander("View Tenant Details"):
            if found:
                st.markdown("**✅ Clauses Found**")
                for c in found:
                    st.markdown(f"- {c}")
            if missing:
                st.markdown("**❌ Missing Clauses**")
                for c in missing:
                    st.markdown(f"- {c}")
            if not found and not missing:
                st.caption("No detail data returned.")

    # — Landlord —
    with col2:
        l_issues = result.get("details", {}).get("landlord", {}).get("issues", [])
        st.markdown(f"""
        <div class="agent-card agent-card-landlord">
            <div class="agent-card-title">🏠 Landlord Agent</div>
            {status_badge(l_status)}
            <div class="agent-card-desc">
                Reviews dates, signatures, red flags, and legal compliance.
            </div>
            <div class="agent-card-stat">
                <strong>{len(l_issues)}</strong> issue(s) identified
            </div>
        </div>""", unsafe_allow_html=True)
        with st.expander("View Landlord Details"):
            if l_issues:
                st.markdown("**⚠️ Issues Found**")
                for i in l_issues:
                    st.markdown(f"- {i}")
            else:
                st.success("No issues found.")

    # — Insurer —
    with col3:
        i_issues = result.get("details", {}).get("insurer", {}).get("issues", [])
        st.markdown(f"""
        <div class="agent-card agent-card-insurer">
            <div class="agent-card-title">🛡️ Insurer Agent</div>
            {status_badge(i_status)}
            <div class="agent-card-desc">
                Validates signatures, property details, and liability clauses.
            </div>
            <div class="agent-card-stat">
                <strong>{len(i_issues)}</strong> issue(s) identified
            </div>
        </div>""", unsafe_allow_html=True)
        with st.expander("View Insurer Details"):
            if i_issues:
                st.markdown("**⚠️ Issues Found**")
                for i in i_issues:
                    st.markdown(f"- {i}")
            else:
                st.success("No issues found.")

    # ── Pipeline Summary ─────────────────────────────────────────────────
    st.markdown(
        "<div class='sec-title'>📈 Pipeline Summary</div>",
        unsafe_allow_html=True,
    )
    all_s    = [t_status, l_status, i_status]
    passed   = sum(1 for s in all_s if s in _OK_SET)
    failed   = sum(1 for s in all_s if s == "FAILED")
    skipped  = sum(1 for s in all_s if s == "SKIPPED")
    override = sum(1 for s in all_s if s == "OK_OVERRIDDEN")

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("Stages Run",    "3")
    mc2.metric("✅ Passed",     str(passed))
    mc3.metric("❌ Failed",     str(failed))
    mc4.metric("⊘ Skipped",    str(skipped))
    mc5.metric("⚡ Overridden", str(override))

    # ── System Decision ──────────────────────────────────────────────────
    st.markdown(
        "<div class='sec-title'>⚖️ System Decision</div>",
        unsafe_allow_html=True,
    )
    ts_html = (
        f"<div class='decision-ts'>Processed: {proc_at}</div>"
        if proc_at else ""
    )
    if decision == "APPROVED":
        st.markdown(f"""
        <div class="decision-banner decision-approved">
            <div class="decision-title">✅ Document APPROVED</div>
            <div class="decision-reason">{reason}</div>
            {ts_html}
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="decision-banner decision-rejected">
            <div class="decision-title">❌ Document REJECTED</div>
            <div class="decision-reason">{reason}</div>
            {ts_html}
        </div>""", unsafe_allow_html=True)

    # ── Override Log ─────────────────────────────────────────────────────
    override_log = result.get("override_log", [])
    if override_log:
        st.markdown(
            "<div class='sec-title'>📜 Override History</div>",
            unsafe_allow_html=True,
        )
        entries_html = ""
        for entry in override_log:
            entries_html += f"""
            <div class="log-entry">
                <div class="log-dot"></div>
                <div>
                    <div class="log-action">{entry.get('action','')}</div>
                    <div class="log-stage">Stage: {entry.get('stage','—')}</div>
                    <div class="log-comment">"{entry.get('comment','')}"</div>
                    <div class="log-ts">{entry.get('timestamp','')}</div>
                </div>
            </div>"""
        st.markdown(
            f"<div class='log-wrap'>{entries_html}</div>",
            unsafe_allow_html=True,
        )

    # ── Human Approval Gate ──────────────────────────────────────────────
    st.markdown(
        "<div class='sec-title'>🔏 Human Approval Gate</div>",
        unsafe_allow_html=True,
    )
    st.markdown("""
    <div class="gate-wrap">
        <div class="gate-intro">
            Review each agent's outcome below. You may
            <strong style="color:#6EE7B7">APPROVE</strong> or
            <strong style="color:#FCA5A5">REJECT</strong> the document,
            <strong style="color:#93C5FD">OVERRIDE</strong> a failed stage
            to force the pipeline forward, or
            <strong style="color:#FBBF24">REVERT</strong> to re-run a
            previous stage from scratch. A reviewer comment is required
            for all actions.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Build available actions
    landlord_done = l_status not in ("UNKNOWN", "SKIPPED", None)
    insurer_done  = i_status not in ("UNKNOWN", "SKIPPED", None)

    available_actions = ["APPROVE", "REJECT"]
    if t_status == "FAILED":
        available_actions.append("OVERRIDE Tenant → Proceed to Landlord")
    if t_status in _OK_SET and l_status == "FAILED":
        available_actions.append("OVERRIDE Landlord → Proceed to Insurer")
    if t_status in _OK_SET and l_status in _OK_SET and i_status == "FAILED":
        available_actions.append("OVERRIDE Insurer → Final Approve")
    if landlord_done:
        available_actions.append("REVERT → Re-run Tenant Agent")
    if insurer_done:
        available_actions.append("REVERT → Re-run Landlord Agent")

    with st.form("approval_gate_form"):

        # Action labels with colour hints
        action_labels = {
            "APPROVE":                              "✅  APPROVE — Accept the document",
            "REJECT":                               "❌  REJECT — Decline the document",
            "OVERRIDE Tenant → Proceed to Landlord":"⚡  OVERRIDE Tenant → Proceed to Landlord",
            "OVERRIDE Landlord → Proceed to Insurer":"⚡  OVERRIDE Landlord → Proceed to Insurer",
            "OVERRIDE Insurer → Final Approve":     "⚡  OVERRIDE Insurer → Final Approve",
            "REVERT → Re-run Tenant Agent":         "↩️  REVERT → Re-run Tenant Agent",
            "REVERT → Re-run Landlord Agent":       "↩️  REVERT → Re-run Landlord Agent",
        }
        display_options = [action_labels.get(a, a) for a in available_actions]

        st.markdown(
            "<p style='font-size:0.82rem;font-weight:700;color:#94A3B8;"
            "text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem'>"
            "Select Action</p>",
            unsafe_allow_html=True,
        )
        selected_display = st.radio(
            "Action",
            options=display_options,
            index=0,
            label_visibility="collapsed",
        )
        # Map display label back to action key
        selected_action = available_actions[display_options.index(selected_display)]

        st.markdown(
            "<p style='font-size:0.82rem;font-weight:700;color:#94A3B8;"
            "text-transform:uppercase;letter-spacing:.05em;"
            "margin-top:1rem;margin-bottom:.4rem'>"
            "Reviewer Comments <span style='color:#F87171'>*</span></p>",
            unsafe_allow_html=True,
        )
        comments = st.text_area(
            "Comments",
            placeholder=(
                "Provide justification for your decision, override reasoning, "
                "or notes for the audit record…"
            ),
            height=120,
            label_visibility="collapsed",
        )

        col_btn, _ = st.columns([1, 3])
        with col_btn:
            submitted = st.form_submit_button(
                "✅  Confirm Action",
                type="primary",
                use_container_width=True,
            )

    if submitted:
        if not comments.strip():
            st.warning("⚠️ Reviewer comments are required before confirming.")
            st.stop()

        ts = datetime.utcnow().isoformat() + "Z"

        # ── APPROVE / REJECT ─────────────────────────────────────────────
        if selected_action in ("APPROVE", "REJECT"):
            payload = save_approval_gate(
                st.session_state.validation_result,
                selected_action,
                comments,
            )
            st.session_state.approval_payload = payload
            st.rerun()

        # ── OVERRIDE ─────────────────────────────────────────────────────
        elif "OVERRIDE" in selected_action:
            ps        = dict(st.session_state.pipeline_state or {})
            log_entry = {
                "action":    selected_action,
                "comment":   comments,
                "timestamp": ts,
            }
            if "Tenant" in selected_action:
                log_entry["stage"] = "Tenant"
                ps["tenant_status"]          = "OK_OVERRIDDEN"
                ps["tenant_missing_clauses"] = []
                ps["tenant_found_clauses"]   = (
                    ps.get("tenant_found_clauses", [])
                    + ps.get("tenant_missing_clauses", [])
                )
                for k in ("landlord_status","landlord_issues",
                          "insurer_status","insurer_issues"):
                    ps.pop(k, None)

            elif "Landlord" in selected_action:
                log_entry["stage"] = "Landlord"
                ps["landlord_status"] = "OK_OVERRIDDEN"
                ps["landlord_issues"] = []
                for k in ("insurer_status","insurer_issues"):
                    ps.pop(k, None)

            elif "Insurer" in selected_action:
                log_entry["stage"] = "Insurer"
                ps["insurer_status"] = "OK_OVERRIDDEN"
                ps["insurer_issues"] = []

            ps.setdefault("override_log", []).append(log_entry)
            st.session_state.pipeline_state     = ps
            st.session_state.validation_started = True
            st.session_state.validation_result  = None
            st.rerun()

        # ── REVERT ───────────────────────────────────────────────────────
        elif "REVERT" in selected_action:
            ps        = dict(st.session_state.pipeline_state or {})
            log_entry = {
                "action":    selected_action,
                "comment":   comments,
                "timestamp": ts,
            }
            if "Tenant" in selected_action:
                log_entry["stage"] = "Tenant (revert)"
                for k in ("tenant_status","tenant_missing_clauses",
                          "tenant_found_clauses","landlord_status",
                          "landlord_issues","insurer_status","insurer_issues"):
                    ps.pop(k, None)
            elif "Landlord" in selected_action:
                log_entry["stage"] = "Landlord (revert)"
                for k in ("landlord_status","landlord_issues",
                          "insurer_status","insurer_issues"):
                    ps.pop(k, None)

            ps.setdefault("override_log", []).append(log_entry)
            st.session_state.pipeline_state     = ps
            st.session_state.validation_started = True
            st.session_state.validation_result  = None
            st.rerun()

# ---------------------------------------------------------------------------
# Approval Confirmation
# ---------------------------------------------------------------------------
if st.session_state.approval_payload is not None:
    ap          = st.session_state.approval_payload.get("approval_gate", {})
    final_dec   = ap.get("decision",    "")
    final_cmt   = ap.get("comments",    "")
    reviewed_at = ap.get("reviewed_at", "")

    st.markdown(
        "<div class='sec-title'>✅ Final Decision Recorded</div>",
        unsafe_allow_html=True,
    )

    if final_dec == "APPROVE":
        st.markdown(f"""
        <div class="confirm-approved">
            ✅ Decision saved: <strong>APPROVED</strong>
            <div class="confirm-note">Reviewed at: {reviewed_at}</div>
            {f'<div class="confirm-note">💬 "{final_cmt}"</div>' if final_cmt else ''}
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="confirm-rejected">
            ❌ Decision saved: <strong>REJECTED</strong>
            <div class="confirm-note">Reviewed at: {reviewed_at}</div>
            {f'<div class="confirm-note">💬 "{final_cmt}"</div>' if final_cmt else ''}
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📄 Full Approval Record (JSON)"):
        st.json(st.session_state.approval_payload)

    if st.button("🔄 Start New Validation", type="primary"):
        _reset()
        st.rerun()

# ---------------------------------------------------------------------------
# Empty State
# ---------------------------------------------------------------------------
if (
    not st.session_state.validation_started
    and st.session_state.validation_result is None
    and st.session_state.approval_payload is None
):
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">📂</div>
        <div class="empty-state-title">No document loaded yet</div>
        <div class="empty-state-sub">
            Upload a rental agreement PDF using the sidebar file uploader,<br>
            select your Ollama model, then click
            <strong>Run Validation Workflow</strong> to begin.
        </div>
    </div>
    """, unsafe_allow_html=True)