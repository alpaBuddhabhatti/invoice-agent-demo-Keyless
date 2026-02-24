
"""
Advanced Streamlit Document Analyzer with LLM
==============================================
Uses Azure OpenAI LLM to intelligently read and analyze:
    - PDF documents
    - CSV/Excel files
    - Images with OCR
    - JSON data
    - Text files

Features:
    - Multi-file upload
    - Intelligent document understanding via LLM
    - Q&A on document content
    - Data extraction and summarization
    - Document comparison
    - Export results
"""

from __future__ import annotations

import asyncio
import io
import json
import os
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

# PDF support
try:
    from pdf2image import convert_from_bytes
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# OCR support
try:
    import easyocr
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

# Numpy (used for OCR image arrays)
try:
    import numpy as np
    NUMPY_SUPPORT = True
except ImportError:
    NUMPY_SUPPORT = False

# Image support
try:
    from PIL import Image
    PIL_SUPPORT = True
except ImportError:
    PIL_SUPPORT = False

# CSV/Excel support
try:
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

from client import create_thread, ensure_agent, get_agents_client, run_agent_turn


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


@st.cache_resource
def get_ocr_reader():
    """Initialize OCR reader (cached for performance)."""
    if not OCR_SUPPORT:
        return None
    return easyocr.Reader(['en'])


def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract text from image using OCR."""
    if not OCR_SUPPORT or not PIL_SUPPORT or not NUMPY_SUPPORT:
        return "[OCR not available - install easyocr, pillow, and numpy]"

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_array = np.array(image)
        reader = get_ocr_reader()
        results = reader.readtext(image_array)
        text = '\n'.join([line[1] for line in results])
        return text if text.strip() else "[No text detected in image]"
    except Exception as e:
        return f"[Error processing image: {str(e)}]"


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF (with fallback to image OCR)."""
    if not PDF_SUPPORT:
        return "[PDF support not available]"

    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = pypdf.PdfReader(pdf_file)
        all_text = []
        
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                all_text.append(f"--- PAGE {page_num + 1} ---\n{text}")
        
        return '\n'.join(all_text) if all_text else "[No text extracted]"
    except Exception as e:
        return f"[Error: {str(e)}]"


def extract_data_from_csv(csv_bytes: bytes) -> tuple[str, pd.DataFrame]:
    """Extract data from CSV file."""
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        text = df.to_string()
        return text, df
    except Exception as e:
        return f"[Error reading CSV: {str(e)}]", None


def extract_data_from_excel(excel_bytes: bytes) -> tuple[str, dict]:
    """Extract data from Excel file."""
    if not EXCEL_SUPPORT:
        return "[Excel support not available]", None
    
    try:
        excel_file = io.BytesIO(excel_bytes)
        dfs = pd.read_excel(excel_file, sheet_name=None)
        text_data = {}
        for sheet_name, df in dfs.items():
            text_data[sheet_name] = df.to_string()
        combined_text = '\n---SHEET BREAK---\n'.join(
            [f"[{name}]\n{text}" for name, text in text_data.items()]
        )
        return combined_text, dfs
    except Exception as e:
        return f"[Error reading Excel: {str(e)}]", None


def extract_data_from_json(json_bytes: bytes) -> str:
    """Extract data from JSON file."""
    try:
        data = json.loads(json_bytes.decode('utf-8'))
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"[Error reading JSON: {str(e)}]"


def get_llm_agent_id() -> str:
    """Get or create the Foundry agent used for document analysis."""
    if "llm_agent_id" not in st.session_state:
        agents_client = _agents_client()
        agent = ensure_agent(
            agents_client,
            name="DocumentAnalyst",
            instructions=(
                "You are an expert document analyst. Your role is to:\n"
                "1. Read and understand uploaded documents\n"
                "2. Extract key information accurately\n"
                "3. Answer detailed questions about document content\n"
                "4. Summarize documents concisely\n"
                "5. Identify patterns and relationships in data\n"
                "6. Provide insights and recommendations\n"
                "\n"
                "Always be precise, cite specific parts of the document, "
                "and ask for clarification if needed."
            ),
        )
        st.session_state.llm_agent_id = agent.id
    return st.session_state.llm_agent_id


def get_thread():
    """Get or create conversation thread (Foundry thread id)."""
    if "analysis_thread_id" not in st.session_state:
        st.session_state.analysis_thread_id = create_thread(_agents_client())
    return st.session_state.analysis_thread_id


def analyze_with_llm(prompt: str, use_thread: bool = True) -> str:
    """Run LLM analysis."""
    agents_client = _agents_client()
    agent_id = get_llm_agent_id()
    thread_id = get_thread() if use_thread else create_thread(agents_client)
    return run_agent_turn(
        agents_client,
        agent_id=agent_id,
        thread_id=thread_id,
        user_text=prompt,
    )


# ==================== File Processing ====================

def process_uploaded_file(uploaded_file) -> dict:
    """Process uploaded file and extract content."""
    file_type = uploaded_file.type
    file_name = uploaded_file.name
    raw_bytes = uploaded_file.getvalue()
    
    result = {
        "name": file_name,
        "type": file_type,
        "size": len(raw_bytes),
        "content": "",
        "dataframe": None,
        "preview": ""
    }
    
    try:
        if file_type == "application/pdf":
            st.info("📄 Extracting text from PDF...")
            result["content"] = extract_text_from_pdf(raw_bytes)
        
        elif file_type == "text/csv":
            st.info("📊 Reading CSV file...")
            content, df = extract_data_from_csv(raw_bytes)
            result["content"] = content
            result["dataframe"] = df
        
        elif file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            st.info("📈 Reading Excel file...")
            content, dfs = extract_data_from_excel(raw_bytes)
            result["content"] = content
            result["dataframe"] = dfs
        
        elif file_type.startswith("image/"):
            st.info("🔄 Extracting text from image...")
            result["content"] = extract_text_from_image(raw_bytes)
            
            if PIL_SUPPORT:
                try:
                    result["preview"] = Image.open(io.BytesIO(raw_bytes))
                except:
                    pass
        
        elif file_type == "application/json" or file_name.endswith(".json"):
            st.info("📋 Reading JSON file...")
            result["content"] = extract_data_from_json(raw_bytes)
        
        else:
            st.info("📝 Reading text file...")
            result["content"] = raw_bytes.decode("utf-8", errors="ignore")
    
    except Exception as e:
        result["content"] = f"[Error processing file: {str(e)}]"
    
    result["preview"] = result["content"][:500] + ("..." if len(result["content"]) > 500 else "")
    
    return result


# ==================== Streamlit UI ====================

st.set_page_config(page_title="Document Analyzer", page_icon="📄", layout="wide")
st.title("📄 Advanced Document Analyzer with LLM")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    analysis_mode = st.selectbox(
        "Analysis Mode",
        ["Extract & Summarize", "Q&A", "Data Analysis", "Comparison"]
    )
    enable_chat = st.checkbox("Enable Conversation Memory", value=True)

# Initialize session state
if "documents" not in st.session_state:
    st.session_state.documents = {}
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []

# Main tabs
tabs = st.tabs(["📤 Upload & Analyze", "🔍 Q&A", "📊 Data Insights", "📑 Document History"])

# ==================== TAB 1: Upload & Analyze ====================
with tabs[0]:
    st.subheader("Upload Documents")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_files = st.file_uploader(
            "Upload documents (PDF, CSV, Excel, Images, JSON, Text)",
            type=["pdf", "csv", "xlsx", "xls", "json", "txt", "png", "jpg", "jpeg", "bmp"],
            accept_multiple_files=True,
        )
    
    with col2:
        if st.button("🔄 Clear All"):
            st.session_state.documents = {}
            st.rerun()
    
    # Process uploaded files
    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in st.session_state.documents:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    doc_data = process_uploaded_file(uploaded_file)
                    st.session_state.documents[uploaded_file.name] = doc_data
    
    # Display uploaded documents
    if st.session_state.documents:
        st.subheader("Uploaded Documents")
        
        for doc_name, doc_data in st.session_state.documents.items():
            with st.expander(f"📄 {doc_name} ({doc_data['size']} bytes)"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Type:** {doc_data['type']}")
                    st.write(f"**Preview:**")
                    st.code(doc_data["preview"][:300])
                
                with col2:
                    if st.button("🔍 Analyze", key=f"analyze_{doc_name}"):
                        st.session_state.current_doc = doc_name
                
                if doc_data["dataframe"] is not None:
                    if isinstance(doc_data["dataframe"], dict):
                        for sheet_name, df in doc_data["dataframe"].items():
                            st.write(f"**Sheet: {sheet_name}**")
                            st.dataframe(df, use_container_width=True)
                    else:
                        st.dataframe(doc_data["dataframe"], use_container_width=True)
                
                if doc_data["preview"] and PIL_SUPPORT:
                    try:
                        st.image(doc_data["preview"], use_container_width=True)
                    except:
                        pass
    
    # Analysis and summarization
    if st.session_state.documents:
        st.subheader("Quick Analysis")
        
        selected_doc = st.selectbox(
            "Select document to analyze",
            list(st.session_state.documents.keys())
        )
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("📋 Summarize"):
                doc = st.session_state.documents[selected_doc]
                prompt = (
                    f"Please analyze and summarize the following document:\n\n"
                    f"DOCUMENT NAME: {selected_doc}\n"
                    f"CONTENT:\n{doc['content'][:2000]}\n\n"
                    "Provide a concise summary with key points."
                )
                
                with st.spinner("Analyzing..."):
                    summary = analyze_with_llm(prompt, use_thread=enable_chat)
                
                st.success("Analysis Complete")
                st.write(summary)
                st.session_state.analysis_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "document": selected_doc,
                    "action": "Summarize",
                    "result": summary
                })
        
        with col2:
            if st.button("🔑 Extract Key Data"):
                doc = st.session_state.documents[selected_doc]
                prompt = (
                    f"Extract ALL important data from this document:\n\n"
                    f"DOCUMENT NAME: {selected_doc}\n"
                    f"CONTENT:\n{doc['content'][:2000]}\n\n"
                    "Return structured key-value pairs or JSON format where possible."
                )
                
                with st.spinner("Extracting..."):
                    extracted = analyze_with_llm(prompt, use_thread=enable_chat)
                
                st.success("Extraction Complete")
                st.write(extracted)
                st.session_state.analysis_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "document": selected_doc,
                    "action": "Extract",
                    "result": extracted
                })

# ==================== TAB 2: Q&A ====================
with tabs[1]:
    st.subheader("Ask Questions About Documents")
    
    if not st.session_state.documents:
        st.info("📤 Please upload documents first in the Upload & Analyze tab")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_docs = st.multiselect(
                "Select documents for Q&A",
                list(st.session_state.documents.keys()),
                default=list(st.session_state.documents.keys())[:1]
            )
        
        with col2:
            st.write(f"**Docs Selected:** {len(selected_docs)}")
        
        # Chat history
        if "qa_messages" not in st.session_state:
            st.session_state.qa_messages = []
        
        for msg in st.session_state.qa_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # Q&A input
        user_question = st.chat_input("Ask a question about the documents...")
        
        if user_question:
            st.session_state.qa_messages.append({"role": "user", "content": user_question})
            
            with st.chat_message("user"):
                st.write(user_question)
            
            # Prepare context from selected documents
            context = "\n---DOCUMENT BREAK---\n".join([
                f"[{doc_name}]\n{st.session_state.documents[doc_name]['content'][:1000]}"
                for doc_name in selected_docs
            ])
            
            prompt = (
                f"Based on the following documents, answer this question:\n\n"
                f"DOCUMENTS:\n{context}\n\n"
                f"QUESTION: {user_question}\n\n"
                "Provide a detailed answer citing specific parts of the documents."
            )
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = analyze_with_llm(prompt, use_thread=enable_chat)
                st.write(response)
            
            st.session_state.qa_messages.append({"role": "assistant", "content": response})

# ==================== TAB 3: Data Insights ====================
with tabs[2]:
    st.subheader("Data Analysis & Insights")
    
    if not st.session_state.documents:
        st.info("📤 Please upload documents first")
    else:
        # Find documents with dataframes
        data_docs = {
            name: doc for name, doc in st.session_state.documents.items()
            if doc["dataframe"] is not None
        }
        
        if not data_docs:
            st.info("📊 No CSV/Excel files found. Please upload structured data.")
        else:
            selected_data_doc = st.selectbox("Select data file", list(data_docs.keys()))
            
            if st.button("📊 Generate Insights"):
                doc = data_docs[selected_data_doc]
                
                # Convert dataframe to text summary
                if isinstance(doc["dataframe"], dict):
                    data_text = str(doc["dataframe"])
                else:
                    data_text = doc["dataframe"].to_string()
                
                prompt = (
                    f"Analyze this data and provide insights:\n\n"
                    f"DOCUMENT: {selected_data_doc}\n"
                    f"DATA:\n{data_text}\n\n"
                    "Provide: 1) Summary statistics, 2) Key patterns, 3) Anomalies, 4) Recommendations"
                )
                
                with st.spinner("Analyzing data..."):
                    insights = analyze_with_llm(prompt, use_thread=False)
                
                st.success("Analysis Complete")
                st.write(insights)

# ==================== TAB 4: History ====================
with tabs[3]:
    st.subheader("Analysis History")
    
    if not st.session_state.analysis_history:
        st.info("No analysis performed yet")
    else:
        history_df = pd.DataFrame(st.session_state.analysis_history)
        st.dataframe(history_df, use_container_width=True)
        
        if st.button("📥 Download History as CSV"):
            csv = history_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="analysis_history.csv",
                mime="text/csv"
            )
