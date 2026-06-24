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
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── Sidebar ── */
[data-testid="stSidebar"] { background:#1C2340; }
[data-testid="stSidebar"] * { color:#E8ECF4 !important; }
[data-testid="stSidebar"] .stButton>button {
    background:#4A6CF7; color:#fff !important; border:none;
    border-radius:8px; padding:.55rem 1.2rem; font-weight:600;
    width:100%; transition:background .2s;
}
[data-testid="stSidebar"] .stButton>button:hover { background:#3A5CE5; }

/* ── Header ── */
.app-header {
    background:linear-gradient(135deg,#1C2340 0%,#2E3D7A 100%);
    border-radius:14px; padding:2rem 2.5rem; margin-bottom:1.8rem;
    display:flex; align-items:center; gap:1.2rem;
}
.app-header h1 { color:#fff; font-size:1.9rem; font-weight:700; margin:0; }
.app-header p  { color:#A8B8D8; margin:.3rem 0 0; font-size:.95rem; }

/* ── Section titles ── */
.section-title {
    font-size:1.1rem; font-weight:700; color:var(--text-color);
    margin:1.6rem 0 .8rem; display:flex; align-items:center; gap:.5rem;
    border-left:4px solid #4A6CF7; padding-left:.7rem;
}

/* ── Agent cards ── */
.agent-card {
    background:var(--secondary-background-color); border-radius:12px;
    padding:1.4rem 1.6rem; box-shadow:0 2px 12px rgba(0,0,0,.08); height:100%;
}
.agent-card-title {
    font-size:1rem; font-weight:700; color:var(--text-color);
    margin-bottom:.8rem; display:flex; align-items:center; gap:.45rem;
}

/* ── Badges ── */
.badge {
    display:inline-block; padding:.28rem .85rem; border-radius:20px;
    font-size:.8rem; font-weight:700; letter-spacing:.04em; margin-bottom:.9rem;
}
.badge-ok         { background:#D1FAE5; color:#065F46; }
.badge-overridden { background:#DBEAFE; color:#1E40AF; }
.badge-failed     { background:#FEE2E2; color:#991B1B; }
.badge-skipped    { background:#FEF9C3; color:#854D0E; }
.badge-unknown    { background:#E5E7EB; color:#374151; }

/* ── Decision banners ── */
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
.decision-title  { font-size:1.2rem; font-weight:700; margin-bottom:.4rem; }
.decision-reason { font-size:.92rem; line-height:1.55; }

/* ── Override / Revert action cards ── */
.gate-card {
    background:var(--secondary-background-color); border-radius:12px;
    padding:1.8rem 2rem; box-shadow:0 2px 12px rgba(0,0,0,.08); margin-top:1rem;
}
.gate-section {
    border:1.5px solid #E5E7EB; border-radius:10px;
    padding:1.2rem 1.4rem; margin-bottom:1rem;
}
.gate-section-title {
    font-size:.95rem; font-weight:700; margin-bottom:.6rem;
    display:flex; align-items:center; gap:.4rem;
}

/* ── Override log ── */
.log-entry {
    background:var(--secondary-background-color); border-radius:8px;
    padding:.7rem 1rem; margin-bottom:.5rem;
    border-left:4px solid #4A6CF7; font-size:.85rem;
}

/* ── Workflow steps ── */
.workflow-step {
    display:flex; align-items:center; gap:.7rem;
    padding:.5rem 0; font-size:.88rem; color:#E8ECF4;
}
.step-dot { width:10px; height:10px; border-radius:50%; background:#4A6CF7; flex-shrink:0; }

hr { border-color:#E5E7EB; }
.stExpander { border-radius:8px !important; }
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
    "pipeline_state":     None,   # carries forward between override/revert runs
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_OK_SET = {"OK", "OK_OVERRIDDEN"}

def status_badge(status: str) -> str:
    mapping = {
        "OK":           ("badge-ok",         "✔ PASSED"),
        "OK_OVERRIDDEN":("badge-overridden",  "⚡ OVERRIDDEN"),
        "FAILED":       ("badge-failed",      "✘ FAILED"),
        "SKIPPED":      ("badge-skipped",     "⊘ SKIPPED"),
    }
    cls, label = mapping.get(status, ("badge-unknown", status))
    return f"<span class='badge {cls}'>{label}</span>"


def _reset():
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<div style='text-align:center;padding:1rem 0 .5rem'>"
        "<span style='font-size:2.2rem'>📋</span>"
        "<p style='font-size:1.05rem;font-weight:700;margin:.4rem 0 0'>Rental Agreement</p>"
        "<p style='font-size:.8rem;opacity:.7;margin:0'>Multi-Agent Validator</p></div>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("**📂 Upload Document**")
    uploaded_file = st.file_uploader(
        "Rental Agreement PDF", type=["pdf"], label_visibility="collapsed"
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
            f"<div class='workflow-step'><div class='step-dot'></div>{step}</div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="app-header">
    <span style="font-size:2.8rem">📋</span>
    <div>
        <h1>Rental Agreement Validator</h1>
        <p>Multi-agent AI pipeline · Tenant · Landlord · Insurer · Human Approval Gate</p>
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
        st.session_state.pipeline_state     = None   # fresh run
        st.rerun()

# ---------------------------------------------------------------------------
# Pipeline Execution Block
# ---------------------------------------------------------------------------
if st.session_state.validation_started and st.session_state.validation_result is None:

    st.markdown(
        "<div class='section-title'>⚙️ Running Validation Pipeline</div>",
        unsafe_allow_html=True,
    )

    with st.status("Starting validation pipeline…", expanded=True) as live:
        progress_bar = st.progress(0)

        def progress_callback(pct: int, msg: str) -> None:
            live.update(label=msg)
            progress_bar.progress(pct, text=msg)

        try:
            result = run_document_validation(
                pdf_bytes     = st.session_state.pdf_bytes,
                filename      = st.session_state.pdf_name,
                model_name    = model_name,
                progress_callback = progress_callback,
                initial_state = st.session_state.pipeline_state,  # None on first run
            )
            st.session_state.validation_result = result
            # Persist the raw pipeline state for future override/revert runs
            st.session_state.pipeline_state = {
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

    # ── Agent Result Cards ───────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>📊 Validation Stage Results</div>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3, gap="medium")

    # — Tenant —
    with col1:
        tenant_det = result.get("details", {}).get("tenant", {})
        missing    = tenant_det.get("missing", [])
        found      = tenant_det.get("found",   [])
        st.markdown(f"""
        <div class="agent-card">
            <div class="agent-card-title">👤 Tenant Agent</div>
            {status_badge(t_status)}
            <p style="font-size:.82rem;opacity:.7;margin:0 0 .6rem">
                Checks required clauses are present and adequately addressed.
            </p>
            <p style="font-size:.85rem;margin:0">
                <strong>{len(found)}</strong> found &nbsp;·&nbsp;
                <strong>{len(missing)}</strong> missing
            </p>
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
        landlord_issues = result.get("details", {}).get("landlord", {}).get("issues", [])
        st.markdown(f"""
        <div class="agent-card">
            <div class="agent-card-title">🏠 Landlord Agent</div>
            {status_badge(l_status)}
            <p style="font-size:.82rem;opacity:.7;margin:0 0 .6rem">
                Reviews dates, signatures, red flags, and legal compliance.
            </p>
            <p style="font-size:.85rem;margin:0">
                <strong>{len(landlord_issues)}</strong> issue(s) identified
            </p>
        </div>""", unsafe_allow_html=True)
        with st.expander("View Landlord Details"):
            if landlord_issues:
                st.markdown("**⚠️ Issues Found**")
                for i in landlord_issues:
                    st.markdown(f"- {i}")
            else:
                st.success("No issues found.")

    # — Insurer —
    with col3:
        insurer_issues = result.get("details", {}).get("insurer", {}).get("issues", [])
        st.markdown(f"""
        <div class="agent-card">
            <div class="agent-card-title">🛡️ Insurer Agent</div>
            {status_badge(i_status)}
            <p style="font-size:.82rem;opacity:.7;margin:0 0 .6rem">
                Validates signatures, property details, and liability clauses.
            </p>
            <p style="font-size:.85rem;margin:0">
                <strong>{len(insurer_issues)}</strong> issue(s) identified
            </p>
        </div>""", unsafe_allow_html=True)
        with st.expander("View Insurer Details"):
            if insurer_issues:
                st.markdown("**⚠️ Issues Found**")
                for i in insurer_issues:
                    st.markdown(f"- {i}")
            else:
                st.success("No issues found.")

    # ── Pipeline Summary ─────────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>📈 Pipeline Summary</div>",
        unsafe_allow_html=True,
    )
    all_statuses = [t_status, l_status, i_status]
    passed   = sum(1 for s in all_statuses if s in _OK_SET)
    failed   = sum(1 for s in all_statuses if s == "FAILED")
    skipped  = sum(1 for s in all_statuses if s == "SKIPPED")
    override = sum(1 for s in all_statuses if s == "OK_OVERRIDDEN")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Stages Run",      3)
    m2.metric("✅ Passed",       passed)
    m3.metric("❌ Failed",       failed)
    m4.metric("⊘ Skipped",      skipped)
    m5.metric("⚡ Overridden",   override)

    # ── System Decision ──────────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>⚖️ System Decision</div>",
        unsafe_allow_html=True,
    )
    ts_html = (
        f"<p style='margin:.6rem 0 0;font-size:.8rem;opacity:.75'>"
        f"Processed: {proc_at}</p>" if proc_at else ""
    )
    if decision == "APPROVED":
        st.markdown(f"""
        <div class="decision-approved">
            <div class="decision-title">✅ Document APPROVED</div>
            <div class="decision-reason">{reason}</div>
            {ts_html}
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="decision-rejected">
            <div class="decision-title">❌ Document REJECTED</div>
            <div class="decision-reason">{reason}</div>
            {ts_html}
        </div>""", unsafe_allow_html=True)

    # ── Override Log ─────────────────────────────────────────────────────
    override_log = result.get("override_log", [])
    if override_log:
        st.markdown(
            "<div class='section-title'>📜 Override History</div>",
            unsafe_allow_html=True,
        )
        for entry in override_log:
            st.markdown(
                f"<div class='log-entry'>"
                f"<strong>{entry.get('action','')}</strong> — "
                f"{entry.get('stage','')} &nbsp;·&nbsp; "
                f"<em>{entry.get('comment','')}</em> &nbsp;·&nbsp; "
                f"<span style='opacity:.6'>{entry.get('timestamp','')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Human Approval Gate ──────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>🔏 Human Approval Gate</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='opacity:.8;font-size:.9rem;margin-top:-.4rem'>"
        "Review each agent's outcome. You may <strong>APPROVE</strong> or "
        "<strong>REJECT</strong> the document, <strong>OVERRIDE</strong> a "
        "failed stage to force the pipeline forward, or <strong>REVERT</strong> "
        "to re-run a previous stage from scratch."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Determine which actions are available ────────────────────────────
    # Rules:
    #   APPROVE / REJECT  → always available
    #   OVERRIDE Tenant   → Tenant FAILED
    #   OVERRIDE Landlord → Tenant OK/OVR, Landlord FAILED
    #   OVERRIDE Insurer  → Tenant+Landlord OK/OVR, Insurer FAILED
    #   REVERT Tenant     → Landlord has been run (any status)
    #   REVERT Landlord   → Insurer has been run (any status)

    tenant_done   = t_status not in ("UNKNOWN", None)
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
        available_actions.append("REVERT → Re-run Insurer Agent")

    with st.form("approval_gate_form"):
        st.markdown("#### Select Action")

        selected_action = st.radio(
            "Action",
            options=available_actions,
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("#### Reviewer Comments *(required)*")
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
                "✅ Confirm Action",
                type="primary",
                use_container_width=True,
            )

    if submitted:
        if not comments.strip():
            st.warning("⚠️ Reviewer comments are required before confirming.")
            st.stop()

        action = selected_action
        ts     = datetime.utcnow().isoformat() + "Z"

        # ── APPROVE / REJECT ─────────────────────────────────────────────
        if action in ("APPROVE", "REJECT"):
            payload = save_approval_gate(
                st.session_state.validation_result,
                action,
                comments,
            )
            st.session_state.approval_payload = payload
            st.rerun()

        # ── OVERRIDE actions ─────────────────────────────────────────────
        elif "OVERRIDE" in action:
            ps = dict(st.session_state.pipeline_state or {})
            log_entry = {"action": action, "comment": comments, "timestamp": ts}

            if "Tenant" in action:
                log_entry["stage"] = "Tenant"
                ps["tenant_status"] = "OK_OVERRIDDEN"
                ps["tenant_missing_clauses"] = []
                ps["tenant_found_clauses"]   = (
                    ps.get("tenant_found_clauses", [])
                    + ps.get("tenant_missing_clauses", [])
                )
                # Clear downstream so they re-run
                ps.pop("landlord_status", None)
                ps.pop("landlord_issues", None)
                ps.pop("insurer_status",  None)
                ps.pop("insurer_issues",  None)

            elif "Landlord" in action:
                log_entry["stage"] = "Landlord"
                ps["landlord_status"] = "OK_OVERRIDDEN"
                ps["landlord_issues"] = []
                # Clear downstream so insurer re-runs
                ps.pop("insurer_status", None)
                ps.pop("insurer_issues", None)

            elif "Insurer" in action:
                log_entry["stage"] = "Insurer"
                ps["insurer_status"] = "OK_OVERRIDDEN"
                ps["insurer_issues"] = []

            ps.setdefault("override_log", []).append(log_entry)
            st.session_state.pipeline_state     = ps
            st.session_state.validation_started = True
            st.session_state.validation_result  = None
            st.rerun()

        # ── REVERT actions ───────────────────────────────────────────────
        elif "REVERT" in action:
            ps = dict(st.session_state.pipeline_state or {})
            log_entry = {"action": action, "comment": comments, "timestamp": ts}

            if "Tenant" in action:
                log_entry["stage"] = "Tenant (revert)"
                # Wipe tenant + all downstream
                for key in [
                    "tenant_status", "tenant_missing_clauses", "tenant_found_clauses",
                    "landlord_status", "landlord_issues",
                    "insurer_status",  "insurer_issues",
                ]:
                    ps.pop(key, None)

            elif "Landlord" in action:
                log_entry["stage"] = "Landlord (revert)"
                # Wipe landlord + insurer only
                for key in [
                    "landlord_status", "landlord_issues",
                    "insurer_status",  "insurer_issues",
                ]:
                    ps.pop(key, None)
                    
            elif "Insurer" in action:
                log_entry["stage"] = "Insurer (revert)"
                # Wipe insurer only
                for key in [
                    "insurer_status",  "insurer_issues",
                ]:
                    ps.pop(key, None)

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

    st.divider()
    if final_dec == "APPROVE":
        st.success(f"✅ Decision saved: **APPROVED** — {reviewed_at}")
    else:
        st.error(f"❌ Decision saved: **REJECTED** — {reviewed_at}")

    if final_cmt:
        st.info(f"💬 Reviewer note: _{final_cmt}_")

    with st.expander("📄 Full Approval Record (JSON)"):
        st.json(st.session_state.approval_payload)

    if st.button("🔄 Start New Validation"):
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
    <div style="text-align:center;padding:3.5rem 1rem;opacity:.6;">
        <div style="font-size:3.5rem;margin-bottom:1rem">📂</div>
        <p style="font-size:1.1rem;font-weight:600;">No document loaded yet</p>
        <p style="font-size:.9rem;">
            Upload a rental agreement PDF in the sidebar and click
            <strong>Run Validation Workflow</strong> to begin.
        </p>
    </div>
    """, unsafe_allow_html=True)