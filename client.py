"""Foundry client configuration (keyless)
========================================

This repo is keyless-only and uses Microsoft Entra ID credentials to call
Microsoft Foundry (Azure AI Foundry) project endpoints.

Primary clients:
- `AIProjectClient` (azure-ai-projects): project-scoped access and `get_openai_client()`
- `AgentsClient` (azure-ai-agents): create agents/threads/runs and fetch messages

Env vars:
- Project endpoint: `FOUNDRY_PROJECT_ENDPOINT` (preferred), or `PROJECT_ENDPOINT`, or `AZURE_AI_PROJECT_ENDPOINT`
- Model deployment: `MODEL_DEPLOYMENT_NAME` (preferred), or `AZURE_OPENAI_DEPLOYMENT`, or `AZURE_OPENAI_DEPLOYMENT_NAME`

Auth:
- Local dev: `az login` (or VS Code Azure sign-in)
- Azure: Managed Identity (optional `AZURE_CLIENT_ID` for user-assigned identity)
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


def get_project_endpoint() -> str:
    endpoint = (
        os.getenv("FOUNDRY_PROJECT_ENDPOINT")
        or os.getenv("PROJECT_ENDPOINT")
        or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    )
    if not endpoint:
        raise RuntimeError(
            "Missing Foundry project endpoint. Set FOUNDRY_PROJECT_ENDPOINT (preferred) "
            "or PROJECT_ENDPOINT (or AZURE_AI_PROJECT_ENDPOINT)."
        )
    return endpoint


def get_model_deployment_name() -> str:
    model = (
        os.getenv("MODEL_DEPLOYMENT_NAME")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    )
    if not model:
        raise RuntimeError(
            "Missing model deployment name. Set MODEL_DEPLOYMENT_NAME (preferred) "
            "or AZURE_OPENAI_DEPLOYMENT (or AZURE_OPENAI_DEPLOYMENT_NAME)."
        )
    return model


def get_credential():
    try:
        from azure.identity import DefaultAzureCredential
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Keyless auth requires azure-identity. Install it with `pip install azure-identity`."
        ) from e

    return DefaultAzureCredential()


def get_project_client():
    try:
        from azure.ai.projects import AIProjectClient
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Foundry project access requires azure-ai-projects. Install it with `pip install azure-ai-projects`."
        ) from e

    return AIProjectClient(endpoint=get_project_endpoint(), credential=get_credential())


def get_openai_client():
    return get_project_client().get_openai_client()


def get_agents_client():
    try:
        from azure.ai.agents import AgentsClient
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Foundry Agents access requires azure-ai-agents. Install it with `pip install azure-ai-agents`."
        ) from e

    return AgentsClient(endpoint=get_project_endpoint(), credential=get_credential())


def _find_agent_by_name(agents_client, name: str):
    for agent in agents_client.list_agents(limit=100):
        if getattr(agent, "name", None) == name:
            return agent
    return None


def ensure_agent(
    agents_client,
    *,
    name: str,
    instructions: str,
    model: Optional[str] = None,
    description: Optional[str] = None,
    toolset=None,
):
    existing = _find_agent_by_name(agents_client, name)
    if existing is not None:
        return existing

    return agents_client.create_agent(
        name=name,
        model=model or get_model_deployment_name(),
        instructions=instructions,
        description=description,
        toolset=toolset,
    )


def create_thread(agents_client, *, initial_user_message: Optional[str] = None) -> str:
    from azure.ai.agents import models as m

    messages = None
    if initial_user_message:
        messages = [
            m.ThreadMessageOptions(role=m.MessageRole.USER, content=initial_user_message)
        ]
    thread = agents_client.threads.create(messages=messages)
    return thread.id


def get_last_assistant_text(agents_client, *, thread_id: str) -> str:
    from azure.ai.agents import models as m

    content = agents_client.messages.get_last_message_text_by_role(
        thread_id=thread_id, role=m.MessageRole.AGENT
    )
    if not content:
        return ""

    try:
        return content.text.value
    except Exception:
        return str(content)


def run_agent_turn(
    agents_client,
    *,
    agent_id: str,
    thread_id: str,
    user_text: str,
    toolset=None,
    instructions: Optional[str] = None,
) -> str:
    from azure.ai.agents import models as m

    def _response_text(resp) -> str:
        try:
            text = resp.text()
            return text if isinstance(text, str) else str(text)
        except TypeError:
            text = resp.text
            return text if isinstance(text, str) else str(text)
        except Exception:
            try:
                raw = resp.read()
                if isinstance(raw, (bytes, bytearray)):
                    return raw.decode("utf-8", errors="replace")
                return str(raw)
            except Exception:
                return "<unable to read response body>"

    def _raw_call(func, *args, **kwargs):
        return func(*args, cls=lambda resp, *_a, **_k: resp, **kwargs)

    try:
        agents_client.messages.create(
            thread_id=thread_id,
            role=m.MessageRole.USER,
            content=user_text,
        )
    except Exception as e:
        try:
            resp = _raw_call(
                agents_client.messages.create,
                thread_id,
                role=m.MessageRole.USER,
                content=user_text,
            )
            body = _response_text(resp)
            raise RuntimeError(
                "Failed to create thread message. "
                f"HTTP {getattr(resp, 'status_code', '???')} {getattr(resp, 'reason', '')}\n"
                f"Endpoint: {get_project_endpoint()}\n"
                f"Response (first 500 chars): {body[:500]}"
            ) from e
        except RuntimeError:
            raise
        except Exception:
            raise

    try:
        agents_client.runs.create_and_process(
            thread_id=thread_id,
            agent_id=agent_id,
            instructions=instructions,
            toolset=toolset,
        )
    except Exception as e:
        try:
            resp = _raw_call(
                agents_client.runs.create_and_process,
                thread_id,
                agent_id=agent_id,
                instructions=instructions,
                toolset=toolset,
            )
            body = _response_text(resp)
            raise RuntimeError(
                "Failed to create/process run. "
                f"HTTP {getattr(resp, 'status_code', '???')} {getattr(resp, 'reason', '')}\n"
                f"Endpoint: {get_project_endpoint()}\n"
                f"Response (first 500 chars): {body[:500]}"
            ) from e
        except RuntimeError:
            raise
        except Exception:
            raise

    return get_last_assistant_text(agents_client, thread_id=thread_id)

