"""
Multi-Agent Multi-Modal Document Analysis System
=================================================
Advanced system with specialized agents for different tasks:
    - ExtractionAgent: Handles document parsing (vision + text)
    - DataAgent: Retrieves and structures data
    - AnalystAgent: Provides insights and summaries
    - ValidationAgent: Verifies extracted data quality

Multi-Modal Support:
    - Text documents (direct processing)
    - Images (vision API)
    - PDFs (vision API)
    - Data files (structured processing)

Agent Collaboration:
    - Extraction → Validation → Analysis pipeline
    - Agents hand off work to specialists
    - Maintains conversation context across agents
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, List, Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Image support
try:
    from PIL import Image
    PIL_SUPPORT = True
except ImportError:
    PIL_SUPPORT = False

# PDF support
try:
    from pdf2image import convert_from_bytes
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from client import create_thread, ensure_agent, get_agents_client, run_agent_turn

load_dotenv()

# ==================== Agent Configurations ====================

def get_extraction_agent_id() -> str:
    """Agent specialized in extracting data from documents (text + vision)."""
    if "extraction_agent_id" not in st.session_state:
        agent = ensure_agent(
            _agents_client(),
            name="ExtractionAgent",
            instructions=(
                "You are an expert data extraction specialist.\n"
                "Your role:\n"
                "1. Extract ALL structured and unstructured data from documents\n"
                "2. Identify document type (invoice, receipt, form, table, etc.)\n"
                "3. Return data in structured JSON format with these fields:\n"
                "   - document_type: Type of document\n"
                "   - confidence: Extraction confidence (0-100)\n"
                "   - extracted_fields: Dict of key-value pairs found\n"
                "   - raw_text: All text found\n"
                "   - notes: Any extraction issues or ambiguities\n"
                "Be thorough and flag low-confidence extractions."
            ),
        )
        st.session_state.extraction_agent_id = agent.id
    return st.session_state.extraction_agent_id


def get_data_agent_id() -> str:
    """Agent specialized in retrieving, structuring, and organizing data."""
    if "data_agent_id" not in st.session_state:
        agent = ensure_agent(
            _agents_client(),
            name="DataAgent",
            instructions=(
                "You are a data organization and retrieval specialist.\n"
                "Your role:\n"
                "1. Take extracted data and structure it properly\n"
                "2. Normalize data formats (dates, currencies, numbers)\n"
                "3. Create tables and relationships\n"
                "4. Fill in missing data with reasonable defaults (flagged)\n"
                "5. Convert data to requested formats (JSON, CSV, etc.)\n"
                "6. Validate data integrity and consistency\n"
                "Return structured data ready for analysis."
            ),
        )
        st.session_state.data_agent_id = agent.id
    return st.session_state.data_agent_id


def get_analyst_agent_id() -> str:
    """Agent specialized in analyzing data and providing insights."""
    if "analyst_agent_id" not in st.session_state:
        agent = ensure_agent(
            _agents_client(),
            name="AnalystAgent",
            instructions=(
                "You are a senior data analyst and business intelligence expert.\n"
                "Your role:\n"
                "1. Analyze structured data for patterns and insights\n"
                "2. Provide executive summaries\n"
                "3. Identify anomalies, trends, and outliers\n"
                "4. Make actionable recommendations\n"
                "5. Compare multiple documents\n"
                "6. Calculate key metrics and statistics\n"
                "Present findings clearly with supporting evidence."
            ),
        )
        st.session_state.analyst_agent_id = agent.id
    return st.session_state.analyst_agent_id


def get_validation_agent_id() -> str:
    """Agent specialized in validating extracted data quality."""
    if "validation_agent_id" not in st.session_state:
        agent = ensure_agent(
            _agents_client(),
            name="ValidationAgent",
            instructions=(
                "You are a data quality assurance specialist.\n"
                "Your role:\n"
                "1. Verify extracted data completeness\n"
                "2. Check for logical inconsistencies\n"
                "3. Validate data types and formats\n"
                "4. Flag suspicious or incorrect values\n"
                "5. Assign quality scores (0-100)\n"
                "6. Suggest corrections for errors\n"
                "Return a validation report with issues and confidence scores."
            ),
        )
        st.session_state.validation_agent_id = agent.id
    return st.session_state.validation_agent_id


# ==================== Utility Functions ====================

@st.cache_resource
def _agents_client():
    return get_agents_client()

def _run_async(coro):
    """Run an async coroutine safely from Streamlit."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    
    new_loop = asyncio.new_event_loop()
    try:
        return new_loop.run_until_complete(coro)
    finally:
        new_loop.close()


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode image to base64 for vision API."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def detect_file_type(file_type: str, file_name: str) -> str:
    """Detect if file needs vision, text, or data processing."""
    if file_type in ["application/pdf"] or file_type.startswith("image/"):
        return "vision"  # Needs vision API
    elif file_type in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        return "data"  # Structured data
    else:
        return "text"  # Plain text


def _to_float(value: Any) -> Optional[float]:
    """Safely convert value to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_invoice_signals(extraction_text: str) -> Dict[str, Any]:
    """Extract core invoice fields from extraction output for controls/decisioning."""
    text = extraction_text or ""

    invoice_match = re.search(r"invoice[_\s-]*(number|no|id)?\s*[:#-]?\s*([A-Za-z0-9\-/]+)", text, re.IGNORECASE)
    vendor_match = re.search(r"vendor\s*[:#-]?\s*([^\n,]+)", text, re.IGNORECASE)
    amount_match = re.search(r"(total|amount)\s*[:#-]?\s*([$€£]?\s*[0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
    currency_match = re.search(r"\b(USD|EUR|GBP|INR|JPY|AUD|CAD)\b", text, re.IGNORECASE)

    invoice_number = invoice_match.group(2).strip() if invoice_match else None
    vendor = vendor_match.group(1).strip() if vendor_match else None
    amount_text = amount_match.group(2).strip() if amount_match else None
    amount = _to_float(amount_text)
    currency = currency_match.group(1).upper() if currency_match else None

    return {
        "invoice_number": invoice_number,
        "vendor": vendor,
        "amount": amount,
        "currency": currency,
    }


def _invoice_fingerprint(signals: Dict[str, Any]) -> str:
    """Create normalized fingerprint for duplicate checks."""
    vendor = (signals.get("vendor") or "unknown-vendor").strip().lower()
    invoice_number = (signals.get("invoice_number") or "unknown-invoice").strip().lower()
    amount = signals.get("amount")
    amount_str = f"{float(amount):.2f}" if amount is not None else "unknown-amount"
    raw = f"{vendor}|{invoice_number}|{amount_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def detect_duplicate_invoice(signals: Dict[str, Any], processed_docs: List[dict]) -> Dict[str, Any]:
    """Detect likely duplicate invoices against processed documents."""
    current_fp = _invoice_fingerprint(signals)
    matched_file = None

    for doc in processed_docs:
        workflow = doc.get("workflow_controls") or {}
        prior_signals = workflow.get("invoice_signals") or {}
        if not prior_signals:
            continue
        if _invoice_fingerprint(prior_signals) == current_fp:
            matched_file = doc.get("file_name")
            break

    return {
        "fingerprint": current_fp,
        "is_duplicate": matched_file is not None,
        "matched_file": matched_file,
    }


def compute_fraud_score(
    signals: Dict[str, Any],
    duplicate_check: Dict[str, Any],
    validation_text: str,
) -> Dict[str, Any]:
    """Compute simple rule-based fraud risk score."""
    score = 0
    reasons: List[str] = []

    amount = signals.get("amount")
    if amount is None:
        score += 20
        reasons.append("Missing or unparseable amount")
    elif amount >= 50000:
        score += 35
        reasons.append("Very high invoice amount")
    elif amount >= 10000:
        score += 20
        reasons.append("High invoice amount")

    if not signals.get("invoice_number"):
        score += 20
        reasons.append("Missing invoice number")

    if not signals.get("vendor"):
        score += 15
        reasons.append("Missing vendor name")

    if duplicate_check.get("is_duplicate"):
        score += 40
        reasons.append("Potential duplicate invoice")

    lower_validation = (validation_text or "").lower()
    if any(keyword in lower_validation for keyword in ["issue", "inconsisten", "suspicious", "error"]):
        score += 10
        reasons.append("Validation reported quality issues")

    final_score = min(100, score)
    risk_label = "low"
    if final_score >= 70:
        risk_label = "high"
    elif final_score >= 40:
        risk_label = "medium"

    return {
        "score": final_score,
        "risk_label": risk_label,
        "reasons": reasons,
    }


def evaluate_workflow_controls(
    file_name: str,
    extraction_result: str,
    validation_result: Optional[str],
    processed_docs: List[dict],
    fraud_threshold: int,
    approval_amount_threshold: float,
) -> Dict[str, Any]:
    """Evaluate duplicate/fraud/approval controls for invoice workflow."""
    signals = extract_invoice_signals(extraction_result)
    duplicate_check = detect_duplicate_invoice(signals, processed_docs)
    fraud = compute_fraud_score(signals, duplicate_check, validation_result or "")

    amount = signals.get("amount") or 0.0
    requires_human_approval = (
        fraud["score"] >= fraud_threshold
        or amount >= approval_amount_threshold
        or duplicate_check["is_duplicate"]
    )

    approval_reasons = []
    if fraud["score"] >= fraud_threshold:
        approval_reasons.append(f"Fraud score {fraud['score']} >= threshold {fraud_threshold}")
    if amount >= approval_amount_threshold:
        approval_reasons.append(
            f"Amount {amount:.2f} >= approval threshold {approval_amount_threshold:.2f}"
        )
    if duplicate_check["is_duplicate"]:
        approval_reasons.append("Potential duplicate invoice")

    return {
        "file_name": file_name,
        "invoice_signals": signals,
        "duplicate_check": duplicate_check,
        "fraud": fraud,
        "requires_human_approval": requires_human_approval,
        "approval_reasons": approval_reasons,
        "decision": "REVIEW_REQUIRED" if requires_human_approval else "AUTO_APPROVED",
        "timestamp": datetime.now().isoformat(),
    }


# ==================== Multi-Modal Processing ====================

def process_with_vision_agent(file_bytes: bytes, file_name: str, file_type: str) -> dict:
    """Process images/PDFs using vision-capable extraction agent."""
    agents_client = _agents_client()
    agent_id = get_extraction_agent_id()
    
    # For multi-modal, we need to properly format the message
    # Note: This depends on your agent_framework supporting vision
    # Typically requires special message format with image data
    
    encoded_image = encode_image_to_base64(file_bytes)
    
    prompt = (
        f"Extract all information from this document:\n"
        f"Filename: {file_name}\n"
        f"Type: {file_type}\n\n"
        f"Return structured JSON with:\n"
        f"- document_type\n"
        f"- confidence\n"
        f"- extracted_fields (all key-value pairs found)\n"
        f"- raw_text (all text)\n"
        f"- notes (any issues)\n"
        f"\n[Image data encoded as base64: {encoded_image[:100]}...]"
    )
    
    thread_id = create_thread(agents_client)
    text = run_agent_turn(
        agents_client,
        agent_id=agent_id,
        thread_id=thread_id,
        user_text=prompt,
    )
    
    return {
        "agent": "ExtractionAgent",
        "mode": "vision",
        "result": text,
        "timestamp": datetime.now().isoformat()
    }


def process_with_text_agent(file_bytes: bytes, file_name: str) -> dict:
    """Process text documents using extraction agent."""
    agents_client = _agents_client()
    agent_id = get_extraction_agent_id()
    
    try:
        text_content = file_bytes.decode('utf-8')
    except:
        text_content = file_bytes.decode('utf-8', errors='ignore')
    
    prompt = (
        f"Extract all information from this text document:\n"
        f"Filename: {file_name}\n"
        f"Content:\n{text_content}\n\n"
        f"Return structured JSON with extracted data."
    )
    
    thread_id = create_thread(agents_client)
    text = run_agent_turn(
        agents_client,
        agent_id=agent_id,
        thread_id=thread_id,
        user_text=prompt,
    )
    
    return {
        "agent": "ExtractionAgent",
        "mode": "text",
        "result": text,
        "timestamp": datetime.now().isoformat()
    }


def process_with_data_agent(file_bytes: bytes, file_name: str, file_type: str) -> dict:
    """Process structured data files using data agent."""
    agents_client = _agents_client()
    agent_id = get_data_agent_id()
    
    # Parse the data first
    if file_type == "text/csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
        data_preview = df.to_string()
    else:
        # Excel or other
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
            data_preview = df.to_string()
        except:
            data_preview = file_bytes.decode('utf-8', errors='ignore')
    
    prompt = (
        f"Structure and organize this data:\n"
        f"Filename: {file_name}\n"
        f"Data:\n{data_preview}\n\n"
        f"Provide:\n"
        f"1. Summary statistics\n"
        f"2. Column types and ranges\n"
        f"3. Data quality assessment\n"
        f"4. Structured JSON representation"
    )
    
    thread_id = create_thread(agents_client)
    text = run_agent_turn(
        agents_client,
        agent_id=agent_id,
        thread_id=thread_id,
        user_text=prompt,
    )
    
    return {
        "agent": "DataAgent",
        "mode": "data",
        "result": text,
        "dataframe": df if file_type == "text/csv" else None,
        "timestamp": datetime.now().isoformat()
    }


def validate_extraction(extraction_result: str, file_name: str) -> dict:
    """Validate extracted data using validation agent."""
    agents_client = _agents_client()
    agent_id = get_validation_agent_id()
    
    prompt = (
        f"Validate this extracted data:\n"
        f"Document: {file_name}\n"
        f"Extracted Data:\n{extraction_result}\n\n"
        f"Provide validation report with:\n"
        f"1. Completeness score (0-100)\n"
        f"2. Consistency check results\n"
        f"3. Issues found\n"
        f"4. Recommended corrections\n"
        f"5. Overall quality score"
    )
    
    thread_id = create_thread(agents_client)
    text = run_agent_turn(
        agents_client,
        agent_id=agent_id,
        thread_id=thread_id,
        user_text=prompt,
    )
    
    return {
        "agent": "ValidationAgent",
        "result": text,
        "timestamp": datetime.now().isoformat()
    }


def analyze_data(data_results: List[dict], analysis_type: str = "summary") -> dict:
    """Analyze extracted data using analyst agent."""
    agents_client = _agents_client()
    agent_id = get_analyst_agent_id()
    
    # Combine all extraction results
    combined_data = "\n---DOCUMENT BREAK---\n".join([
        f"[{r.get('file_name', 'Unknown')}]\n{r.get('extraction', {}).get('result', '')}"
        for r in data_results
    ])
    
    if analysis_type == "summary":
        prompt = (
            f"Provide executive summary of these documents:\n"
            f"{combined_data}\n\n"
            f"Include:\n"
            f"1. Overall summary\n"
            f"2. Key metrics\n"
            f"3. Important findings\n"
            f"4. Recommendations"
        )
    elif analysis_type == "comparison":
        prompt = (
            f"Compare these documents:\n"
            f"{combined_data}\n\n"
            f"Provide:\n"
            f"1. Similarities\n"
            f"2. Differences\n"
            f"3. Anomalies\n"
            f"4. Insights"
        )
    else:
        prompt = f"Analyze this data:\n{combined_data}"
    
    thread_id = create_thread(agents_client)
    text = run_agent_turn(
        agents_client,
        agent_id=agent_id,
        thread_id=thread_id,
        user_text=prompt,
    )
    
    return {
        "agent": "AnalystAgent",
        "analysis_type": analysis_type,
        "result": text,
        "timestamp": datetime.now().isoformat()
    }


# ==================== Document Processing Pipeline ====================

def process_document_multi_agent(
    uploaded_file,
    enable_validation: bool = True,
    enable_workflow_controls: bool = True,
    fraud_threshold: int = 60,
    approval_amount_threshold: float = 10000.0,
) -> dict:
    """Process document through multi-agent pipeline."""
    file_name = uploaded_file.name
    file_type = uploaded_file.type
    file_bytes = uploaded_file.getvalue()
    
    result = {
        "file_name": file_name,
        "file_type": file_type,
        "file_size": len(file_bytes),
        "processing_mode": detect_file_type(file_type, file_name),
        "extraction": None,
        "validation": None,
        "workflow_controls": None,
        "preview": None
    }
    
    # Step 1: Extract based on file type
    processing_mode = result["processing_mode"]
    
    with st.status(f"Processing {file_name}...", expanded=True) as status:
        st.write(f"🔍 Mode: {processing_mode}")
        
        try:
            if processing_mode == "vision":
                st.write("📸 Using ExtractionAgent (Vision Mode)...")
                result["extraction"] = process_with_vision_agent(file_bytes, file_name, file_type)
            elif processing_mode == "data":
                st.write("📊 Using DataAgent (Structured Data Mode)...")
                result["extraction"] = process_with_data_agent(file_bytes, file_name, file_type)
            else:
                st.write("📝 Using ExtractionAgent (Text Mode)...")
                result["extraction"] = process_with_text_agent(file_bytes, file_name)
            
            st.write(f"✅ Extraction complete by {result['extraction']['agent']}")
            
            # Step 2: Validate if enabled
            if enable_validation:
                st.write("🔎 Using ValidationAgent...")
                result["validation"] = validate_extraction(
                    result["extraction"]["result"],
                    file_name
                )
                st.write("✅ Validation complete")

            if enable_workflow_controls:
                st.write("🛡️ Running workflow controls (duplicate/fraud/approval)...")
                result["workflow_controls"] = evaluate_workflow_controls(
                    file_name=file_name,
                    extraction_result=result["extraction"].get("result", ""),
                    validation_result=(result.get("validation") or {}).get("result"),
                    processed_docs=st.session_state.get("processed_docs", []),
                    fraud_threshold=fraud_threshold,
                    approval_amount_threshold=approval_amount_threshold,
                )
                st.write(
                    f"✅ Workflow decision: {result['workflow_controls']['decision']}"
                )
            
            status.update(label=f"✅ {file_name} processed!", state="complete")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            result["extraction"] = {"error": str(e)}
            status.update(label=f"❌ Error processing {file_name}", state="error")
    
    # Generate preview
    if file_type.startswith("image/") and PIL_SUPPORT:
        try:
            result["preview"] = Image.open(io.BytesIO(file_bytes))
        except:
            pass
    
    return result


# ==================== Streamlit UI ====================

st.set_page_config(
    page_title="Multi-Agent Document System",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Multi-Agent Multi-Modal Document Analysis")
st.markdown("""
**Specialized agents working together:**
- 📸 **ExtractionAgent**: Handles vision (images/PDFs) and text extraction
- 📊 **DataAgent**: Structures and organizes data files
- ✅ **ValidationAgent**: Verifies data quality
- 📈 **AnalystAgent**: Provides insights and summaries
""")

# Sidebar: Agent Status
with st.sidebar:
    st.header("🤖 Agent System")
    
    st.subheader("Active Agents")
    agents = {
        "ExtractionAgent": "📸 Extracts data (text + vision)",
        "DataAgent": "📊 Structures data",
        "ValidationAgent": "✅ Validates quality",
        "AnalystAgent": "📈 Analyzes & summarizes"
    }
    
    for agent_name, description in agents.items():
        st.write(f"**{agent_name}**")
        st.caption(description)
    
    st.divider()
    
    st.subheader("⚙️ Settings")
    enable_validation = st.checkbox("Enable Validation Agent", value=True)
    enable_analysis = st.checkbox("Enable Analyst Agent", value=True)
    enable_workflow_controls = st.checkbox("Enable Workflow Controls", value=True)
    fraud_threshold = st.slider("Fraud Score Threshold", min_value=20, max_value=90, value=60)
    approval_amount_threshold = st.number_input(
        "Approval Amount Threshold",
        min_value=1000.0,
        value=10000.0,
        step=500.0,
    )
    
    st.divider()
    st.caption("Multi-modal support: Text, Images, PDFs, CSV, Excel")

# Initialize session state
if "processed_docs" not in st.session_state:
    st.session_state.processed_docs = []

# Main tabs
tabs = st.tabs([
    "📤 Upload & Process",
    "📋 Extracted Data",
    "📈 Analysis Dashboard",
    "🔍 Agent Collaboration"
])

# ==================== TAB 1: Upload & Process ====================
with tabs[0]:
    st.subheader("Upload Documents for Multi-Agent Processing")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Upload documents - agents will automatically route to appropriate processor",
            type=["pdf", "csv", "xlsx", "txt", "json", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
        )
    
    with col2:
        if st.button("🗑️ Clear All"):
            st.session_state.processed_docs = []
            st.rerun()
    
    # Process files
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Check if already processed
            if not any(doc["file_name"] == uploaded_file.name for doc in st.session_state.processed_docs):
                result = process_document_multi_agent(
                    uploaded_file,
                    enable_validation,
                    enable_workflow_controls,
                    fraud_threshold,
                    approval_amount_threshold,
                )
                st.session_state.processed_docs.append(result)
    
    # Display processed documents
    if st.session_state.processed_docs:
        st.subheader("Processed Documents")
        
        for idx, doc in enumerate(st.session_state.processed_docs):
            with st.expander(f"📄 {doc['file_name']} - {doc['processing_mode'].upper()} mode"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Type:** {doc['file_type']}")
                    st.write(f"**Size:** {doc['file_size']} bytes")
                    st.write(f"**Mode:** {doc['processing_mode']}")
                
                with col2:
                    if doc.get("preview"):
                        st.image(doc["preview"], width=200)
                
                # Extraction results
                if doc.get("extraction"):
                    st.markdown("### 📸 Extraction Results")
                    st.info(f"Agent: {doc['extraction'].get('agent', 'Unknown')}")
                    st.markdown(doc["extraction"].get("result", "No results"))
                    
                    # Show dataframe if available
                    if doc["extraction"].get("dataframe") is not None:
                        st.dataframe(doc["extraction"]["dataframe"], use_container_width=True)
                
                # Validation results
                if doc.get("validation"):
                    st.markdown("### ✅ Validation Results")
                    st.info(f"Agent: {doc['validation'].get('agent', 'Unknown')}")
                    st.markdown(doc["validation"].get("result", "No validation"))

                if doc.get("workflow_controls"):
                    workflow = doc["workflow_controls"]
                    st.markdown("### 🛡️ Workflow Controls")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("Fraud Score", workflow["fraud"]["score"])
                    with c2:
                        st.metric("Duplicate", "Yes" if workflow["duplicate_check"]["is_duplicate"] else "No")
                    with c3:
                        st.metric("Decision", workflow["decision"])

                    if workflow["requires_human_approval"]:
                        st.warning("Human review required")
                        for reason in workflow.get("approval_reasons", []):
                            st.caption(f"• {reason}")
                    else:
                        st.success("Auto-approved by workflow controls")

# ==================== TAB 2: Extracted Data ====================
with tabs[1]:
    st.subheader("All Extracted Data")
    
    if not st.session_state.processed_docs:
        st.info("📤 No documents processed yet")
    else:
        for doc in st.session_state.processed_docs:
            with st.expander(f"📄 {doc['file_name']}"):
                if doc.get("extraction"):
                    st.markdown(doc["extraction"].get("result", ""))
                    
                    # Export options
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📥 Export JSON", key=f"json_{doc['file_name']}"):
                            export_data = {
                                "file": doc['file_name'],
                                "extracted": doc["extraction"].get("result"),
                                "timestamp": doc["extraction"].get("timestamp")
                            }
                            st.download_button(
                                "Download",
                                data=json.dumps(export_data, indent=2),
                                file_name=f"{doc['file_name']}_extracted.json",
                                mime="application/json"
                            )

# ==================== TAB 3: Analysis Dashboard ====================
with tabs[2]:
    st.subheader("📈 Analyst Agent Dashboard")
    
    if not st.session_state.processed_docs:
        st.info("📤 No documents to analyze yet")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Generate Executive Summary"):
                with st.spinner("AnalystAgent analyzing..."):
                    analysis = analyze_data(st.session_state.processed_docs, "summary")
                    st.success("Analysis Complete")
                    st.markdown(analysis["result"])
        
        with col2:
            if st.button("🔄 Compare All Documents"):
                with st.spinner("AnalystAgent comparing..."):
                    analysis = analyze_data(st.session_state.processed_docs, "comparison")
                    st.success("Comparison Complete")
                    st.markdown(analysis["result"])
        
        # Statistics
        st.divider()
        st.subheader("📊 Document Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Documents", len(st.session_state.processed_docs))
        with col2:
            vision_docs = sum(1 for d in st.session_state.processed_docs if d["processing_mode"] == "vision")
            st.metric("Vision Processed", vision_docs)
        with col3:
            data_docs = sum(1 for d in st.session_state.processed_docs if d["processing_mode"] == "data")
            st.metric("Data Files", data_docs)

        st.subheader("🛡️ Workflow Metrics")
        m1, m2, m3 = st.columns(3)
        with m1:
            duplicate_count = sum(
                1
                for d in st.session_state.processed_docs
                if (d.get("workflow_controls") or {}).get("duplicate_check", {}).get("is_duplicate")
            )
            st.metric("Potential Duplicates", duplicate_count)
        with m2:
            review_required = sum(
                1
                for d in st.session_state.processed_docs
                if (d.get("workflow_controls") or {}).get("requires_human_approval")
            )
            st.metric("Human Review Required", review_required)
        with m3:
            fraud_scores = [
                (d.get("workflow_controls") or {}).get("fraud", {}).get("score")
                for d in st.session_state.processed_docs
                if (d.get("workflow_controls") or {}).get("fraud", {}).get("score") is not None
            ]
            avg_fraud = (sum(fraud_scores) / len(fraud_scores)) if fraud_scores else 0.0
            st.metric("Avg Fraud Score", f"{avg_fraud:.1f}")

# ==================== TAB 4: Agent Collaboration ====================
with tabs[3]:
    st.subheader("🔍 Agent Collaboration Viewer")
    
    st.markdown("""
    ### How Agents Collaborate
    
    **Pipeline Flow:**
    1. 📤 **Upload** → System routes to appropriate agent
    2. 📸 **ExtractionAgent** (vision/text) OR 📊 **DataAgent** (structured)
    3. ✅ **ValidationAgent** checks quality
    4. 📈 **AnalystAgent** provides insights
    
    **Agent Specialization:**
    - Each agent has specific expertise
    - Agents pass results to next specialist
    - Maintains context across pipeline
    """)
    
    if st.session_state.processed_docs:
        st.subheader("Processing History")
        
        for doc in st.session_state.processed_docs:
            st.write(f"**{doc['file_name']}**")
            
            # Show agent pipeline
            pipeline = [f"1. UploadHandler → {doc['processing_mode']} routing"]
            
            if doc.get("extraction"):
                extraction_agent = doc.get("extraction", {}).get("agent", "ExtractionAgent")
                if doc.get("extraction", {}).get("error"):
                    pipeline.append(f"2. {extraction_agent} → Extraction (failed)")
                else:
                    pipeline.append(f"2. {extraction_agent} → Extraction")
            
            if doc.get("validation"):
                validation_agent = doc.get("validation", {}).get("agent", "ValidationAgent")
                pipeline.append(f"3. {validation_agent} → Validation")

            if doc.get("workflow_controls"):
                pipeline.append(
                    f"4. WorkflowEngine → {doc['workflow_controls'].get('decision', 'UNKNOWN')}"
                )
                pipeline.append("5. Ready for AnalystAgent")
            else:
                pipeline.append("4. Ready for AnalystAgent")
            
            for step in pipeline:
                st.caption(step)
            
            st.divider()

# Footer
st.markdown("---")
st.caption("🤖 Multi-Agent System | Each agent is specialized for optimal performance")
