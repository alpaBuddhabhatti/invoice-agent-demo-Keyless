"""
Step 4: Advanced Validation Tool
=================================
Demonstrates conditional business logic within tools.
Shows how to implement approval thresholds and multi-tier validation.

Key Concepts:
    - Business Rules: Encoding company policies in code
    - Conditional Logic: Different outcomes based on input values
    - Approval Workflows: Routing invoices based on amount thresholds
    - Risk Management: Flagging high-value transactions for review

What This Does:
    - Validates invoices against amount thresholds
    - Auto-approves low-value invoices
    - Flags high-value invoices for manual approval

Enhancement Suggestions:
    1. Implement multi-tier approval levels (manager, director, CFO)
    2. Add department-specific budget validation
    3. Integrate with approval workflow systems
    4. Add email/Slack notifications to approvers
    5. Implement time-based auto-approval for trusted vendors
    6. Add fraud detection scoring
    7. Cross-reference with purchase orders
    8. Implement seasonal or project-based budget rules
    9. Add vendor risk scoring
    10. Create audit trail for all validation decisions
"""

from azure.ai.agents.models import FunctionTool, ToolSet

from client import create_thread, ensure_agent, get_agents_client, run_agent_turn

# Define validation tool with business logic
def validate_invoice(amount: int, currency: str) -> str:
    """
    Validate invoice and determine approval status based on business rules.
    
    Args:
        amount: Invoice amount (numeric value)
        currency: Currency code (USD, EUR, etc.)
        
    Returns:
        Approval status: "APPROVED" or "REQUIRES_APPROVAL"
        
    Current Rules:
        - Amounts <= $10,000: Auto-approved
        - Amounts > $10,000: Requires manual approval
        
    Enhancement Ideas:
        - Add multi-tier thresholds ($10K, $50K, $100K, etc.)
        - Implement currency-specific thresholds
        - Add vendor-based rules (trusted vendors get higher limits)
        - Check against available budget
        - Add time-of-day or day-of-week rules
        - Implement ML-based fraud detection
        - Add industry-specific validation
        - Support custom approval chains by department
        - Add duplicate invoice checking
        - Implement velocity checks (too many invoices in short time)
    """
    # Simple threshold-based validation
    # Enhancement: Make threshold configurable via environment variables
    APPROVAL_THRESHOLD = 10000
    
    if amount > APPROVAL_THRESHOLD:
        # High-value invoice needs approval
        # Enhancement: Return approval level needed and assign to specific approver
        return "REQUIRES_APPROVAL"
    else:
        # Low-value invoice is auto-approved
        # Enhancement: Still log for audit purposes
        return "APPROVED"
    
    # Enhancement: Return structured data with reasoning
    # return {
    #     "status": "APPROVED",
    #     "reason": "Below approval threshold",
    #     "approver": None,
    #     "confidence": 0.95
    # }

def main():
    """
    Main function demonstrating validation tool with business rules.
    
    Enhancement Ideas:
        - Test with various amounts to demonstrate different outcomes
        - Add validation result persistence
        - Integrate with approval notification systems
        - Add validation metrics tracking
    """
    agents_client = get_agents_client()

    toolset = ToolSet()
    toolset.add(FunctionTool({validate_invoice}))
    # Required for local Python tool execution: allows the SDK to run tool calls and submit outputs.
    agents_client.enable_auto_function_calls(toolset)

    agent = ensure_agent(
        agents_client,
        name="InvoiceValidationAgent",
        instructions="Validate invoices according to company approval policies.",
        toolset=toolset,
    )

    thread_id = create_thread(agents_client)
    text = run_agent_turn(
        agents_client,
        agent_id=agent.id,
        thread_id=thread_id,
        user_text="Validate invoice with amount 1200 USD",
        toolset=toolset,
    )
    print(text)
    
    # Enhancement: Test with high-value invoice
    # result2 = await agent.run("Validate invoice with amount 50000 USD")
    # print(result2.text)
    
    # Enhancement: Batch validate multiple invoices
    # Enhancement: Generate validation report
    # Enhancement: Send results to approval system

# Entry point for the script
if __name__ == '__main__':
    main()
