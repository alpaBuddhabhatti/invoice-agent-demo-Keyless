"""
Step 2: Thread Memory Agent
============================
Demonstrates how to use thread-based memory to maintain conversation context.
This allows the agent to remember previous interactions and answer follow-up questions.

Key Concepts:
    - Thread: A persistent conversation context that stores message history
    - Memory: The agent can reference previous messages in the same thread
    - Multi-turn Conversation: Enables natural back-and-forth interactions

What This Does:
    - Creates an agent with conversation memory
    - Processes an initial invoice message
    - Answers follow-up questions using context from earlier messages

Enhancement Suggestions:
    1. Persist threads to database for long-term storage
    2. Add thread management (list, delete, archive threads)
    3. Implement thread sharing between users for collaboration
    4. Add conversation summarization for long threads
    5. Support multiple concurrent threads per user
    6. Implement context window management (truncate old messages)
    7. Add thread export functionality (PDF, JSON, HTML)
    8. Implement semantic search across thread history
    9. Add conversation analytics (sentiment, topics, entities)
    10. Support branching conversations (what-if scenarios)
"""

from client import create_thread, ensure_agent, get_agents_client, run_agent_turn

def main():
    """Demonstrate thread-based memory using Foundry threads + runs."""

    agents_client = get_agents_client()
    agent = ensure_agent(
        agents_client,
        name="InvoiceQnAAgent",
        instructions="Answer invoice questions.",
    )

    thread_id = create_thread(agents_client)

    run_agent_turn(
        agents_client,
        agent_id=agent.id,
        thread_id=thread_id,
        user_text="Invoice from Contoso for 1200 USD",
    )

    text = run_agent_turn(
        agents_client,
        agent_id=agent.id,
        thread_id=thread_id,
        user_text="What is the total amount?",
    )
    print(text)

# Entry point for the script
if __name__ == '__main__':
    main()
