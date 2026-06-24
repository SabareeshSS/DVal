# README.md

```markdown
# 📋 Rental Agreement — Multi-Agent Validator & Approval Gate

A production-ready document intelligence pipeline that automatically validates
residential rental agreements through a sequential multi-agent AI workflow,
culminating in a Human-in-the-Loop approval gate.

Built with **Streamlit**, **LangChain + Ollama**, and **PyMuPDF** — fully
local, privacy-first, no external API calls.

---

## 📸 Overview

```
Upload PDF  →  Tenant Agent  →  Landlord Agent  →  Insurer Agent  →  Decision Agent  →  Human Approval Gate
```

Each agent is role-scoped, rule-driven from `rules.yaml`, and equipped with
a deterministic fallback if the LLM is unavailable. The pipeline short-circuits
intelligently — downstream agents are automatically skipped if an upstream
stage fails.

---

## 🎯 What It Does

| Stage | Agent | Responsibility |
|-------|-------|----------------|
| 1️⃣ | **Tenant Agent** | Verifies all required clauses are present and adequately addressed (e.g., Fixed-Term Agreement, Rent Payment Procedure, Full Disclosure) |
| 2️⃣ | **Landlord Agent** | Checks dates, signatures, red flags (`TBD`, blank fields), landlord obligations, and legal compliance. *Auto-skips if Tenant stage fails.* |
| 3️⃣ | **Insurer Agent** | Validates tenant/landlord signatures, property details, coverage period alignment, and liability clauses. *Auto-skips if prior stages fail.* |
| 4️⃣ | **Decision Agent** | Aggregates all results and issues a final `APPROVED` or `REJECTED` system decision with a detailed reason. |
| 5️⃣ | **Human Approval Gate** | Reviewer confirms, overrides, or rejects the system decision with mandatory comments. Full record is saved to disk. |

---

## 🧠 Agent Logic & Short-Circuit Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     PDF Uploaded                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  Tenant Agent    │
              │  Clause Check    │
              └────────┬─────────┘
                       │
          ┌────────────┴─────────────┐
          │ FAILED                   │ OK
          ▼                          ▼
   Landlord → SKIPPED     ┌──────────────────┐
   Insurer  → SKIPPED     │  Landlord Agent  │
   Decision → REJECTED    │  Compliance Check│
                          └────────┬─────────┘
                                   │
                      ┌────────────┴────────────┐
                      │ FAILED/SKIPPED           │ OK
                      ▼                          ▼
               Insurer → SKIPPED     ┌──────────────────┐
               Decision → REJECTED   │  Insurer Agent   │
                                     │  Sig & Coverage  │
                                     └────────┬─────────┘
                                              │
                                   ┌──────────┴──────────┐
                                   │ FAILED               │ OK
                                   ▼                      ▼
                            Decision →          Decision → APPROVED
                            REJECTED
```

---

## 📁 Project Structure

```
├── app.py                  # Streamlit UI — multi-agent workflow interface
├── main.py                 # Core pipeline — agents, LLM calls, orchestration
├── rules.yaml              # Validation rules for all three agents
├── requirements.txt        # Python dependencies
├── output/
│   ├── result.json         # Latest validation result (auto-generated)
│   └── approval_gate.json  # Final human approval record (auto-generated)
└── README.md               # You are here
```

---

## 📐 Validation Rules (`rules.yaml`)

Rules are structured with a `name` and `description` for every clause and
check. Each agent reads only its own section.

### 👤 Tenant Rules — Required Clauses

| Clause | What Is Checked |
|--------|-----------------|
| `FIXED-TERM AGREEMENT` | Clear start and end dates; no open-ended terms |
| `RENT PAYMENT PROCEDURE` | Due dates, grace periods, late payment penalties |
| `FORM OF PAYMENT` | Accepted payment methods explicitly stated |
| `FULL DISCLOSURE` | All fees, deposits, utilities, and pet policies disclosed |
| `TERMINATION AND RENEWAL TERMS` | Early termination conditions and notice periods |
| `TENANT RIGHTS AND RESPONSIBILITIES` | Upkeep obligations, privacy rights, guest rules |

### 🏠 Landlord Rules — Compliance Checks

| Check | What Is Verified |
|-------|-----------------|
| `TENANT CONSENT VERIFICATION` | Tenant has signed and acknowledged without coercion |
| `DATE COMPLETENESS CHECK` | All date fields filled; no blank or TBD dates |
| `SIGNATURE COMPLETENESS CHECK` | All parties have signed; no blank signature fields |
| `RED FLAG DETECTION` | Scans for "TBD", "N/A", blank clauses, contradictions |
| `LANDLORD OBLIGATIONS DISCLOSURE` | Maintenance duties, habitability, emergency contacts |
| `LEGAL COMPLIANCE CHECK` | Rent control, deposit limits, eviction procedures |

### 🛡️ Insurer Rules — Insurance Validation

| Check | What Is Validated |
|-------|------------------|
| `TENANT SIGNATURE VALIDATION` | Signature present, legible, matches agreement name |
| `LANDLORD SIGNATURE VALIDATION` | Signature present, matches registered property owner |
| `PROPERTY DETAILS VERIFICATION` | Address and unit match the insurance policy |
| `COVERAGE PERIOD ALIGNMENT` | Lease dates align with insurance activation period |
| `LIABILITY CLAUSE PRESENCE` | Liability for damage, injury, and renter's insurance |

---

## 🖥️ UI Walkthrough

```
┌─────────────────────────────────────────────────────────────────┐
│  SIDEBAR                    │  MAIN PANEL                       │
│  ─────────────────────────  │  ─────────────────────────────    │
│  📂 Upload PDF              │  📋 App Header                    │
│  🤖 Select Ollama Model     │                                   │
│  🚀 Run Validation          │  ⚙️  Progress Bar (staged)        │
│                             │                                   │
│  Workflow Pipeline Steps:   │  📊 Agent Cards (3 columns)       │
│  · PDF Extraction           │     👤 Tenant  🏠 Landlord        │
│  · Tenant Validation        │     🛡️  Insurer                   │
│  · Landlord Compliance      │                                   │
│  · Insurer Validation       │  📈 Pipeline Summary Metrics      │
│  · Decision Agent           │                                   │
│  · Human Approval Gate      │  ⚖️  System Decision Banner       │
│                             │                                   │
│                             │  🔏 Human Approval Gate Form      │
│                             │     · APPROVE / REJECT toggle     │
│                             │     · Mandatory reviewer comment  │
│                             │     · Confirm & Save button       │
│                             │                                   │
│                             │  ✅ Approval Confirmation         │
│                             │  📄 Full JSON Record (expandable) │
│                             │  🔄 Start New Validation          │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Setup & Installation

### Prerequisites

| Requirement | Details |
|-------------|---------|
| Python | 3.10 or higher |
| [Ollama](https://ollama.com) | Installed and running locally |
| LLM Model | At least one model pulled (e.g., `llama3.2`, `mistral`) |
| PDF | Text-based PDF (not scanned/image-only) |

---

### 1. Clone the Repository

```bash
git clone https://github.com/SabareeshSS/DVal.git
cd DVal
```

### 2. Create a Virtual Environment

```bash
# macOS / Linux
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Pull an Ollama Model

```bash
# Recommended — fast and capable
ollama pull llama3.2

# Alternative options
ollama pull mistral
ollama pull gemma2
```

### 5. Start Ollama (if not already running)

```bash
ollama serve
```

### 6. Launch the Application

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🚀 Usage Guide

```
Step 1 — Upload
  └── Drag and drop or browse for your rental agreement PDF
      in the sidebar file uploader.

Step 2 — Select Model
  └── Choose from your locally installed Ollama models.
      The dropdown auto-populates from `ollama list`.

Step 3 — Run Workflow
  └── Click "Run Validation Workflow".
      A staged progress bar tracks each agent in real time.

Step 4 — Review Results
  └── Three agent cards display PASSED / FAILED / SKIPPED
      status with expandable issue details.
      Pipeline summary metrics show totals at a glance.

Step 5 — System Decision
  └── The Decision Agent banner shows APPROVED or REJECTED
      with a full plain-English reason.

Step 6 — Human Approval Gate
  └── Select APPROVE or REJECT (pre-filled from system decision).
      Add mandatory reviewer comments.
      Click "Confirm & Save Decision".

Step 7 — Record Saved
  └── output/approval_gate.json is written with the full
      validation result + reviewer decision + timestamp.
      Click "Start New Validation" to reset.
```

---

## 📤 Output Files

### `output/result.json`
Generated automatically after every validation run.

```json
{
    "decision": "APPROVED",
    "reason": "All three validation stages passed successfully...",
    "tenant_status": "OK",
    "landlord_status": "OK",
    "insurer_status": "OK",
    "details": {
        "tenant": {
            "found": ["FIXED-TERM AGREEMENT", "RENT PAYMENT PROCEDURE"],
            "missing": []
        },
        "landlord": { "issues": [] },
        "insurer":  { "issues": [] }
    },
    "processed_at": "2025-01-15T10:32:44Z"
}
```

### `output/approval_gate.json`
Generated after the reviewer submits the Human Approval Gate form.

```json
{
    "validation_result": { "...": "full result object above" },
    "approval_gate": {
        "decision": "APPROVE",
        "comments": "Reviewed and confirmed. All clauses verified manually.",
        "reviewed_at": "2025-01-15T10:35:12Z"
    }
}
```

---

## 🔒 Privacy & Security

- **Fully local** — no data is sent to any external API or cloud service.
- All LLM inference runs on your machine via Ollama.
- Uploaded PDFs are processed in-memory; nothing is stored except
  the two JSON output files in `output/`.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `No Ollama models detected` | Run `ollama serve` and ensure at least one model is pulled with `ollama pull llama3.2` |
| `PDF appears empty or image-only` | Use a text-based PDF. Scanned documents require OCR pre-processing |
| `Validation always falls back` | Check Ollama is running on `http://localhost:11434`. Try `ollama run llama3.2` in terminal |
| `JSON parse error in logs` | The model returned malformed JSON. Try a larger/more capable model |
| `Streamlit reruns unexpectedly` | Expected behaviour — Streamlit reruns on every interaction; session state guards prevent data loss |

---

## 📦 Dependencies

```
streamlit          # Web UI framework
langchain          # LLM orchestration
langchain-community # Community LLM integrations
langchain-ollama   # Ollama-specific LangChain integration
pymupdf            # PDF text extraction (fitz)
pyyaml             # YAML rules file parsing
```

---

## 🗺️ Roadmap

- [ ] OCR support for scanned/image-based PDFs
- [ ] Multi-document batch validation
- [ ] Downloadable PDF/HTML validation report
- [ ] Clause-level highlighting in PDF viewer
- [ ] Webhook integration for approval notifications
- [ ] Role-based access control for the approval gate

---

## 📄 License

This project is licensed under the **MIT License**.
See `LICENSE` for details.

---

> Built for legal document automation · Powered by local AI · Privacy-first by design
```