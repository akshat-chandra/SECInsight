def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[dict]:
    """
    Split text into overlapping chunks.

    chunk_size: target number of words per chunk
    overlap:    number of words to repeat between consecutive chunks
                so context isn't lost at boundaries
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append({
            "text": " ".join(chunk_words),
            "chunk_index": len(chunks),
            "word_start": start,
            "word_end": end,
        })
        if end == len(words):
            break
        start += chunk_size - overlap  # step forward but keep overlap words

    return chunks
