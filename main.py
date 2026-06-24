import json
import os
import subprocess
import yaml
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import fitz  # PyMuPDF

try:
    from langchain_ollama import ChatOllama
except ImportError:
    from langchain_community.chat_models import ChatOllama  # type: ignore


BASE_DIR   = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE   = OUTPUT_DIR / "result.json"
APPROVAL_FILE = OUTPUT_DIR / "approval_gate.json"

ProgressFn = Optional[Callable[[int, str], None]]

# ---------------------------------------------------------------------------
# Rule Loading
# ---------------------------------------------------------------------------

def load_validation_rules() -> dict:
    rules_path = BASE_DIR / "rules.yaml"
    with open(rules_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return raw.get("rental_agreement_rules", raw)


VALIDATION_RULES = load_validation_rules()

# ---------------------------------------------------------------------------
# Ollama Helpers
# ---------------------------------------------------------------------------

def get_installed_ollama_models() -> list:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, check=True, timeout=10,
        )
        lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
        if len(lines) <= 1:
            return []
        models = []
        for line in lines[1:]:
            name = line.split()[0]
            if name and name not in models:
                models.append(name)
        return models
    except Exception:
        return []


def get_llm(model_name: str = None):
    selected = model_name or os.getenv("OLLAMA_MODEL") or "llama3.2:latest"
    return ChatOllama(model=selected, base_url="http://localhost:11434")

# ---------------------------------------------------------------------------
# JSON Parsing
# ---------------------------------------------------------------------------

def parse_json_response(response_text: str) -> dict:
    text  = response_text if isinstance(response_text, str) else str(response_text)
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No valid JSON object found in model output:\n{text}")
    return json.loads(text[start: end + 1])

# ---------------------------------------------------------------------------
# Fallback Validators
# ---------------------------------------------------------------------------

def _clause_names() -> list:
    clauses = VALIDATION_RULES.get("tenant_rules", {}).get("required_clauses", [])
    return [c["name"] if isinstance(c, dict) else str(c) for c in clauses]


def fallback_tenant_validation() -> dict:
    return {
        "tenant_missing_clauses": _clause_names(),
        "tenant_found_clauses":   [],
        "tenant_status":          "FAILED",
    }


def fallback_landlord_validation() -> dict:
    return {
        "landlord_issues": [
            "Fallback executed — Ollama unavailable. "
            "Manual review required for all landlord checks."
        ],
        "landlord_status": "FAILED",
    }


def fallback_insurer_validation() -> dict:
    return {
        "insurer_issues": [
            "Fallback executed — Ollama unavailable. "
            "Manual review required for all insurer checks."
        ],
        "insurer_status": "FAILED",
    }

# ---------------------------------------------------------------------------
# LLM Call Wrapper
# ---------------------------------------------------------------------------

def call_model_with_fallback(
    prompt: str,
    fallback_fn: Callable,
    model_name: str = None,
) -> dict:
    try:
        llm     = get_llm(model_name)
        raw     = llm.invoke(prompt)
        content = raw.content if hasattr(raw, "content") else str(raw)
        return parse_json_response(content)
    except Exception as exc:
        print(f"[WARN] LLM call failed ({exc}). Using deterministic fallback.")
        return fallback_fn()

# ---------------------------------------------------------------------------
# PDF Extraction
# ---------------------------------------------------------------------------

def extract_pdf_text_from_bytes(pdf_bytes: bytes, filename: str = "document.pdf") -> str:
    doc       = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages     = [page.get_text() for page in doc]
    doc.close()
    full_text = "\n".join(pages)
    if not full_text.strip():
        raise ValueError(
            "The uploaded PDF appears to be empty or image-only "
            "(no extractable text). Please upload a text-based PDF."
        )
    return full_text

# ---------------------------------------------------------------------------
# Individual Agents
# ---------------------------------------------------------------------------

def tenant_agent(state: dict, model_name: str = None) -> dict:
    """Always runs fresh — never skips."""
    clauses    = VALIDATION_RULES.get("tenant_rules", {}).get("required_clauses", [])
    clause_list = [
        {"name": c["name"], "description": c.get("description", "").strip()}
        if isinstance(c, dict) else {"name": c, "description": ""}
        for c in clauses
    ]
    prompt = f"""
You are a Tenant Compliance Agent reviewing a residential rental agreement.

Your task is to check whether each of the following required clauses is present
and adequately addressed in the document below.

Required Clauses:
{json.dumps(clause_list, indent=2)}

Document:
\"\"\"
{state['text']}
\"\"\"

Instructions:
- For each clause, determine if it is present AND sufficiently covered.
- A clause is "found" only if the document meaningfully addresses it — not just
  mentions the keyword.
- Return ONLY a valid JSON object with these exact keys:
  {{
    "tenant_missing_clauses": ["<clause name>", ...],
    "tenant_found_clauses":   ["<clause name>", ...],
    "tenant_status":          "OK" or "FAILED"
  }}
- "tenant_status" must be "OK" only if tenant_missing_clauses is empty.
- Do NOT include any explanation outside the JSON.
"""
    parsed = call_model_with_fallback(prompt, fallback_tenant_validation, model_name)
    return {
        **state,
        "tenant_missing_clauses": parsed.get("tenant_missing_clauses", []),
        "tenant_found_clauses":   parsed.get("tenant_found_clauses",   []),
        "tenant_status":          parsed.get("tenant_status",          "FAILED"),
    }


def landlord_agent(state: dict, model_name: str = None) -> dict:
    """Always runs fresh — caller decides whether to invoke."""
    checks     = VALIDATION_RULES.get("landlord_rules", {}).get("checks", [])
    check_list = [
        {"name": c["name"], "description": c.get("description", "").strip()}
        if isinstance(c, dict) else {"name": c, "description": ""}
        for c in checks
    ]
    prompt = f"""
You are a Landlord Compliance Agent reviewing a residential rental agreement.

Your task is to perform the following checks on the document below and identify
any issues, omissions, or red flags.

Checks to Perform:
{json.dumps(check_list, indent=2)}

Document:
\"\"\"
{state['text']}
\"\"\"

Instructions:
- For each check, identify specific problems found (e.g., missing date, blank
  signature field, "TBD" in a critical section).
- If a check passes cleanly, do NOT include it in the issues list.
- Return ONLY a valid JSON object with these exact keys:
  {{
    "landlord_issues": ["<specific issue description>", ...],
    "landlord_status": "OK" or "FAILED"
  }}
- "landlord_status" must be "OK" only if landlord_issues is empty.
- Do NOT include any explanation outside the JSON.
"""
    parsed = call_model_with_fallback(prompt, fallback_landlord_validation, model_name)
    return {
        **state,
        "landlord_issues": parsed.get("landlord_issues", []),
        "landlord_status": parsed.get("landlord_status", "FAILED"),
    }


def insurer_agent(state: dict, model_name: str = None) -> dict:
    """Always runs fresh — caller decides whether to invoke."""
    checks     = VALIDATION_RULES.get("insurer_rules", {}).get("checks", [])
    check_list = [
        {"name": c["name"], "description": c.get("description", "").strip()}
        if isinstance(c, dict) else {"name": c, "description": ""}
        for c in checks
    ]
    prompt = f"""
You are an Insurance Compliance Agent reviewing a residential rental agreement.

Your task is to validate the document against the following insurance-related
checks and identify any deficiencies.

Checks to Perform:
{json.dumps(check_list, indent=2)}

Document:
\"\"\"
{state['text']}
\"\"\"

Instructions:
- For each check, identify specific problems found (e.g., missing tenant
  signature, coverage period mismatch, absent liability clause).
- If a check passes cleanly, do NOT include it in the issues list.
- Return ONLY a valid JSON object with these exact keys:
  {{
    "insurer_issues": ["<specific issue description>", ...],
    "insurer_status": "OK" or "FAILED"
  }}
- "insurer_status" must be "OK" only if insurer_issues is empty.
- Do NOT include any explanation outside the JSON.
"""
    parsed = call_model_with_fallback(prompt, fallback_insurer_validation, model_name)
    return {
        **state,
        "insurer_issues": parsed.get("insurer_issues", []),
        "insurer_status": parsed.get("insurer_status", "FAILED"),
    }


def decision_agent(state: dict) -> dict:
    """Aggregate all agent results into a final APPROVED / REJECTED decision."""
    t_status = state.get("tenant_status",   "FAILED")
    l_status = state.get("landlord_status", "FAILED")
    i_status = state.get("insurer_status",  "FAILED")

    _ok = {"OK", "OK_OVERRIDDEN"}
    all_ok   = t_status in _ok and l_status in _ok and i_status in _ok
    decision = "APPROVED" if all_ok else "REJECTED"

    if all_ok:
        reason = (
            "All three validation stages passed successfully "
            "(or were manually overridden by a reviewer). "
            "The document meets all required standards."
        )
    else:
        parts = []
        if t_status not in _ok:
            parts.append(f"Tenant stage: {t_status}")
        if l_status not in _ok:
            parts.append(f"Landlord stage: {l_status}")
        if i_status not in _ok:
            parts.append(f"Insurer stage: {i_status}")
        reason = (
            "Document rejected due to validation failures — "
            + ", ".join(parts)
            + ". Please review the detailed issues in each stage "
            "or use the Human Approval Gate to override."
        )

    return {
        "result": {
            "decision":        decision,
            "reason":          reason,
            "tenant_status":   t_status,
            "landlord_status": l_status,
            "insurer_status":  i_status,
            "details": {
                "tenant":   {
                    "missing": state.get("tenant_missing_clauses", []),
                    "found":   state.get("tenant_found_clauses",   []),
                },
                "landlord": {"issues": state.get("landlord_issues", [])},
                "insurer":  {"issues": state.get("insurer_issues",  [])},
            },
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "override_log": state.get("override_log", []),
        }
    }

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_OK_SET = {"OK", "OK_OVERRIDDEN"}


def run_document_validation(
    pdf_bytes: bytes = None,
    filename:  str   = "document.pdf",
    model_name: str  = None,
    progress_callback: ProgressFn = None,
    initial_state: dict = None,
) -> dict:
    """
    Sequential multi-agent pipeline with resume support.

    • Pass initial_state=None  → fresh run from PDF extraction.
    • Pass initial_state=<dict> → resume from a previously saved state
      (used after OVERRIDE or REVERT actions from the Human Approval Gate).

    progress_callback(pct, msg) is fired BEFORE each blocking LLM call
    so the UI updates immediately.
    """

    def _cb(pct: int, msg: str) -> None:
        if progress_callback:
            progress_callback(pct, msg)

    # ── Stage 1: PDF Extraction ──────────────────────────────────────────
    if initial_state is None:
        _cb(10, "📄 Extracting text from PDF…")
        text  = extract_pdf_text_from_bytes(pdf_bytes, filename)
        state = {
            "text":         text,
            "filename":     filename,
            "override_log": [],
        }
    else:
        # Resume: carry forward the extracted text and override history
        state = dict(initial_state)
        state.setdefault("override_log", [])
        _cb(10, "📄 Resuming from saved pipeline state…")

    # ── Stage 2: Tenant Agent ────────────────────────────────────────────
    if state.get("tenant_status") in _OK_SET:
        _cb(25, "👤 Tenant Agent — already passed / overridden, skipping re-run…")
    else:
        _cb(25, "👤 Tenant Agent — validating required clauses…")
        state = tenant_agent(state, model_name)

    # ── Stage 3: Landlord Agent ──────────────────────────────────────────
    if state.get("tenant_status") not in _OK_SET:
        # Tenant still failing — landlord cannot run
        _cb(55, "🏠 Landlord Agent — skipped (Tenant stage not cleared)…")
        state.update({
            "landlord_status": "SKIPPED",
            "landlord_issues": [
                "Skipped — Tenant validation has not been cleared. "
                "Use the Human Approval Gate to override the Tenant stage first."
            ],
        })
    elif state.get("landlord_status") in _OK_SET:
        _cb(55, "🏠 Landlord Agent — already passed / overridden, skipping re-run…")
    else:
        _cb(55, "🏠 Landlord Agent — running compliance checks…")
        state = landlord_agent(state, model_name)

    # ── Stage 4: Insurer Agent ───────────────────────────────────────────
    prior_clear = (
        state.get("tenant_status")   in _OK_SET
        and state.get("landlord_status") in _OK_SET
    )
    if not prior_clear:
        _cb(80, "🛡️ Insurer Agent — skipped (prior stages not cleared)…")
        state.update({
            "insurer_status": "SKIPPED",
            "insurer_issues": [
                "Skipped — Tenant and/or Landlord stages have not been cleared. "
                "Resolve or override those stages first."
            ],
        })
    elif state.get("insurer_status") in _OK_SET:
        _cb(80, "🛡️ Insurer Agent — already passed / overridden, skipping re-run…")
    else:
        _cb(80, "🛡️ Insurer Agent — validating signatures & coverage…")
        state = insurer_agent(state, model_name)

    # ── Stage 5: Decision Agent ──────────────────────────────────────────
    _cb(95, "⚖️ Decision Agent — aggregating results…")
    decision    = decision_agent(state)
    final_state = {**state, **decision}

    # ── Persist ──────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_state["result"], f, indent=4)

    return final_state

# ---------------------------------------------------------------------------
# Approval Gate
# ---------------------------------------------------------------------------

def save_approval_gate(
    validation_result: dict,
    approval_decision: str,
    comments: str,
) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "validation_result": validation_result["result"],
        "approval_gate": {
            "decision":    approval_decision,
            "comments":    comments,
            "reviewed_at": datetime.utcnow().isoformat() + "Z",
        },
    }
    with open(APPROVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
    return payload


if __name__ == "__main__":
    print("Run `streamlit run app.py` to launch the web interface.")