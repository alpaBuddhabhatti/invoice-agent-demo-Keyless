
"""
Step 1: Basic Invoice Agent
============================
Demonstrates the simplest form of an AI agent that processes a single invoice.
This example shows the foundational pattern for creating and running an agent.

What This Does:
    - Creates an AI agent with basic instructions
    - Processes a single invoice string
    - Returns a summarized response

Enhancement Suggestions:
    1. Add error handling for API failures and network issues
    2. Implement input validation for invoice data
    3. Support batch processing of multiple invoices
    4. Add structured output formatting (JSON, CSV, PDF)
    5. Implement logging for audit trails
    6. Add performance metrics tracking (response time, token usage)
    7. Support different invoice formats (text, JSON, XML)
    8. Add confidence scoring for extracted data
    9. Implement user authentication and authorization
    10. Create a REST API endpoint for web integration
"""

from client import create_thread, ensure_agent, get_agents_client, run_agent_turn

def main():
    """Create and run the basic invoice agent using Foundry Agents."""

    agents_client = get_agents_client()
    agent = ensure_agent(
        agents_client,
        name="BasicInvoiceAgent",
        instructions="Summarize invoice data.",
    )

    thread_id = create_thread(agents_client)

    invoice = "Invoice INV-1001 from Contoso for 1200 USD"
    text = run_agent_turn(
        agents_client,
        agent_id=agent.id,
        thread_id=thread_id,
        user_text=invoice,
    )
    print(text)

# Entry point for the script
if __name__ == '__main__':
    main()
