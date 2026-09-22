from app.core.database import SessionLocal, init_db
from app.agents.memory.agent import ConversationMemoryAgent


def main():
    # Create tables.
    init_db()

    db = SessionLocal()

    try:
        memory = ConversationMemoryAgent(
            history_limit=10
        )

        conversation_id = "test-conversation-001"

        # Store first turn.
        memory.store_turn(
            db=db,
            conversation_id=conversation_id,
            user_query="What is the leave policy?",
            ai_response="Employees receive 12 days of paid leave per year.",
        )

        # Store second turn.
        memory.store_turn(
            db=db,
            conversation_id=conversation_id,
            user_query="What about probation employees?",
            ai_response="The policy for probation employees is described in the HR policy document.",
        )

        # Retrieve history.
        history = memory.get_history(
            db=db,
            conversation_id=conversation_id,
        )

        print("\nHISTORY:")
        for message in history:
            print(
                f"{message.role}: {message.content}"
            )

        # Retrieve LLM-friendly context.
        context = memory.get_context(
            db=db,
            conversation_id=conversation_id,
        )

        print("\nCONTEXT:")
        for message in context:
            print(message)

        # Retrieve text context.
        context_text = memory.get_context_text(
            db=db,
            conversation_id=conversation_id,
        )

        print("\nTEXT CONTEXT:")
        print(context_text)

        # Check memory.
        print("\nHAS MEMORY:")
        print(
            memory.has_memory(
                db=db,
                conversation_id=conversation_id,
            )
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()