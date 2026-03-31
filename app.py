import streamlit as st
from urllib.parse import quote
from src.sec_fetcher import get_company_text, get_filing_url, COMPANIES
from src.chunker import chunk_text
from src.vector_store import index_chunks, is_indexed, search
from src.query import build_context, stream_answer

st.set_page_config(page_title="SECInsight", layout="wide")

st.title("SECInsight")
st.caption("Ask questions about any company's SEC 10-K filing in plain English.")

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []          # chat history
if "last_chunks" not in st.session_state:
    st.session_state.last_chunks = []       # chunks used in last answer
if "compare_mode" not in st.session_state:
    st.session_state.compare_mode = False


# ── Company selector + compare mode ──────────────────────────────────────────
col_sel, col_toggle = st.columns([4, 1])

with col_toggle:
    st.session_state.compare_mode = st.toggle("Compare companies", value=st.session_state.compare_mode)

with col_sel:
    if st.session_state.compare_mode:
        companies = st.multiselect(
            "Select companies to compare",
            list(COMPANIES.keys()),
            default=list(COMPANIES.keys())[:2],
        )
    else:
        companies = [st.selectbox("Select a company", list(COMPANIES.keys()))]


# ── Index status + fetch ──────────────────────────────────────────────────────
for company in companies:
    if not is_indexed(company):
        st.info(f"{company}'s 10-K has not been indexed yet.")
        if st.button(f"Fetch & Index {company}'s 10-K", key=f"fetch_{company}"):
            with st.spinner(f"Fetching {company}'s latest 10-K from SEC EDGAR..."):
                text = get_company_text(company)
            with st.spinner("Chunking and embedding — takes ~30 seconds the first time..."):
                chunks = chunk_text(text)
                index_chunks(company, chunks)
            st.success(f"{company} indexed — {len(chunks)} chunks stored.")
            st.rerun()
    else:
        st.success(f"{company}'s 10-K is indexed and ready.")

all_indexed = all(is_indexed(c) for c in companies)

st.divider()


# ── Chat history display ──────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("chunks"):
            filing_url = msg.get("filing_url")
            if filing_url:
                company_name = msg.get("company", "")
                st.caption(f"📄 Source: [{company_name} 10-K Filing (SEC EDGAR)]({filing_url})")
            with st.expander("View source excerpts used"):
                for i, chunk in enumerate(msg["chunks"], 1):
                    snippet = " ".join(chunk.split()[:8])
                    fragment = quote(snippet)
                    deep_link = f"{filing_url}#:~:text={fragment}" if filing_url else None
                    col_a, col_b = st.columns([6, 1])
                    with col_a:
                        st.markdown(f"**Excerpt {i}:**")
                        st.caption(chunk[:500] + "..." if len(chunk) > 500 else chunk)
                    with col_b:
                        if deep_link:
                            st.markdown(f"[View in filing ↗]({deep_link})")
                    st.divider()


# ── Example question buttons ──────────────────────────────────────────────────
if all_indexed:
    st.markdown("**Try asking:**")
    example_questions = [
        "What are the main risks facing this company?",
        "What did they say about artificial intelligence?",
        "How did revenue perform this year?",
        "What are their biggest sources of revenue?",
        "What did management say about competition?",
    ]
    clicked_example = None
    row1 = st.columns(3)
    row2 = st.columns(2)
    for col, eq in zip(row1 + row2, example_questions):
        with col:
            if st.button(eq, use_container_width=True):
                clicked_example = eq

# ── Chat input ────────────────────────────────────────────────────────────────
question = st.chat_input(
    "Ask a question about the filing...",
    disabled=not all_indexed,
)

# Example button click overrides chat input
if all_indexed and clicked_example:
    question = clicked_example

if question:
    # Show user message
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    # Build conversation history (exclude chunks metadata, just role+content)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]  # exclude current message
    ]

    if st.session_state.compare_mode and len(companies) > 1:
        # ── COMPARISON MODE: answer per company side by side ──────────────
        cols = st.columns(len(companies))
        for col, company in zip(cols, companies):
            with col:
                st.markdown(f"### {company}")
                with st.chat_message("assistant"):
                    chunks, _ = build_context(company, question)
                    filing_url = get_filing_url(company)

                    full_response = st.write_stream(
                        stream_answer(company, question, history)
                    )

                    if filing_url:
                        st.caption(f"📄 [{company} 10-K (SEC EDGAR)]({filing_url})")

                    with st.expander("Source excerpts"):
                        for i, chunk in enumerate(chunks, 1):
                            snippet = " ".join(chunk.split()[:8])
                            fragment = quote(snippet)
                            deep_link = f"{filing_url}#:~:text={fragment}" if filing_url else None
                            ca, cb = st.columns([6, 1])
                            with ca:
                                st.markdown(f"**Excerpt {i}:**")
                                st.caption(chunk[:400] + "..." if len(chunk) > 400 else chunk)
                            with cb:
                                if deep_link:
                                    st.markdown(f"[↗]({deep_link})")
                            st.divider()

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"**{company}:** {full_response}",
                        "chunks": chunks,
                        "filing_url": filing_url,
                        "company": company,
                    })

    else:
        # ── SINGLE COMPANY MODE ───────────────────────────────────────────
        company = companies[0]
        filing_url = get_filing_url(company)
        chunks, _ = build_context(company, question)

        with st.chat_message("assistant"):
            full_response = st.write_stream(
                stream_answer(company, question, history)
            )

            if filing_url:
                st.caption(f"📄 Source: [{company} 10-K Filing (SEC EDGAR)]({filing_url})")

            with st.expander("View source excerpts used"):
                for i, chunk in enumerate(chunks, 1):
                    snippet = " ".join(chunk.split()[:8])
                    fragment = quote(snippet)
                    deep_link = f"{filing_url}#:~:text={fragment}" if filing_url else None
                    col_a, col_b = st.columns([6, 1])
                    with col_a:
                        st.markdown(f"**Excerpt {i}:**")
                        st.caption(chunk[:500] + "..." if len(chunk) > 500 else chunk)
                    with col_b:
                        if deep_link:
                            st.markdown(f"[View in filing ↗]({deep_link})")
                    st.divider()

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "chunks": chunks,
            "filing_url": filing_url,
            "company": company,
        })

st.divider()
if st.button("Clear chat history"):
    st.session_state.messages = []
    st.rerun()

st.caption("SECInsight | Built with Anthropic Claude, ChromaDB, and SEC EDGAR | github.com/akshat-chandra")
