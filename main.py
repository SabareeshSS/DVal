import json
import os
import re
import subprocess
import yaml
from pathlib import Path
import fitz  # PyMuPDF

try:
    from langchain_ollama import ChatOllama
except ImportError:
    from langchain_community.chat_models import ChatOllama  # type: ignore


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "result.json"
APPROVAL_FILE = OUTPUT_DIR / "approval_gate.json"


def load_validation_rules():
    with open(BASE_DIR / "rules.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


VALIDATION_RULES = load_validation_rules()


def get_installed_ollama_models():
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
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


def get_llm(model_name=None):
    selected_model = model_name or os.getenv("OLLAMA_MODEL") or "llama3.2:latest"
    return ChatOllama(model=selected_model, base_url="http://localhost:11434")


def parse_json_response(response_text):
    text = response_text if isinstance(response_text, str) else str(response_text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Could not parse JSON from model output: {text}")
    return json.loads(text[start : end + 1])


def fallback_clause_validation(text):
    normalized = text.lower()
    clause_keywords = {
        "Termination Clause": ["termination", "terminate", "terminated"],
        "Confidentiality Clause": ["confidential", "confidentiality"],
        "Governing Law": ["governing law", "jurisdiction", "law"],
        "Payment Terms": ["payment", "rent", "pay", "monthly", "due"],
    }
    found = []
    missing = []
    for clause, keywords in clause_keywords.items():
        if any(keyword in normalized for keyword in keywords):
            found.append(clause)
        else:
            missing.append(clause)
    return {"missing_clauses": missing, "found_clauses": found}


def fallback_compliance_validation(text):
    issues = []
    if not re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b", text, re.I):
        if not re.search(r"\b\d{4}\b", text):
            issues.append("No clear date found")
    if not re.search(r"\b(signature|signed|sign)\b", text, re.I):
        issues.append("Missing signature evidence")
    if not re.search(r"\bpage\b", text, re.I):
        issues.append("Page numbering not clearly present")
    if re.search(r"\b(tbd|n/a|empty|blank)\b", text, re.I):
        issues.append("Contains placeholder or empty-field markers")
    return {"issues_found": issues}


def call_model_with_fallback(prompt, fallback_builder, model_name=None):
    try:
        llm = get_llm(model_name)
        result = llm.invoke(prompt)
        return parse_json_response(result.content if hasattr(result, "content") else result)
    except Exception as exc:
        print(f"Falling back to deterministic validation because Ollama call failed: {exc}")
        return fallback_builder()


def extract_pdf_text_from_bytes(pdf_bytes, filename="document.pdf"):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


def clause_validator_agent(state, model_name=None):
    required_clauses = VALIDATION_RULES["required_clauses"]

    prompt = f"""
Check if the following required clauses are present in this document:

Required Clauses: {required_clauses}

Document:
\"\"\"
{state['text']}
\"\"\"

Return a JSON object with:
- "missing_clauses": list of clauses not found
- "found_clauses": list of clauses found
"""
    parsed = call_model_with_fallback(prompt, lambda: fallback_clause_validation(state["text"]), model_name)
    return {**state, **parsed}


def compliance_agent(state, model_name=None):
    formatting_issues = VALIDATION_RULES["formatting_checks"]

    prompt = f"""
Review the document for formatting and red flags:
Checks: {formatting_issues}

Document:
\"\"\"
{state['text']}
\"\"\"

Return a JSON object with:
- "issues_found": list of formatting/completeness issues
"""
    parsed = call_model_with_fallback(prompt, lambda: fallback_compliance_validation(state["text"]), model_name)
    return {**state, **parsed}


def decision_agent(state, model_name=None):
    prompt = f"""
Based on the following validation results:

Missing Clauses: {state.get('missing_clauses', [])}
Issues Found: {state.get('issues_found', [])}

Decide whether the document should be APPROVED or REJECTED.
Explain the reasoning clearly.

Return JSON:
{{
  "decision": "APPROVED" or "REJECTED",
  "reason": "..."
}}
"""
    parsed = call_model_with_fallback(prompt, lambda: ({"decision": "REJECTED" if state.get("missing_clauses") or state.get("issues_found") else "APPROVED", "reason": "Determined from rule-based validation."}), model_name)
    return {"result": parsed}


def run_document_validation(pdf_bytes, filename="document.pdf", model_name=None):
    extracted_text = extract_pdf_text_from_bytes(pdf_bytes, filename)
    state = {"text": extracted_text}
    state = clause_validator_agent(state, model_name)
    state = compliance_agent(state, model_name)
    decision = decision_agent(state, model_name)
    result = {**state, **decision}

    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result["result"], f, indent=4)

    return result


def save_approval_gate(result, approval_decision, comments):
    OUTPUT_DIR.mkdir(exist_ok=True)
    payload = {
        "validation_result": result["result"],
        "approval_gate": {
            "decision": approval_decision,
            "comments": comments,
        },
    }
    with open(APPROVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
    return payload


if __name__ == "__main__":
    print("This module is used by the UI. Run app.py to start the web interface.")
