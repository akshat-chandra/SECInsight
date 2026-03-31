import os
import anthropic
from dotenv import load_dotenv
from src.vector_store import search

load_dotenv()

CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a financial analyst assistant. Answer questions using ONLY the SEC 10-K filing excerpts provided in each message.

If the answer is not in the excerpts, say "I couldn't find that information in the filing excerpts provided."

Be concise and cite specific details from the filing when possible."""


def build_context(company: str, question: str) -> tuple[list[str], str]:
    """Retrieve relevant chunks and format them as context."""
    chunks = search(company, question, n_results=8)
    context = "\n\n---\n\n".join(chunks)
    return chunks, context


def stream_answer(company: str, question: str, history: list[dict]):
    """
    Streaming RAG pipeline with conversation history.
    Yields text chunks as Claude generates them.
    history: list of {"role": "user"/"assistant", "content": str}
    """
    chunks, context = build_context(company, question)

    # Inject the retrieved context into the current user message
    user_message = f"""FILING EXCERPTS from {company}'s 10-K:
{context}

QUESTION: {question}"""

    messages = history + [{"role": "user", "content": user_message}]

    with CLIENT.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text

    return chunks
