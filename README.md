# Invoice Processing Agent – Microsoft Foundry Demo

A comprehensive demonstration of building AI-powered invoice processing agents using Microsoft Foundry (for model/project management) with the Agent Framework. This project shows progressive complexity from basic agents to multi-tool workflows with business logic.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Step-by-Step Guide](#step-by-step-guide)
- [Enhancement Roadmap](#enhancement-roadmap)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🎯 Overview

This project demonstrates how to build intelligent invoice processing systems using AI agents. It covers:

- **Basic Agent Creation**: Simple invoice summarization
- **Memory Management**: Conversation context with thread-based memory
- **Tool Integration**: Custom functions for extraction and validation
- **Business Logic**: Approval workflows and conditional processing
- **Model Endpoint Integration**: Production-ready authentication and configuration

### Use Cases

- Automated invoice data extraction
- Invoice validation and approval workflows
- Conversational invoice queries
- Multi-step invoice processing pipelines
- Compliance and audit trail generation

## 🏗️ Architecture

```
┌─────────────────┐
│   User Input    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent Engine   │ ◄─── Instructions & Tools
└────────┬────────┘
         │
         ▼
┌──────────────────────────────┐
│ Model Deployment             │ (managed via Foundry)
│  Chat Client (OpenAI-style)  │
└───────────────┬──────────────┘
         │
         ▼
┌─────────────────┐
│  Tool Execution │ (Extract, Validate, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Output      │
└─────────────────┘
```

## 📋 Prerequisites

- **Python**: 3.8 or higher (3.11 recommended)
- **Microsoft Foundry + model endpoint**:
   - A model deployment (created/managed in Microsoft Foundry)
   - A compatible endpoint and Entra ID (keyless) access to call that deployment
- **Libraries** (installed via `requirements.txt`):
   - `agent-framework`
   - `python-dotenv`
   - `streamlit` (only needed for the Streamlit demos)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd invoice-agent-demo_keyless
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate virtual environment**
   - Windows:
     ```powershell
     .venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Model Endpoint Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini

# Optional: Advanced Configuration
AZURE_OPENAI_API_VERSION=2024-02-01
LOG_LEVEL=INFO
```

Notes:
- `AZURE_OPENAI_DEPLOYMENT` is the preferred variable name. For compatibility, the code also accepts `AZURE_OPENAI_DEPLOYMENT_NAME`.
- The endpoint must be a resource-style model endpoint (for this repo’s default client: `https://<resource>.openai.azure.com/`). Microsoft Foundry *project* URLs are different and won’t work as `AZURE_OPENAI_ENDPOINT`.

#### Keyless authentication (recommended)

This repo uses keyless auth via Microsoft Entra ID.

1. Ensure your identity has access to the Azure OpenAI resource (RBAC): assign the **Cognitive Services OpenAI User** role on the Azure OpenAI resource (or resource group).
2. Authenticate:
   - Local dev: `az login` (or VS Code Azure sign-in)
   - Azure compute: enable Managed Identity (system-assigned or user-assigned). For user-assigned MI, set `AZURE_CLIENT_ID`.

Optional:
- `AZURE_OPENAI_TOKEN_ENDPOINT` (defaults to `https://cognitiveservices.azure.com/.default`).

### Security Best Practices

⚠️ **Never commit secrets to version control!**

- Use environment variables for sensitive data
- Add `.env` to `.gitignore`
- Use Managed Identity in production (where supported)
- Use Key Vault (or another secret store) for other secrets (if applicable)

## 💻 Usage

### Running the Examples

Each step file demonstrates different capabilities:

1. **Basic Agent (Step 1)**
   ```bash
   python step1_basic_agent.py
   ```
   Processes a single invoice and returns a summary.

2. **Thread Memory (Step 2)**
   ```bash
   python step2_thread_memory.py
   ```
   Maintains conversation context for follow-up questions.

3. **Single Tool (Step 3)**
   ```bash
   python step3_invoice_tool.py
   ```
   Uses custom extraction tool for structured data.

4. **Multiple Tools (Step 3 - Alternative)**
   ```bash
   python step3_invoice_tools.py
   ```
   Chains extraction and validation tools together.

5. **Advanced Validation (Step 4)**
   ```bash
   python step4_validation_tool.py
   ```
   Implements business rules and approval thresholds.

## 📁 Project Structure

```
invoice-agent-demo_keyless/
├── client.py                   # Model endpoint client configuration
├── step1_basic_agent.py        # Basic invoice summarization
├── step2_thread_memory.py      # Conversation memory demo
├── step3_invoice_tool.py       # Single tool usage
├── step3_invoice_tools.py      # Multiple tools workflow
├── step4_validation_tool.py    # Business logic validation
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in repo)
├── .env.example                # Example environment file
└── README.md                   # This file
```

## 📚 Step-by-Step Guide

### Step 1: Basic Agent

**Purpose**: Understand agent creation and basic execution

**Key Concepts**:
- Agent initialization
- Simple instruction-based processing
- Single-turn interaction

**Example**:
```python
agent = Agent(client=get_chat_client(), instructions='Summarize invoice data.')
result = await agent.run('Invoice INV-1001 from Contoso for 1200 USD')
```

### Step 2: Thread Memory

**Purpose**: Maintain conversation context

**Key Concepts**:
- Thread creation and management
- Multi-turn conversations
- Context retention across messages

**Example**:
```python
thread = agent.get_new_thread()
await agent.run('Invoice from Contoso for 1200 USD', thread=thread)
result = await agent.run('What is the total amount?', thread=thread)
```

### Step 3: Tools

**Purpose**: Extend agent capabilities with custom functions

**Key Concepts**:
- Tool decoration and registration
- Function calling by LLM
- Structured data extraction
- Multi-tool orchestration

**Example**:
```python
@tool(name="extract_invoice", description="Extract invoice data")
def extract_invoice(text: str) -> dict:
    return {"vendor": "Contoso", "amount": 1200, "currency": "USD"}

agent = Agent(client=get_chat_client(), tools=[extract_invoice])
```

### Step 4: Business Logic

**Purpose**: Implement real-world validation rules

**Key Concepts**:
- Conditional logic in tools
- Approval workflows
- Threshold-based processing

**Example**:
```python
def validate_invoice(amount: int, currency: str) -> str:
    return "REQUIRES_APPROVAL" if amount > 10000 else "APPROVED"
```

## 🚀 Enhancement Roadmap

### Phase 1: Core Improvements
- [ ] Centralize config and secrets (if any) in a secret store (for example Key Vault)
- [ ] Add comprehensive error handling
- [ ] Implement structured logging
- [ ] Add unit and integration tests
- [ ] Create performance benchmarks

### Phase 2: Feature Expansion
- [ ] Real invoice parsing (OCR/PDF)
- [ ] Database integration for persistence
- [ ] Multi-user support with authentication
- [ ] REST API endpoint creation
- [ ] Web UI dashboard

### Phase 3: Advanced Capabilities
- [ ] Multi-currency support with conversion
- [ ] Line-item extraction
- [ ] Duplicate detection
- [ ] Fraud detection with ML
- [ ] Integration with accounting systems (SAP, QuickBooks)

### Phase 4: Enterprise Features
- [ ] Multi-tier approval workflows
- [ ] Email/Slack notifications
- [ ] Comprehensive audit trails
- [ ] Analytics and reporting dashboard
- [ ] Batch processing capabilities
- [ ] High-availability deployment

## ✅ Best Practices

### Security
- Prefer keyless auth (Managed Identity / Entra ID)
- Use environment variables or a secret store (for example Key Vault) for other secrets
- Implement least-privilege access
- Enable audit logging
- Regular security assessments

### Performance
- Implement connection pooling
- Use async/await for concurrent operations
- Cache frequently accessed data
- Monitor token usage and costs
- Implement rate limiting

### Reliability
- Add retry logic with exponential backoff
- Implement circuit breakers
- Comprehensive error handling
- Health checks and monitoring
- Graceful degradation

### Code Quality
- Follow PEP 8 style guidelines
- Write comprehensive docstrings
- Maintain high test coverage
- Use type hints
- Regular code reviews

## 🔧 Troubleshooting

### Common Issues

**Issue**: `401 Unauthorized` error
- **Solution**: Ensure you are signed in (`az login`) or Managed Identity is enabled
- Verify endpoint URL is accurate
- Ensure RBAC is configured (role: **Cognitive Services OpenAI User**)

**Issue**: `404 Resource not found`
- **Solution**: Verify the deployment/model name matches what you configured in Foundry / your provider portal
- Check endpoint URL format (no `/openai/v1/` suffix for AzureOpenAIChatClient)

**Issue**: `400 API version not supported`
- **Solution**: Update to supported API version (2024-02-01, 2023-12-01-preview)
- Check your provider documentation / deployment portal for available versions

**Issue**: Slow response times
- **Solution**: Monitor token usage
- Optimize prompts for brevity
- Consider using smaller models for simple tasks

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request



---

**Note**: This is a demonstration project. For production use, implement proper security, error handling, and testing.
