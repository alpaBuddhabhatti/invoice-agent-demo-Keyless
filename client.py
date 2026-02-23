"""
Azure OpenAI Chat Client Configuration
=======================================
This module provides a centralized way to configure and create Azure OpenAI chat clients
for the invoice processing agent application.

Configuration:
    - endpoint: Azure OpenAI service endpoint URL
    - deployment_name: Name of the deployed model (e.g., gpt-4, gpt-4.1-mini)
    - credential: Microsoft Entra ID credential (keyless authentication)

Enhancement Suggestions:
    1. Use managed identity / Entra ID (no secrets in config)
    2. Add retry logic with exponential backoff for API calls
    3. Implement connection pooling for multiple concurrent requests
    4. Add logging for debugging and monitoring
    5. Support multiple deployment configurations (dev, staging, prod)
    6. Add API version configuration for better version control
    7. Implement rate limiting to avoid quota exhaustion
    8. Add health check functionality to verify endpoint availability
"""

import os

from dotenv import load_dotenv

from agent_framework.azure import AzureOpenAIChatClient

# Load environment variables from .env file
load_dotenv()

def get_chat_client():
    """
    Create and configure an Azure OpenAI chat client.

    Authentication:
        - Keyless authentication via Microsoft Entra ID (DefaultAzureCredential).
    
    Returns:
        AzureOpenAIChatClient: Configured chat client instance
        
    Raises:
        RuntimeError: If required configuration is missing
        
    Enhancement Ideas:
        - Add caching to reuse client instances
        - Support alternative authentication methods (Managed Identity, Service Principal)
        - Add client configuration validation
        - Implement fallback to different deployments if primary fails
    """
    # Azure OpenAI endpoint (without /openai/v1/ suffix for AzureOpenAIChatClient)
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

    # Deployment name - the model deployed in Azure OpenAI.
    # Prefer AZURE_OPENAI_DEPLOYMENT, but accept AZURE_OPENAI_DEPLOYMENT_NAME
    # for compatibility with older docs/config.
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv(
        "AZURE_OPENAI_DEPLOYMENT_NAME"
    )

    # Optional API version override.
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    # Optional transport settings (passed through to the underlying OpenAI client).
    # These help avoid "hangs" on network/TLS issues and make behavior predictable.
    timeout_seconds = os.getenv("AZURE_OPENAI_TIMEOUT_SECONDS")
    max_retries = os.getenv("AZURE_OPENAI_MAX_RETRIES")

    # Optional token scope/endpoint for Entra ID. Agent Framework defaults this to
    # https://cognitiveservices.azure.com/.default if not provided.
    token_endpoint = os.getenv("AZURE_OPENAI_TOKEN_ENDPOINT")

    # Validate required configuration
    missing = []
    if not endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not deployment_name:
        missing.append("AZURE_OPENAI_DEPLOYMENT (preferred) or AZURE_OPENAI_DEPLOYMENT_NAME")
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    # Create and return the Azure OpenAI chat client
    # Note: AzureOpenAIChatClient automatically handles API versioning
    client_kwargs = {
        "endpoint": endpoint,
        "deployment_name": deployment_name,
    }
    if api_version:
        client_kwargs["api_version"] = api_version

    if timeout_seconds:
        try:
            client_kwargs["timeout"] = float(timeout_seconds)
        except ValueError:
            raise RuntimeError(
                "AZURE_OPENAI_TIMEOUT_SECONDS must be a number (seconds), e.g. 30 or 60."
            )
    if max_retries:
        try:
            client_kwargs["max_retries"] = int(max_retries)
        except ValueError:
            raise RuntimeError(
                "AZURE_OPENAI_MAX_RETRIES must be an integer, e.g. 0, 2, 5."
            )

    # Keyless authentication using Microsoft Entra ID.
    try:
        from azure.identity import DefaultAzureCredential
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Keyless auth requires azure-identity. Install it with `pip install azure-identity` "
            "or add it to requirements.txt."
        ) from e

    # DefaultAzureCredential supports:
    # - Local dev: Azure CLI / VS Code sign-in
    # - Azure: Managed Identity (system- or user-assigned)
    credential = DefaultAzureCredential()
    client_kwargs["credential"] = credential
    if token_endpoint:
        client_kwargs["token_endpoint"] = token_endpoint

    return AzureOpenAIChatClient(**client_kwargs)
