from services.gemini_service import generate_content_with_retry
from prompts.chat_prompt import CHAT_SYSTEM_PROMPT


def send_chat_message(
    client,
    study_material,
    chat_history,
    user_message
):
    """
    Generate a response grounded in the student's
    study material.

    Returns:
        (answer, model_name)
    """

    conversation = ""

    for message in chat_history:

        role = message["role"]

        if role == "user":

            conversation += (
                f"\nStudent: {message['content']}\n"
            )

        elif role == "assistant":

            conversation += (
                f"\nAI StudyMate: {message['content']}\n"
            )

    prompt = f"""
{CHAT_SYSTEM_PROMPT}

STUDENT'S STUDY MATERIAL:
{study_material}

PREVIOUS CONVERSATION:
{conversation}

CURRENT STUDENT QUESTION:
{user_message}

Answer the current question using the study material
as the primary source.

Do not repeat the entire study material unless necessary.

If the answer is not available in the study material,
say so clearly and then provide useful general background
knowledge when appropriate.
"""

    return generate_content_with_retry(
        client,
        prompt
    )
