import os
import re
import threading
from uuid import uuid4
from dotenv import load_dotenv
from pathlib import Path
from langchain_classic.chains import RetrievalQAWithSourcesChain
from langchain_community.document_loaders import UnstructuredURLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    import torch
    torch.set_num_threads(1)
except Exception:
    pass

load_dotenv()

# Constants
CHUNK_SIZE = 1000
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTORSTORE_DIR = Path(__file__).parent / "resources/vectorstore"
COLLECTION_NAME = "real_estate"

llm = None
vector_store = None
lock = threading.RLock()


def initialize_components():
    global llm, vector_store

    with lock:
        if llm is None:
            model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
            llm = ChatGroq(model=model_name, temperature=0.7, max_tokens=500)

        if vector_store is None:
            ef = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs={"trust_remote_code": True, "device": "cpu"}
            )

            vector_store = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=ef,
                persist_directory=str(VECTORSTORE_DIR)
            )


def process_urls(urls):
    """
    This function scrapes data from URLs and stores it in a vector DB
    :param urls: input urls
    :return: generator of status messages
    """
    yield "Initializing components..."
    initialize_components()

    yield "Resetting vector store..."
    vector_store.reset_collection()

    yield "Loading data from URLs (this may take a few moments)..."
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    loader = UnstructuredURLLoader(urls=urls, headers=headers)
    data = loader.load()

    if not data:
        yield "Warning: Could not fetch content from the provided URLs."
        return

    yield f"Splitting text from {len(data)} page(s) into chunks..."
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", " "],
        chunk_size=CHUNK_SIZE
    )
    docs = text_splitter.split_documents(data)

    if not docs:
        yield "Warning: No text chunks found to index."
        return

    yield f"Embedding and adding {len(docs)} chunks to vector database..."
    uuids = [str(uuid4()) for _ in range(len(docs))]
    vector_store.add_documents(docs, ids=uuids)

    yield f"Successfully processed and added {len(docs)} chunks to vector database!"

# Patch ChatGroq._combine_llm_outputs at runtime for robustness against NoneType token details
def _safe_combine_llm_outputs(self, llm_outputs):
    overall_token_usage = {}
    system_fingerprint = None
    for output in llm_outputs:
        if output is None:
            continue
        token_usage = output.get("token_usage")
        if token_usage is not None:
            for k, v in token_usage.items():
                if k in overall_token_usage:
                    if v is not None:
                        if isinstance(v, dict):
                            if not isinstance(overall_token_usage[k], dict):
                                overall_token_usage[k] = {}
                            for nested_k, nested_v in v.items():
                                if (
                                    nested_k in overall_token_usage[k]
                                    and nested_v is not None
                                    and overall_token_usage[k][nested_k] is not None
                                ):
                                    overall_token_usage[k][nested_k] += nested_v
                                elif nested_v is not None or nested_k not in overall_token_usage[k]:
                                    overall_token_usage[k][nested_k] = nested_v
                        else:
                            if overall_token_usage[k] is None:
                                overall_token_usage[k] = v
                            else:
                                overall_token_usage[k] += v
                else:
                    overall_token_usage[k] = v
        if system_fingerprint is None:
            system_fingerprint = output.get("system_fingerprint")
    combined = {"token_usage": overall_token_usage, "model_name": self.model_name}
    if system_fingerprint:
        combined["system_fingerprint"] = system_fingerprint
    if getattr(self, "service_tier", None):
        combined["service_tier"] = self.service_tier
    return combined

ChatGroq._combine_llm_outputs = _safe_combine_llm_outputs


def generate_answer(query):
    if vector_store is None or llm is None:
        initialize_components()

    if vector_store._collection.count() == 0:
        raise RuntimeError("Vector database is empty. You must process URLs first.")

    # 1. Retrieve top relevant document chunks
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})
    docs = retriever.invoke(query)

    if not docs:
        return "No relevant information found in the processed articles.", ""

    # 2. Extract unique verified source URLs from document metadata
    sources_list = []
    seen = set()
    for doc in docs:
        if doc.metadata and "source" in doc.metadata:
            src = str(doc.metadata["source"]).strip()
            if src and src not in seen:
                seen.add(src)
                sources_list.append(src)

    # 3. Compile context excerpts
    context_chunks = []
    for i, doc in enumerate(docs, 1):
        content = doc.page_content.strip()
        context_chunks.append(f"[Excerpt {i}]\n{content}")
    context_str = "\n\n---\n\n".join(context_chunks)

    # 4. Professional analyst prompt
    system_prompt = (
        "You are an expert real estate research analyst. "
        "Provide a clear, professional, and well-structured answer based strictly on the provided article excerpts."
    )

    user_prompt = f"""Article Excerpts:
{context_str}

User Question:
{query}

Instructions:
1. Provide a direct, professional, and well-explained answer to the question.
2. Structure the response clearly: start with an executive summary sentence, followed by structured bullet points for key details, rates, loan conditions, or dates where relevant.
3. Bold important numbers, rates, and terms for readability.
4. Professional tone: Write in an objective, authoritative business style.
5. Strictly ground your answer in the provided excerpts. If the information is not contained in the text, state: 'The provided articles do not contain sufficient information to answer this question.'
6. CRITICAL RULE: Do NOT include any 'SOURCES:', 'REFERENCES:', or URL citations in your answer body. Sources are displayed automatically in a dedicated section below.

Answer:"""

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])
    raw_answer = str(response.content or "").strip()

    # Clean any residual prefixes/meta-tags
    cleaned_answer = re.sub(r'^(FINAL ANSWER:\s*)+', '', raw_answer, flags=re.IGNORECASE).strip()

    # Strictly separate any sources block if generated by the LLM
    sources_pattern = r'(?i)\n+\s*(?:\*{0,2}SOURCES?:?\*{0,2}|REFERENCES?:?)\s*'
    if re.search(sources_pattern, cleaned_answer):
        parts = re.split(sources_pattern, cleaned_answer, maxsplit=1)
        cleaned_answer = parts[0].strip()
        if len(parts) > 1 and parts[1].strip():
            extra_urls = re.findall(r'https?://[^\s\]\)\}\>\"\'】]+', parts[1])
            for u in extra_urls:
                if u not in sources_list:
                    sources_list.append(u)

    sources_str = "\n".join(sources_list)
    return cleaned_answer, sources_str


if __name__ == "__main__":
    urls = [
        "https://www.cnbc.com/2024/12/21/how-the-federal-reserves-rate-policy-affects-mortgages.html",
        "https://www.cnbc.com/2024/12/20/why-mortgage-rates-jumped-despite-fed-interest-rate-cut.html"
    ]

    process_urls(urls)
    answer, sources = generate_answer("Tell me what was the 30 year fixed mortagate rate along with the date?")
    print(f"Answer: {answer}")
    print(f"Sources: {sources}")