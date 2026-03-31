import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

# ChromaDB's built-in embedding function — uses ONNX, no PyTorch required
EMBED_FN = DefaultEmbeddingFunction()

# ChromaDB stored locally in the data/ folder
CLIENT = chromadb.PersistentClient(path="data/chroma")


def get_collection(company: str):
    """Get or create a ChromaDB collection for a company."""
    name = company.lower().replace(" ", "-").replace("(", "").replace(")", "")
    return CLIENT.get_or_create_collection(name, embedding_function=EMBED_FN)


def index_chunks(company: str, chunks: list[dict]) -> None:
    """Embed all chunks and store them in ChromaDB."""
    collection = get_collection(company)

    texts = [c["text"] for c in chunks]
    ids = [f"{company}-chunk-{c['chunk_index']}" for c in chunks]
    metadatas = [{"chunk_index": c["chunk_index"], "company": company} for c in chunks]

    print(f"Embedding {len(chunks)} chunks for {company}...")
    collection.upsert(documents=texts, ids=ids, metadatas=metadatas)
    print(f"Stored {len(chunks)} chunks in ChromaDB.")


def is_indexed(company: str) -> bool:
    """Check if a company has already been indexed."""
    try:
        collection = get_collection(company)
        return collection.count() > 0
    except Exception:
        return False


def search(company: str, query: str, n_results: int = 5) -> list[str]:
    """Find the top N chunks most relevant to the query."""
    collection = get_collection(company)
    results = collection.query(query_texts=[query], n_results=n_results)
    return results["documents"][0]
