import json
import os
import re
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

_OK_SET = {"OK", "OK_OVERRIDDEN"}

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
    return ChatOllama(
        model=selected,
        base_url="http://localhost:11434",
        temperature=0,          # deterministic output
        format="json",          # force JSON mode if model supports it
    )

# ---------------------------------------------------------------------------
# JSON Parsing  — hardened against markdown fences, trailing text, etc.
# ---------------------------------------------------------------------------

def parse_json_response(response_text: str) -> dict:
    """
    Robustly extract the first valid JSON object from any LLM response.
    Handles:
      - Markdown fences  ```json ... ```
      - Leading/trailing prose
      - Nested braces
      - Single-quoted keys (best-effort)
    """
    text = response_text if isinstance(response_text, str) else str(response_text)

    # 1. Strip markdown code fences
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()

    # 2. Find the outermost { ... } block
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in response:\n{text[:300]}")

    depth   = 0
    end_idx = -1
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end_idx = i
                break

    if end_idx == -1:
        raise ValueError(f"Unbalanced braces in response:\n{text[:300]}")

    json_str = text[start: end_idx + 1]

    # 3. Attempt direct parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 4. Best-effort: replace single quotes with double quotes
        json_str2 = re.sub(r"(?<![\\])'", '"', json_str)
        try:
            return json.loads(json_str2)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Could not parse JSON after cleanup:\n{json_str[:300]}"
            ) from exc

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

def extract_pdf_text_from_bytes(
    pdf_bytes: bytes,
    filename:  str = "document.pdf",
) -> str:
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
# Status Correction Helper
# ---------------------------------------------------------------------------

def _correct_tenant_status(parsed: dict) -> dict:
    """
    Guarantee logical consistency:
      - If missing list is empty  → status MUST be OK
      - If missing list non-empty → status MUST be FAILED
      - Move any found items that appear in missing back to found
    This prevents the LLM from saying FAILED when nothing is missing.
    """
    missing = parsed.get("tenant_missing_clauses", [])
    found   = parsed.get("tenant_found_clauses",   [])

    # De-duplicate: if a clause appears in both lists, keep it in found
    missing_clean = [c for c in missing if c not in found]
    found_clean   = list(found)

    # Derive status purely from the lists — never trust the LLM's status field
    status = "OK" if len(missing_clean) == 0 else "FAILED"

    return {
        "tenant_missing_clauses": missing_clean,
        "tenant_found_clauses":   found_clean,
        "tenant_status":          status,
    }


def _correct_landlord_status(parsed: dict) -> dict:
    """If issues list is empty, status must be OK."""
    issues = parsed.get("landlord_issues", [])
    # Filter out empty strings
    issues_clean = [i for i in issues if str(i).strip()]
    status = "OK" if len(issues_clean) == 0 else "FAILED"
    return {
        "landlord_issues": issues_clean,
        "landlord_status": status,
    }


def _correct_insurer_status(parsed: dict) -> dict:
    """If issues list is empty, status must be OK."""
    issues = parsed.get("insurer_issues", [])
    issues_clean = [i for i in issues if str(i).strip()]
    status = "OK" if len(issues_clean) == 0 else "FAILED"
    return {
        "insurer_issues": issues_clean,
        "insurer_status": status,
    }

# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

def tenant_agent(state: dict, model_name: str = None) -> dict:
    """
    Validate required tenant clauses.
    Status is derived programmatically AFTER the LLM responds —
    the LLM's own status field is intentionally ignored.
    """
    clauses    = VALIDATION_RULES.get("tenant_rules", {}).get("required_clauses", [])
    clause_list = [
        {
            "name":        c["name"],
            "description": c.get("description", "").strip(),
        }
        if isinstance(c, dict) else {"name": c, "description": ""}
        for c in clauses
    ]
    clause_names = [c["name"] for c in clause_list]

    prompt = f"""You are a Tenant Compliance Agent reviewing a residential rental agreement.

TASK: Determine which of the required clauses below are present in the document.

REQUIRED CLAUSES:
{json.dumps(clause_list, indent=2)}

DOCUMENT:
\"\"\"
{state['text']}
\"\"\"

RULES:
1. A clause is FOUND if the document meaningfully covers its substance — even if
   the exact heading is different (e.g. "RENT DUE DATE" covers RENT PAYMENT PROCEDURE).
2. A clause is MISSING only if the document contains NO content addressing it at all.
3. Every clause name must appear in exactly one of the two lists below.
4. Do NOT be strict about exact wording — look for equivalent meaning.

Return ONLY this JSON object and nothing else:
{{
  "tenant_found_clauses":   ["<clause name>", ...],
  "tenant_missing_clauses": ["<clause name>", ...]
}}

The clause names in your response MUST be taken exactly from this list:
{json.dumps(clause_names)}
"""

    parsed = call_model_with_fallback(prompt, fallback_tenant_validation, model_name)

    # ── Programmatic correction — never trust LLM's status field ────────
    corrected = _correct_tenant_status(parsed)

    # ── Safety net: any clause not mentioned goes to missing ─────────────
    all_mentioned = set(corrected["tenant_found_clauses"]) | set(corrected["tenant_missing_clauses"])
    unmentioned   = [n for n in clause_names if n not in all_mentioned]
    if unmentioned:
        corrected["tenant_missing_clauses"].extend(unmentioned)
        corrected = _correct_tenant_status(corrected)   # re-derive status

    return {**state, **corrected}


def landlord_agent(state: dict, model_name: str = None) -> dict:
    """Run landlord compliance checks."""
    checks     = VALIDATION_RULES.get("landlord_rules", {}).get("checks", [])
    check_list = [
        {
            "name":        c["name"],
            "description": c.get("description", "").strip(),
        }
        if isinstance(c, dict) else {"name": c, "description": ""}
        for c in checks
    ]

    prompt = f"""You are a Landlord Compliance Agent reviewing a residential rental agreement.

TASK: Perform each check below and list ONLY the specific problems you find.

CHECKS:
{json.dumps(check_list, indent=2)}

DOCUMENT:
\"\"\"
{state['text']}
\"\"\"

RULES:
1. Only report a problem if it is clearly present in the document.
2. If a check passes, do NOT include it in the issues list.
3. Be reasonable — a sample/template document with labelled blank signature
   lines is NOT the same as a missing signature field.
4. Do NOT invent issues that are not evident in the text.

Return ONLY this JSON object and nothing else:
{{
  "landlord_issues": ["<specific issue>", ...]
}}

If there are no issues, return:
{{
  "landlord_issues": []
}}
"""

    parsed    = call_model_with_fallback(prompt, fallback_landlord_validation, model_name)
    corrected = _correct_landlord_status(parsed)
    return {**state, **corrected}


def insurer_agent(state: dict, model_name: str = None) -> dict:
    """Run insurer validation checks."""
    checks     = VALIDATION_RULES.get("insurer_rules", {}).get("checks", [])
    check_list = [
        {
            "name":        c["name"],
            "description": c.get("description", "").strip(),
        }
        if isinstance(c, dict) else {"name": c, "description": ""}
        for c in checks
    ]

    prompt = f"""You are an Insurance Compliance Agent reviewing a residential rental agreement.

TASK: Validate the document against each check below and list ONLY the specific
problems you find.

CHECKS:
{json.dumps(check_list, indent=2)}

DOCUMENT:
\"\"\"
{state['text']}
\"\"\"

RULES:
1. Only report a problem if it is clearly and unambiguously present.
2. If a check passes, do NOT include it in the issues list.
3. A labelled signature line (e.g. "Tenant _____ Date _____") counts as a
   valid signature field even if blank in a sample document.
4. Do NOT invent issues that are not evident in the text.

Return ONLY this JSON object and nothing else:
{{
  "insurer_issues": ["<specific issue>", ...]
}}

If there are no issues, return:
{{
  "insurer_issues": []
}}
"""

    parsed    = call_model_with_fallback(prompt, fallback_insurer_validation, model_name)
    corrected = _correct_insurer_status(parsed)
    return {**state, **corrected}


def decision_agent(state: dict) -> dict:
    """Aggregate all agent results into a final APPROVED / REJECTED decision."""
    t_status = state.get("tenant_status",   "FAILED")
    l_status = state.get("landlord_status", "FAILED")
    i_status = state.get("insurer_status",  "FAILED")

    all_ok   = t_status in _OK_SET and l_status in _OK_SET and i_status in _OK_SET
    decision = "APPROVED" if all_ok else "REJECTED"

    if all_ok:
        reason = (
            "All three validation stages passed successfully "
            "(or were manually overridden by a reviewer). "
            "The document meets all required standards and is approved to proceed."
        )
    else:
        parts = []
        if t_status not in _OK_SET:
            parts.append(f"Tenant stage: {t_status}")
        if l_status not in _OK_SET:
            parts.append(f"Landlord stage: {l_status}")
        if i_status not in _OK_SET:
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
                "tenant": {
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

def run_document_validation(
    pdf_bytes:         bytes = None,
    filename:          str   = "document.pdf",
    model_name:        str   = None,
    progress_callback: ProgressFn = None,
    initial_state:     dict  = None,
) -> dict:
    """
    Sequential multi-agent pipeline with resume support.

    Pass initial_state=None  → fresh run from PDF extraction.
    Pass initial_state=dict  → resume from a saved state (after override/revert).

    progress_callback(pct, msg) fires BEFORE each blocking LLM call.
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
        state = dict(initial_state)
        state.setdefault("override_log", [])
        _cb(10, "📄 Resuming from saved pipeline state…")

    # ── Stage 2: Tenant Agent ────────────────────────────────────────────
    if state.get("tenant_status") in _OK_SET:
        _cb(25, "👤 Tenant Agent — already cleared, skipping…")
    else:
        _cb(25, "👤 Tenant Agent — validating required clauses…")
        state = tenant_agent(state, model_name)
        _cb(40, f"👤 Tenant Agent — complete: {state.get('tenant_status')}")

    # ── Stage 3: Landlord Agent ──────────────────────────────────────────
    if state.get("tenant_status") not in _OK_SET:
        _cb(55, "🏠 Landlord Agent — skipped (Tenant stage not cleared)…")
        state.setdefault("landlord_status", "SKIPPED")
        state.setdefault("landlord_issues", [
            "Skipped — Tenant validation has not been cleared. "
            "Use the Human Approval Gate to override the Tenant stage first."
        ])
    elif state.get("landlord_status") in _OK_SET:
        _cb(55, "🏠 Landlord Agent — already cleared, skipping…")
    else:
        _cb(55, "🏠 Landlord Agent — running compliance checks…")
        state = landlord_agent(state, model_name)
        _cb(70, f"🏠 Landlord Agent — complete: {state.get('landlord_status')}")

    # ── Stage 4: Insurer Agent ───────────────────────────────────────────
    prior_clear = (
        state.get("tenant_status")   in _OK_SET
        and state.get("landlord_status") in _OK_SET
    )
    if not prior_clear:
        _cb(80, "🛡️ Insurer Agent — skipped (prior stages not cleared)…")
        state.setdefault("insurer_status", "SKIPPED")
        state.setdefault("insurer_issues", [
            "Skipped — Tenant and/or Landlord stages have not been cleared. "
            "Resolve or override those stages first."
        ])
    elif state.get("insurer_status") in _OK_SET:
        _cb(80, "🛡️ Insurer Agent — already cleared, skipping…")
    else:
        _cb(80, "🛡️ Insurer Agent — validating signatures & coverage…")
        state = insurer_agent(state, model_name)
        _cb(92, f"🛡️ Insurer Agent — complete: {state.get('insurer_status')}")

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
    comments:          str,
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