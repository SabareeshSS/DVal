import streamlit as st
from pathlib import Path
from main import run_document_validation, save_approval_gate, get_installed_ollama_models

st.set_page_config(page_title="Document Validator & Approval Gate", page_icon="📄", layout="wide")

st.title("📄 Document Validator and Approval Gate")
st.write("Upload a rental agreement PDF, choose an installed Ollama model, validate it, and then move to the approval gate.")

if "validation_result" not in st.session_state:
    st.session_state.validation_result = None
if "approval_payload" not in st.session_state:
    st.session_state.approval_payload = None

with st.sidebar:
    st.header("Settings")
    uploaded_file = st.file_uploader("Upload Rental Agreement (PDF)", type=["pdf"])
    model_options = get_installed_ollama_models()
    model_name = st.selectbox("Select Ollama model", model_options or ["llama3.2:latest"], index=0)
    run_button = st.button("Run Validation", type="primary")

if run_button:
    if uploaded_file is None:
        st.error("Please upload a PDF file first.")
    else:
        with st.spinner("Extracting text and validating the document..."):
            pdf_bytes = uploaded_file.read()
            result = run_document_validation(pdf_bytes, uploaded_file.name, model_name=model_name)
            st.session_state.validation_result = result
            st.session_state.approval_payload = None

if st.session_state.validation_result is not None:
    result = st.session_state.validation_result["result"]
    st.subheader("Validation Result")
    st.json(result)

    decision = result.get("decision", "REJECTED")
    if decision == "APPROVED":
        st.success("Document passed validation. You can proceed to the approval gate.")
    else:
        st.warning("Document did not pass validation. Review the issues before proceeding.")

    st.subheader("Approval Gate")
    approval_decision = st.radio("Final decision", ["APPROVE", "REJECT"], horizontal=True)
    comments = st.text_area("Comments", placeholder="Add reviewer comments here...")
    if st.button("Submit Approval Gate", type="primary"):
        payload = save_approval_gate(st.session_state.validation_result, approval_decision, comments)
        st.session_state.approval_payload = payload
        st.success("Approval gate submitted successfully.")
        st.json(payload)
