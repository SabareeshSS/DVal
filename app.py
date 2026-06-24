import streamlit as st
from main import (
    run_document_validation,
    save_approval_gate,
    get_installed_ollama_models,
)

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Rental Agreement Validator",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] .stButton > button {
        background: #4A6CF7; color: #fff !important;
        border: none; border-radius: 8px;
        padding: 0.55rem 1.2rem; font-weight: 600;
        width: 100%; transition: background 0.2s;
    }
    [data-testid="stSidebar"] .stButton > button:hover { background: #3A5CE5; }

    .app-header {
        background: linear-gradient(135deg,#1C2340 0%,#2E3D7A 100%);
        border-radius: 14px; padding: 2rem 2.5rem;
        margin-bottom: 1.8rem; display: flex;
        align-items: center; gap: 1.2rem;
    }
    .app-header h1 { color:#fff; font-size:1.9rem; font-weight:700; margin:0; }
    .app-header p  { color:#A8B8D8; margin:0.3rem 0 0; font-size:0.95rem; }

    .section-title {
        font-size:1.15rem; font-weight:700; color: var(--text-color);
        margin:1.6rem 0 0.8rem; display:flex; align-items:center; gap:0.5rem;
    }

    .agent-card {
        background: var(--secondary-background-color); border-radius:12px; padding:1.4rem 1.6rem;
        box-shadow:0 2px 12px rgba(0,0,0,.08); height:100%;
    }
    .agent-card-title {
        font-size:1rem; font-weight:700; color: var(--text-color);
        margin-bottom:0.8rem; display:flex; align-items:center; gap:0.45rem;
    }

    .badge {
        display:inline-block; padding:0.28rem 0.85rem; border-radius:20px;
        font-size:0.8rem; font-weight:700; letter-spacing:0.04em; margin-bottom:0.9rem;
    }
    .badge-ok      { background:#D1FAE5; color:#065F46; }
    .badge-failed  { background:#FEE2E2; color:#991B1B; }
    .badge-skipped { background:#FEF9C3; color:#854D0E; }
    .badge-unknown { background:#E5E7EB; color:#374151; }

    .decision-approved {
        background:linear-gradient(135deg,#D1FAE5,#A7F3D0);
        border-left:5px solid #059669; border-radius:10px;
        padding:1.2rem 1.6rem; color:#065F46;
    }
    .decision-rejected {
        background:linear-gradient(135deg,#FEE2E2,#FECACA);
        border-left:5px solid #DC2626; border-radius:10px;
        padding:1.2rem 1.6rem; color:#991B1B;
    }
    .decision-title  { font-size:1.2rem; font-weight:700; margin-bottom:0.4rem; }
    .decision-reason { font-size:0.92rem; line-height:1.55; }

    .approval-card {
        background: var(--secondary-background-color); border-radius:12px; padding:1.8rem 2rem;
        box-shadow:0 2px 12px rgba(0,0,0,.08); margin-top:1rem;
    }

    .workflow-step {
        display:flex; align-items:center; gap:0.7rem;
        padding:0.5rem 0; font-size:0.88rem; color: var(--text-color);
    }
    .step-dot {
        width:10px; height:10px; border-radius:50%;
        background:#4A6CF7; flex-shrink:0;
    }

    hr { border-color:#E5E7EB; }
    .stExpander { border-radius:8px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session State
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "validation_result": None,
    "approval_payload": None,
    "validation_started": False,
    "pdf_bytes": None,
    "pdf_name": None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<div style='text-align:center;padding:1rem 0 0.5rem'>"
        "<span style='font-size:2.2rem'>📋</span>"
        "<p style='font-size:1.05rem;font-weight:700;margin:0.4rem 0 0'>"
        "Rental Agreement</p>"
        "<p style='font-size:0.8rem;opacity:0.7;margin:0'>"
        "Multi-Agent Validator</p></div>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("**📂 Upload Document**")
    uploaded_file = st.file_uploader(
        "Rental Agreement PDF",
        type=["pdf"],
        label_visibility="collapsed",
    )

    st.markdown("**🤖 AI Model**")
    model_options = get_installed_ollama_models()
    model_name = st.selectbox(
        "Ollama Model",
        options=model_options if model_options else ["llama3.2:latest"],
        index=0,
        label_visibility="collapsed",
    )
    if not model_options:
        st.caption("⚠️ No Ollama models detected. Ensure Ollama is running.")

    st.divider()
    run_button = st.button("🚀 Run Validation Workflow", type="primary")

    st.divider()
    st.markdown("**Workflow Pipeline**")
    for step in [
        "PDF Text Extraction",
        "Tenant Clause Validation",
        "Landlord Compliance Check",
        "Insurer Signature & Coverage",
        "Decision Agent",
        "Human Approval Gate",
    ]:
        st.markdown(
            f"<div class='workflow-step'>"
            f"<div class='step-dot'></div>{step}</div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="app-header">
        <span style="font-size:2.8rem">📋</span>
        <div>
            <h1>Rental Agreement Validator</h1>
            <p>Multi-agent AI pipeline · Tenant · Landlord · Insurer · Approval Gate</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Handle Run Button
# ---------------------------------------------------------------------------
if run_button:
    if uploaded_file is None:
        st.error("⚠️ Please upload a PDF rental agreement before running the workflow.")
    else:
        # Snapshot the bytes NOW — before Streamlit re-runs and loses the widget
        st.session_state.pdf_bytes = uploaded_file.read()
        st.session_state.pdf_name = uploaded_file.name
        st.session_state.validation_started = True
        st.session_state.validation_result = None
        st.session_state.approval_payload = None
        st.rerun()

# ---------------------------------------------------------------------------
# Run Validation Pipeline
# ---------------------------------------------------------------------------
if st.session_state.validation_started and st.session_state.validation_result is None:

    st.markdown(
        "<div class='section-title'>⚙️ Running Validation Pipeline</div>",
        unsafe_allow_html=True,
    )

    # ── Live status container ────────────────────────────────────────────
    # st.status keeps the spinner open and lets us write live updates
    # into it while the blocking LLM calls run on the main thread.
    with st.status("Starting validation pipeline…", expanded=True) as live:

        progress_bar = st.progress(0)

        def progress_callback(pct: int, msg: str) -> None:
            """
            Called from main.py IMMEDIATELY BEFORE each blocking agent call.
            Because this runs synchronously on the same thread, Streamlit
            flushes the update to the browser before the LLM blocks.
            """
            live.update(label=msg)
            progress_bar.progress(pct, text=msg)

        try:
            result = run_document_validation(
                st.session_state.pdf_bytes,
                st.session_state.pdf_name,
                model_name=model_name,
                progress_callback=progress_callback,
            )
            st.session_state.validation_result = result
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

    # ── Badge helper ─────────────────────────────────────────────────────
    def status_badge(status: str) -> str:
        cls = {
            "OK": "badge-ok",
            "FAILED": "badge-failed",
            "SKIPPED": "badge-skipped",
        }.get(status, "badge-unknown")
        label = {
            "OK": "✔ PASSED",
            "FAILED": "✘ FAILED",
            "SKIPPED": "⊘ SKIPPED",
        }.get(status, status)
        return f"<span class='badge {cls}'>{label}</span>"

    # ── Agent Cards ──────────────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>📊 Validation Stage Results</div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3, gap="medium")

    # — Tenant —
    with col1:
        t_status = result.get("tenant_status", "UNKNOWN")
        tenant_det = result.get("details", {}).get("tenant", {})
        missing = tenant_det.get("missing", [])
        found = tenant_det.get("found", [])

        st.markdown(
            f"""
            <div class="agent-card">
                <div class="agent-card-title">👤 Tenant Agent</div>
                {status_badge(t_status)}
                <p style="font-size:0.82rem;opacity:0.7;margin:0 0 0.6rem">
                    Checks required clauses are present and adequately addressed.
                </p>
                <p style="font-size:0.85rem;margin:0">
                    <strong>{len(found)}</strong> clause(s) found &nbsp;·&nbsp;
                    <strong>{len(missing)}</strong> missing
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
        l_status = result.get("landlord_status", "UNKNOWN")
        landlord_issues = result.get("details", {}).get("landlord", {}).get("issues", [])

        st.markdown(
            f"""
            <div class="agent-card">
                <div class="agent-card-title">🏠 Landlord Agent</div>
                {status_badge(l_status)}
                <p style="font-size:0.82rem;opacity:0.7;margin:0 0 0.6rem">
                    Reviews dates, signatures, red flags, and legal compliance.
                </p>
                <p style="font-size:0.85rem;margin:0">
                    <strong>{len(landlord_issues)}</strong> issue(s) identified
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("View Landlord Details"):
            if landlord_issues:
                st.markdown("**⚠️ Issues Found**")
                for issue in landlord_issues:
                    st.markdown(f"- {issue}")
            else:
                st.success("No issues found.")

    # — Insurer —
    with col3:
        i_status = result.get("insurer_status", "UNKNOWN")
        insurer_issues = result.get("details", {}).get("insurer", {}).get("issues", [])

        st.markdown(
            f"""
            <div class="agent-card">
                <div class="agent-card-title">🛡️ Insurer Agent</div>
                {status_badge(i_status)}
                <p style="font-size:0.82rem;opacity:0.7;margin:0 0 0.6rem">
                    Validates signatures, property details, and liability clauses.
                </p>
                <p style="font-size:0.85rem;margin:0">
                    <strong>{len(insurer_issues)}</strong> issue(s) identified
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("View Insurer Details"):
            if insurer_issues:
                st.markdown("**⚠️ Issues Found**")
                for issue in insurer_issues:
                    st.markdown(f"- {issue}")
            else:
                st.success("No issues found.")

    # ── Pipeline Summary Metrics ─────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>📈 Pipeline Summary</div>",
        unsafe_allow_html=True,
    )
    all_statuses = [t_status, l_status, i_status]
    passed  = sum(1 for s in all_statuses if s == "OK")
    failed  = sum(1 for s in all_statuses if s == "FAILED")
    skipped = sum(1 for s in all_statuses if s == "SKIPPED")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Stages Run", 3)
    m2.metric("✅ Passed",  passed)
    m3.metric("❌ Failed",  failed)
    m4.metric("⊘ Skipped", skipped)

    # ── Final Decision ───────────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>⚖️ System Decision</div>",
        unsafe_allow_html=True,
    )
    decision     = result.get("decision", "REJECTED")
    reason       = result.get("reason", "No reason provided.")
    processed_at = result.get("processed_at", "")
    ts_html = (
        f"<p style='margin:0.6rem 0 0;font-size:0.8rem;opacity:0.75'>"
        f"Processed: {processed_at}</p>"
        if processed_at else ""
    )

    if decision == "APPROVED":
        st.markdown(
            f"""
            <div class="decision-approved">
                <div class="decision-title">✅ Document APPROVED</div>
                <div class="decision-reason">{reason}</div>
                {ts_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="decision-rejected">
                <div class="decision-title">❌ Document REJECTED</div>
                <div class="decision-reason">{reason}</div>
                {ts_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Human Approval Gate ──────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>🔏 Human Approval Gate</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='opacity:0.8;font-size:0.9rem;margin-top:-0.4rem'>"
        "Review the system decision and submit your final ruling. "
        "You may override the system recommendation with a written justification."
        "</p>",
        unsafe_allow_html=True,
    )

    with st.form("approval_form"):
        default_idx = 0 if decision == "APPROVED" else 1
        approval_decision = st.radio(
            "**Final Action**",
            options=["APPROVE", "REJECT"],
            index=default_idx,
            horizontal=True,
        )
        comments = st.text_area(
            "**Reviewer Comments**",
            placeholder=(
                "Add override justification, notes for the record, "
                "or any additional observations here…"
            ),
            height=110,
        )
        col_submit, _ = st.columns([1, 3])
        with col_submit:
            submitted = st.form_submit_button(
                "✅ Confirm & Save Decision",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not comments.strip():
                st.warning("⚠️ Please add a reviewer comment before confirming.")
            else:
                payload = save_approval_gate(
                    st.session_state.validation_result,
                    approval_decision,
                    comments,
                )
                st.session_state.approval_payload = payload
                st.rerun()

# ---------------------------------------------------------------------------
# Approval Confirmation
# ---------------------------------------------------------------------------
if st.session_state.approval_payload is not None:
    ap          = st.session_state.approval_payload.get("approval_gate", {})
    final_dec   = ap.get("decision", "")
    final_cmt   = ap.get("comments", "")
    reviewed_at = ap.get("reviewed_at", "")

    if final_dec == "APPROVE":
        st.success(f"✅ Decision saved: **APPROVED** — {reviewed_at}")
    else:
        st.error(f"❌ Decision saved: **REJECTED** — {reviewed_at}")

    if final_cmt:
        st.info(f"💬 Reviewer note: _{final_cmt}_")

    with st.expander("📄 Full Approval Record (JSON)"):
        st.json(st.session_state.approval_payload)

    if st.button("🔄 Start New Validation"):
        for k in _DEFAULTS:
            st.session_state[k] = _DEFAULTS[k]
        st.rerun()

# ---------------------------------------------------------------------------
# Empty State
# ---------------------------------------------------------------------------
if (
    not st.session_state.validation_started
    and st.session_state.validation_result is None
    and st.session_state.approval_payload is None
):
    st.markdown(
        """
        <div style="text-align:center;padding:3.5rem 1rem;opacity:0.6;">
            <div style="font-size:3.5rem;margin-bottom:1rem">📂</div>
            <p style="font-size:1.1rem;font-weight:600;">
                No document loaded yet
            </p>
            <p style="font-size:0.9rem;">
                Upload a rental agreement PDF in the sidebar and click
                <strong>Run Validation Workflow</strong> to begin.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )