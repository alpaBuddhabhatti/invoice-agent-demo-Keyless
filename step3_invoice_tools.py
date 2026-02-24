"""
Step 3: Invoice Tools Agent (Multiple Tools)
=============================================
Demonstrates how to create an agent with multiple specialized tools.
This example shows tool chaining where one tool's output can feed into another.

Key Concepts:
    - Multiple Tools: Agents can use many different tools
    - Tool Chaining: Agent orchestrates multiple tool calls in sequence
    - Workflow Automation: Tools work together to complete complex tasks
    - Autonomous Decision Making: Agent decides which tools to use and when

What This Does:
    - Defines extraction and validation tools
    - Agent automatically chains tools together
    - Processes invoice from extraction through validation

Enhancement Suggestions:
    1. Add more tools (calculate_tax, check_duplicate, save_to_db)
    2. Implement approval workflow for high-value invoices
    3. Add email notification tools for stakeholders
    4. Create audit logging tools for compliance
    5. Add payment processing integration
    6. Implement budget checking against department allocations
    7. Add vendor verification tools (check against approved vendor list)
    8. Create reporting and analytics tools
    9. Add document attachment handling tools
    10. Implement multi-currency conversion tools
"""

from azure.ai.agents.models import FunctionTool, ToolSet

from client import create_thread, ensure_agent, get_agents_client, run_agent_turn

# Tool 1: Invoice Extraction
def extract_invoice(text: str) -> dict:
    """
    Extract key invoice fields from text input.
    
    Args:
        text: Raw invoice text
        
    Returns:
        Dictionary with vendor, amount, and currency
        
    Enhancement Ideas:
        - Parse real invoice data using NLP
        - Extract line items and detailed information
        - Add invoice date, due date, payment terms
        - Include vendor address and contact info
        - Support multiple invoice formats
    """
    # Hardcoded for demo - replace with actual extraction logic
    return {
        'vendor': 'Contoso', 
        'amount': 1200, 
        'currency': 'USD'
    }

# Tool 2: Invoice Validation
def validate_invoice(amount: int, currency: str) -> str:
    """
    Validate invoice based on business rules.
    
    Args:
        amount: Invoice amount
        currency: Currency code (USD, EUR, etc.)
        
    Returns:
        Approval status string
        
    Enhancement Ideas:
        - Implement multi-tier approval rules
        - Check against budget constraints
        - Verify currency is supported
        - Cross-check with purchase orders
        - Validate vendor is approved
        - Check for duplicate invoices
        - Apply department-specific rules
        - Add fraud detection checks
    """
    # Simple approval logic - always approves for demo
    # Enhancement: Add real validation rules
    return 'APPROVED'

def main():
    """
    Main function demonstrating multi-tool agent workflow.
    
    Enhancement Ideas:
        - Add error handling for tool failures
        - Implement conditional tool execution
        - Log tool call sequences for debugging
        - Support parallel tool execution where possible
        - Add tool execution timeout handling
    """
    agents_client = get_agents_client()

    toolset = ToolSet()
    toolset.add(FunctionTool({extract_invoice, validate_invoice}))
    # Required for local Python tool execution: allows the SDK to run tool calls and submit outputs.
    agents_client.enable_auto_function_calls(toolset)

    invoice_text = """INVOICE\nVendor: Contoso\nInvoice Number: INV-1001\nDate: 2026-02-23\nTotal Due: 1200 USD\n"""

    agent = ensure_agent(
        agents_client,
        # Use a distinct name so we don't accidentally reuse an older agent with different instructions.
        name="InvoiceWorkflowAgent_Step3_MultiTools",
        instructions=(
            "You are an invoice processing workflow agent.\n"
            "The user will provide invoice TEXT in the message. Do NOT ask for an invoice document or image.\n"
            "Workflow (always follow):\n"
            "1) Call extract_invoice(invoice_text) using the provided invoice text.\n"
            "2) Call validate_invoice(amount, currency) using the extracted fields.\n"
            "Then respond with a short summary containing vendor, amount, currency, and the validation result."
        ),
        toolset=toolset,
    )

    thread_id = create_thread(agents_client)
    text = run_agent_turn(
        agents_client,
        agent_id=agent.id,
        thread_id=thread_id,
        user_text=(
            "Process this invoice text end-to-end (extract then validate):\n\n"
            f"{invoice_text}"
        ),
        toolset=toolset,
    )
    print(text)
    
    # Enhancement: Access intermediate tool results
    # Enhancement: Implement custom workflow logic

# Entry point for the script
if __name__ == '__main__':
    main()
