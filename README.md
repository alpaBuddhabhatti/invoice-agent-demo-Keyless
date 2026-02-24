# Invoice Processing Agent – Microsoft Foundry Demo (Keyless)

Demo project showing how to build AI-powered invoice processing agents using Microsoft Foundry (project + model deployment) with the Foundry SDKs (`azure-ai-projects` + `azure-ai-agents`).

This repo is **keyless-only**: authentication uses Microsoft Entra ID (no API keys).

## 🚀 Quickstart (new user)

1. Create + activate a virtual environment
   - Windows (PowerShell)
     ```powershell
     py -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - macOS/Linux
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. Install dependencies
   ```bash
   python -m pip install -r requirements.txt
   python -m pip check
   ```

3. Configure `.env`
   ```env
   FOUNDRY_PROJECT_ENDPOINT=https://<your-project>.services.ai.azure.com/api/projects/<project>
   MODEL_DEPLOYMENT_NAME=<your-deployment-name>
   ```

4. Sign in (keyless auth)
   ```bash
   az login
   ```

5. Run the step demos
   ```bash
   python step1_basic_agent.py
   python step2_thread_memory.py
   python step3_invoice_tool.py
   python step3_invoice_tools.py
   python step4_validation_tool.py
   ```

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Frameworks: Agent Framework vs Foundry Agents](#-frameworks-agent-framework-vs-foundry-agents)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Streamlit Demos](#streamlit-demos)
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
│ Foundry Project +            │
│ Model Deployment             │
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

## 🧩 Frameworks: Agent Framework vs Foundry Agents

You may see two very similar-looking invoice demos:

- **This repo** uses **Azure AI Foundry (project) + the Foundry Agents SDK** (`azure-ai-projects` + `azure-ai-agents`).
- Another repo may use **`agent_framework`** (a Python library with `Agent(...)`, `@tool`, and `agent.run(...)`).

Even though both are “agent apps”, they are different layers.

### What’s the difference?

**1) Where the agent runtime lives**

- **`agent_framework` (library / in-process runtime)**
   - The agent orchestration loop runs **inside your Python process**.
   - Tools are normal Python callables; the framework invokes them locally.
   - Memory/state is usually managed in your app (or whatever the framework stores in-process).

- **Foundry managed Agents (`azure-ai-agents`)**
   - Agents, threads, messages, and runs are **first-class service concepts**.
   - You create an agent (gets an `agent_id`), create a thread, then create/process runs.
   - Tool calling is integrated via a **toolset**; local function execution may require explicit enablement (example: `enable_auto_function_calls(...)`).

**2) What Foundry adds (vs just calling a model endpoint)**

Foundry provides a *project-centric* experience for deploying/organizing model deployments and typically pairs well with evaluation, tracing, and governance. It’s not “just auth”; it’s a higher-level platform concept around AI app development.

**3) Keyless vs API keys is orthogonal**

Keyless (Entra ID) vs API key is an authentication choice. Either style of app can be written to use keyless auth *if the underlying client supports it*. The bigger architectural split is **in-process library agent runtime** vs **managed Agents service runtime**.

### Quick visual

```
In-process agent library (agent_framework)         Managed agent runtime (Foundry Agents)

your_app.py                                        your_app.py
   |                                                  |
   | Agent.run(...)                                   | AgentsClient.create_agent(...)
   |  - framework plans + loops                       | AgentsClient.threads.create(...)
   |  - framework invokes tools locally               | AgentsClient.runs.create_and_process(...)
   v                                                  v
Model API (chat)                                 Foundry Agent Run (service)
                                                                            |  - may request tool calls
                                                                            v
                                                                        Tool execution + submit outputs
```

### How to recognize which one you’re looking at

- **Foundry managed Agents (this repo)**
   - See `client.py`: uses `AIProjectClient` / `AgentsClient`, and functions like `ensure_agent(...)`, `create_thread(...)`, `run_agent_turn(...)`.
   - See `step3_invoice_tools.py`: uses `ToolSet` + `FunctionTool` and enables local tool execution via `agents_client.enable_auto_function_calls(toolset)`.
   - Streamlit apps store `agent.id` and call runs/threads via `run_agent_turn(...)`.

- **agent_framework repo (library runtime)**
   - You’ll see `from agent_framework import Agent, tool`.
   - Agents are created like `Agent(client=..., tools=[...])` and run with `await agent.run(...)`.

### Proof by imports (quick check)

If you’re unsure which style a repo is using, check for these *signature imports*.

**Foundry managed Agents (this repo)**

```python
# Foundry Project + managed Agents clients
from azure.ai.projects import AIProjectClient
from azure.ai.agents import AgentsClient

# Toolsets for local function tools
from azure.ai.agents.models import FunctionTool, ToolSet
```

**agent_framework (library runtime + Azure OpenAI client)**

```python
from agent_framework import Agent, tool
from agent_framework.azure import AzureOpenAIChatClient
```

### Which should you use?

- Choose **Foundry managed Agents** when you want a more “platform-native” agent lifecycle (agents/threads/runs), and easier alignment with enterprise app patterns.
- Choose **agent_framework** when you want the simplest Python-first experience for demos/prototyping where you control the loop in-process.

## 📋 Prerequisites

- **Python**: 3.11+ recommended
- **Microsoft Foundry + model endpoint**:
   - A model deployment (created/managed in Microsoft Foundry)
   - A compatible endpoint and Entra ID (keyless) access to call that deployment
- **Libraries** (installed via `requirements.txt`):
   - `azure-ai-projects`
   - `azure-ai-agents`
   - `python-dotenv`
   - `streamlit` (only needed for the Streamlit demos)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd invoice-agent-demo-Keyless
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
   pip check
   ```

### Windows on ARM notes

Some Python packages may not provide native `win_arm64` wheels.
If you see install errors related to building `cryptography` (Rust toolchain), use one of these options:

- Install and use **Python 3.11 x64** (often has prebuilt wheels available).
- Or force a wheel-only install for `cryptography`:
  ```bash
  pip install "cryptography" --only-binary=:all:
  ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Foundry project configuration
FOUNDRY_PROJECT_ENDPOINT=https://<your-project>.services.ai.azure.com/api/projects/<project>

# Model deployment name configured for your project
MODEL_DEPLOYMENT_NAME=gpt-4o-mini
```

Notes:
- `FOUNDRY_PROJECT_ENDPOINT` is the preferred variable name. For compatibility, the code also accepts `PROJECT_ENDPOINT` and `AZURE_AI_PROJECT_ENDPOINT`.
- `MODEL_DEPLOYMENT_NAME` is the preferred variable name. For compatibility, the code also accepts `AZURE_OPENAI_DEPLOYMENT` and `AZURE_OPENAI_DEPLOYMENT_NAME`.

#### Keyless authentication (recommended)

This repo uses keyless auth via Microsoft Entra ID.

1. Ensure your identity has access to the Foundry-backed model resource (RBAC): assign the **Cognitive Services OpenAI User** role on the underlying Azure AI Services / OpenAI model resource (or resource group), depending on how your Foundry project is configured.
2. Authenticate:
   - Local dev: `az login` (or VS Code Azure sign-in)
   - Azure compute: enable Managed Identity (system-assigned or user-assigned). For user-assigned MI, set `AZURE_CLIENT_ID`.

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

### Streamlit Demos

There are three Streamlit apps. See [STREAMLIT_APPS_GUIDE.md](STREAMLIT_APPS_GUIDE.md) for details.

Run (recommended from the virtualenv):
```bash
python -m streamlit run streamlit_advanced_app.py
python -m streamlit run streamlit_llm_extraction_app.py
python -m streamlit run streamlit_multi_agent_app.py
```

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
from client import create_thread, ensure_agent, get_agents_client, run_agent_turn

agents_client = get_agents_client()
agent = ensure_agent(agents_client, name="BasicInvoiceAgent", instructions="Summarize invoice data.")
thread_id = create_thread(agents_client)
text = run_agent_turn(agents_client, agent_id=agent.id, thread_id=thread_id, user_text="Invoice INV-1001 from Contoso for 1200 USD")
print(text)
```

### Step 2: Thread Memory

**Purpose**: Maintain conversation context

**Key Concepts**:
- Thread creation and management
- Multi-turn conversations
- Context retention across messages

**Example**:
```python
from client import create_thread, ensure_agent, get_agents_client, run_agent_turn

agents_client = get_agents_client()
agent = ensure_agent(agents_client, name="InvoiceQnAAgent", instructions="Answer invoice questions.")
thread_id = create_thread(agents_client)
run_agent_turn(agents_client, agent_id=agent.id, thread_id=thread_id, user_text="Invoice from Contoso for 1200 USD")
text = run_agent_turn(agents_client, agent_id=agent.id, thread_id=thread_id, user_text="What is the total amount?")
print(text)
```

### Step 3: Tools

**Purpose**: Extend agent capabilities with custom functions

**Key Concepts**:
- Tool decoration and registration
- Function calling by LLM
- Structured data extraction
- Multi-tool orchestration

**Example (this repo’s SDK pattern)**:
```python
from azure.ai.agents.models import FunctionTool, ToolSet
from client import get_agents_client

def extract_invoice(text: str) -> dict:
   return {"vendor": "Contoso", "amount": 1200, "currency": "USD"}

agents_client = get_agents_client()
toolset = ToolSet()
toolset.add(FunctionTool({extract_invoice}))

# Required: lets the SDK execute local Python functions during runs.
agents_client.enable_auto_function_calls(toolset)
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

**Issue**: `Import "azure.ai.agents.models._patch" could not be resolved`
- **Solution**: This repo uses the public imports: `from azure.ai.agents.models import FunctionTool, ToolSet`.

**Issue**: Tool calls not executing (agent says it can’t call functions)
- **Solution**: Ensure your code calls `agents_client.enable_auto_function_calls(toolset)` before running.

**Issue**: `cryptography` install fails on Windows ARM
- **Solution**: Use Python 3.11 x64, or install `cryptography` with `--only-binary=:all:` as described in Installation.

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
