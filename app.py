from __future__ import annotations

import base64
import hashlib
import html
from datetime import datetime
from pathlib import Path
import uuid
from typing import Any, Callable

import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader

from src.core.config import get_config
from src.core.constants import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_TTS_SPEAKER,
    LANGUAGES,
    TTS_LANGUAGE_CODES,
)
from src.services.document_store import DocumentStore
from src.services.ingestion_service import IngestionService
from src.services.sarvam_service import SarvamService


LOCAL_DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"
LOCAL_DOCUMENT_CATEGORIES = ["tax", "agriculture", "startups", "pensions", "user_uploads"]
LOCAL_DOCUMENT_CATEGORY_LABELS = {
    "tax": "Tax",
    "agriculture": "Agriculture",
    "startups": "Startups",
    "pensions": "Pensions",
    "user_uploads": "User Uploads",
}

LOCAL_DOCUMENTS_DIR.mkdir(exist_ok=True)
for category in LOCAL_DOCUMENT_CATEGORIES:
    (LOCAL_DOCUMENTS_DIR / category).mkdir(exist_ok=True)


st.set_page_config(
    page_title="Policy Intelligence Studio",
    page_icon="🏛️",
    layout="wide",
)


st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

        :root {
            --bg-0: #04111f;
            --bg-1: #07182c;
            --bg-2: #0a2740;
            --panel: rgba(10, 20, 35, 0.72);
            --panel-strong: rgba(7, 16, 29, 0.88);
            --panel-soft: rgba(255, 255, 255, 0.06);
            --border: rgba(255, 255, 255, 0.12);
            --border-strong: rgba(0, 212, 255, 0.28);
            --text-main: #f5f8ff;
            --text-subtle: rgba(245, 248, 255, 0.74);
            --sarvam-cyan: #00d4ff;
            --sarvam-blue: #1b7cff;
            --hcl-teal: #00b3a6;
            --hcl-gold: #ffb547;
            --accent-coral: #ff6b5a;
            --shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
        }

        .stApp {
            background:
                radial-gradient(circle at 8% 12%, rgba(0, 212, 255, 0.18), transparent 24%),
                radial-gradient(circle at 92% 8%, rgba(255, 181, 71, 0.16), transparent 22%),
                radial-gradient(circle at 88% 88%, rgba(0, 179, 166, 0.12), transparent 20%),
                linear-gradient(135deg, var(--bg-0) 0%, var(--bg-1) 42%, var(--bg-2) 100%);
            color: var(--text-main);
            font-family: 'Source Sans 3', sans-serif;
        }

        [data-testid="stAppViewContainer"] {
            background: transparent;
        }

        [data-testid="stHeader"] {
            background: rgba(4, 17, 31, 0.54);
            backdrop-filter: blur(16px);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(4, 17, 31, 0.92), rgba(7, 24, 44, 0.88));
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Space Grotesk', sans-serif;
            color: var(--text-main);
            letter-spacing: -0.02em;
        }

        .theme-hero {
            position: relative;
            overflow: hidden;
            margin-bottom: 1.2rem;
            padding: 1.15rem 1.35rem 1.25rem;
            border-radius: 22px;
            border: 1px solid var(--border);
            background:
                linear-gradient(135deg, rgba(0, 212, 255, 0.16), rgba(27, 124, 255, 0.14) 34%, rgba(0, 179, 166, 0.10) 68%, rgba(255, 181, 71, 0.10));
            box-shadow: var(--shadow);
        }

        .theme-hero::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                radial-gradient(circle at 15% 30%, rgba(255, 255, 255, 0.20), transparent 18%),
                radial-gradient(circle at 85% 18%, rgba(255, 255, 255, 0.12), transparent 16%),
                linear-gradient(90deg, rgba(255, 255, 255, 0.04), transparent 40%, rgba(255, 255, 255, 0.02));
            pointer-events: none;
        }

        .theme-kicker {
            position: relative;
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.28rem 0.75rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: var(--text-subtle);
            font-size: 0.78rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .theme-kicker::before {
            content: "";
            width: 0.45rem;
            height: 0.45rem;
            border-radius: 999px;
            background: linear-gradient(135deg, var(--sarvam-cyan), var(--hcl-teal));
            box-shadow: 0 0 14px rgba(0, 212, 255, 0.65);
        }

        .theme-title {
            position: relative;
            margin: 0.6rem 0 0.25rem;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.15rem;
            line-height: 1.02;
            color: var(--text-main);
        }

        .theme-subtitle {
            position: relative;
            margin: 0;
            max-width: 68rem;
            color: var(--text-subtle);
            font-size: 1rem;
        }

        .document-card,
        div[data-testid="stVerticalBlockBorderWrapper"],
        section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(180deg, rgba(14, 26, 45, 0.90), rgba(8, 17, 31, 0.82));
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            border-radius: 18px;
            backdrop-filter: blur(14px);
        }

        .document-card {
            padding: 12px 14px;
            margin-bottom: 10px;
        }

        .document-card b,
        .document-card small,
        .document-card span {
            color: var(--text-main);
        }

        .document-card,
        .document-card * {
            color: var(--text-main) !important;
        }

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span {
            color: var(--text-main) !important;
        }

        .status-ready,
        .status-indexing {
            float: right;
            padding: 0.18rem 0.58rem;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.03em;
        }

        .status-ready {
            color: #7af0d1;
            background: rgba(0, 179, 166, 0.16);
            border: 1px solid rgba(0, 179, 166, 0.30);
        }

        .status-indexing {
            color: #ffd08b;
            background: rgba(255, 181, 71, 0.16);
            border: 1px solid rgba(255, 181, 71, 0.30);
        }

        .stMarkdown,
        .stCaption,
        .stSelectbox,
        .stFileUploader,
        .stRadio,
        .stCheckbox,
        .stTextInput,
        .stTextArea {
            color: var(--text-main);
        }

        p,
        li,
        label,
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] span,
        .stCaption p,
        .stMarkdown p,
        .stRadio label,
        .stCheckbox label,
        .stFileUploader label,
        [data-testid="stFileUploaderDropzoneInstructions"],
        [data-testid="stFileUploaderDropzoneInstructions"] span,
        [data-testid="stFileUploaderDropzone"] small {
            color: var(--text-main) !important;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] span {
            color: var(--text-main) !important;
        }

        .stRadio [role="radiogroup"] label span {
            color: var(--text-main) !important;
        }

        .stSelectbox [data-baseweb="select"],
        .stTextInput input,
        .stTextArea textarea {
            color: #091423;
            font-weight: 500;
        }

        [data-testid="stFileUploaderDropzone"] {
            background: linear-gradient(180deg, rgba(14, 26, 45, 0.88), rgba(8, 17, 31, 0.8));
            border: 1px dashed rgba(0, 212, 255, 0.35);
        }

        [data-testid="stFileUploaderDropzone"] *,
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] span,
        [data-testid="stFileUploaderDropzoneInstructions"],
        [data-testid="stFileUploaderDropzoneInstructions"] * {
            color: var(--text-main) !important;
            opacity: 1 !important;
        }

        [data-testid="stFileUploaderDropzone"] button,
        [data-testid="stFileUploaderDropzone"] button:disabled {
            background: rgba(255, 255, 255, 0.14) !important;
            color: var(--text-main) !important;
            border: 1px solid rgba(255, 255, 255, 0.32) !important;
            opacity: 1 !important;
        }

        [data-testid="stFileUploaderDropzone"] button p,
        [data-testid="stFileUploaderDropzone"] button span,
        [data-testid="stFileUploaderDropzone"] button svg {
            color: var(--text-main) !important;
            fill: var(--text-main) !important;
            opacity: 1 !important;
        }

        [data-testid="stChatMessage"] {
            background: transparent;
        }

        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
            color: var(--text-main);
        }

        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton > button {
            background: linear-gradient(135deg, var(--sarvam-cyan), var(--hcl-teal) 58%, var(--hcl-gold));
            color: #05111d;
            border: none;
            border-radius: 999px;
            font-weight: 700;
            box-shadow: 0 14px 32px rgba(0, 212, 255, 0.18);
            transition: transform 120ms ease, box-shadow 120ms ease, filter 120ms ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        .stFormSubmitButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 18px 38px rgba(255, 181, 71, 0.18);
            filter: saturate(1.05);
        }

        .stButton > button:focus-visible,
        .stDownloadButton > button:focus-visible,
        .stFormSubmitButton > button:focus-visible {
            outline: 2px solid rgba(0, 212, 255, 0.72);
            outline-offset: 2px;
        }

        .stButton > button:disabled,
        .stDownloadButton > button:disabled,
        .stFormSubmitButton > button:disabled {
            background: rgba(212, 218, 228, 0.92);
            color: #5a6575;
            box-shadow: none;
            opacity: 1;
            border: 1px solid rgba(90, 101, 117, 0.28);
        }

        [data-testid="stTabs"] button {
            color: var(--text-subtle);
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--text-main);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state() -> None:
    st.session_state.setdefault("api_key", get_config().sarvam_api_key)
    st.session_state.setdefault(
        "messages",
        [
            {
                "role": "assistant",
                "content": "Hello! I am your AI Policy Assistant. Ask me anything about the uploaded documents.",
            }
        ],
    )
    st.session_state.setdefault("last_audio_digest", None)
    st.session_state.setdefault("last_voice_prompt", None)
    st.session_state.setdefault("prompt_draft", "")
    st.session_state.setdefault("submitted_prompt", None)


@st.cache_resource(show_spinner=False)
def get_document_store() -> DocumentStore:
    return DocumentStore(get_config())


def get_sarvam_service() -> SarvamService:
    return SarvamService(api_key=st.session_state.get("api_key", "").strip())


def get_ingestion_service() -> IngestionService:
    return IngestionService(config=get_config(), store=get_document_store())


def build_tts_language_options() -> list[str]:
    options = ["Same as response (if supported)", "English"]
    for label, code in LANGUAGES.items():
        if code in TTS_LANGUAGE_CODES and label != "English":
            options.append(label)
    return options


def ensure_local_document_tree() -> None:
    LOCAL_DOCUMENTS_DIR.mkdir(exist_ok=True)
    for category in LOCAL_DOCUMENT_CATEGORIES:
        (LOCAL_DOCUMENTS_DIR / category).mkdir(exist_ok=True)


def fetch_local_documents() -> dict[str, list[dict[str, Any]]]:
    ensure_local_document_tree()
    documents: dict[str, list[dict[str, Any]]] = {category: [] for category in LOCAL_DOCUMENT_CATEGORIES}
    documents["uncategorized"] = []

    for category in LOCAL_DOCUMENT_CATEGORIES:
        category_dir = LOCAL_DOCUMENTS_DIR / category
        for file_path in sorted(
            (path for path in category_dir.iterdir() if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        ):
            file_stat = file_path.stat()
            uploaded_at = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            documents[category].append(
                {
                    "id": f"{category}/{file_path.name}",
                    "path": str(file_path),
                    "category": category,
                    "name": file_path.name,
                    "status": "Ready",
                    "uploaded_at": uploaded_at,
                    "size": f"{file_stat.st_size / 1024:.1f} KB",
                }
            )

    for file_path in sorted(
        (path for path in LOCAL_DOCUMENTS_DIR.iterdir() if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        file_stat = file_path.stat()
        uploaded_at = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        documents["uncategorized"].append(
            {
                "id": file_path.name,
                "path": str(file_path),
                "category": "uncategorized",
                "name": file_path.name,
                "status": "Ready",
                "uploaded_at": uploaded_at,
                "size": f"{file_stat.st_size / 1024:.1f} KB",
            }
        )

    return documents


def pdf_text_preview(file_path: str, max_pages: int = 6, max_chars: int = 8000) -> str:
    preview_parts: list[str] = []
    reader = PdfReader(file_path)
    for page in reader.pages[:max_pages]:
        extracted_text = page.extract_text() or ""
        if extracted_text:
            preview_parts.append(extracted_text.strip())
        if sum(len(part) for part in preview_parts) >= max_chars:
            break

    preview_text = "\n\n".join(preview_parts).strip()
    return preview_text[:max_chars]


def read_document_preview(file_path: str) -> str:
    path = Path(file_path)
    try:
        if path.suffix.lower() == ".pdf":
            return pdf_text_preview(file_path)
        if path.suffix.lower() in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")[:8000]
    except Exception as exc:
        return f"[Could not extract text: {exc}]"
    return "[No preview is available for this file type.]"


def get_selected_documents(documents_by_category: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    selected_documents: list[dict[str, Any]] = []
    for category in LOCAL_DOCUMENT_CATEGORIES + ["uncategorized"]:
        for document in documents_by_category.get(category, []):
            if st.session_state.get(f"doc_selected::{document['id']}"):
                selected_documents.append(document)
    return selected_documents


def build_selected_context(selected_documents: list[dict[str, Any]]) -> str:
    context_blocks: list[str] = []
    total_chars = 0
    max_total_chars = 20000

    for document in selected_documents:
        preview_text = read_document_preview(document["path"])
        if not preview_text.strip():
            preview_text = (
                "[No extractable text was found in this document. Do not infer facts from the filename or category.]"
            )

        block = (
            f"Document source: selected local file\n"
            f"Filename: {document['name']}\n"
            f"Category: {document.get('category', 'uncategorized')}\n"
            f"Uploaded: {document.get('uploaded_at', '')}\n"
            f"Content evidence (use this only; filename is metadata, not evidence):\n{preview_text}"
        )

        if total_chars + len(block) > max_total_chars:
            remaining_chars = max_total_chars - total_chars
            if remaining_chars > 0:
                context_blocks.append(block[:remaining_chars])
            context_blocks.append("[Additional selected document content truncated to keep the request small.]")
            break

        context_blocks.append(block)
        total_chars += len(block)

    return "\n\n---\n\n".join(context_blocks)


def render_document_card(document: dict[str, Any]) -> None:
    uploaded_at_line = f"<br/><small>Uploaded: {html.escape(document['uploaded_at'])}</small>" if document.get("uploaded_at") else ""
    st.markdown(
        f"""
        <div class="document-card">
            <b>{html.escape(document['name'])}</b>
            <span class="status-ready">{html.escape(document['status'])}</span>
            {uploaded_at_line}
            <br/><small>Size: {html.escape(document['size'])}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_local_document_panel() -> dict[str, list[dict[str, Any]]]:
    st.header("📄 Knowledge Base")
    st.markdown("Upload and manage policy documents.")
    documents = fetch_local_documents()

    selected_category = st.selectbox(
        "Choose document category",
        LOCAL_DOCUMENT_CATEGORIES,
        format_func=lambda category: LOCAL_DOCUMENT_CATEGORY_LABELS[category],
        key="local_document_category",
    )
    uploaded_file = st.file_uploader("Upload new PDF", type=["pdf"], key="local_document_upload")

    if uploaded_file is not None:
        try:
            target_path = LOCAL_DOCUMENTS_DIR / selected_category / uploaded_file.name
            target_path.write_bytes(uploaded_file.getbuffer())
            st.success(f"{uploaded_file.name} is now available in {selected_category}.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save document locally: {exc}")

    st.subheader("Local Documents")
    st.caption(f"Local storage folder: {LOCAL_DOCUMENTS_DIR.name}")
    st.caption("Select the local documents you want the assistant to use. Use the expanders to keep the list compact.")

    for category in LOCAL_DOCUMENT_CATEGORIES:
        category_documents = documents.get(category, [])
        with st.expander(f"{LOCAL_DOCUMENT_CATEGORY_LABELS[category]} ({len(category_documents)})", expanded=category == "user_uploads"):
            button_col_1, button_col_2 = st.columns(2)
            if button_col_1.button("Select all", key=f"select_all_local_{category}"):
                for document in category_documents:
                    st.session_state[f"doc_selected::{document['id']}"] = True
                st.rerun()
            if button_col_2.button("Clear all", key=f"clear_all_local_{category}"):
                for document in category_documents:
                    st.session_state[f"doc_selected::{document['id']}"] = False
                st.rerun()

            if not category_documents:
                st.caption("No documents in this category yet.")
            else:
                for doc in category_documents:
                    selection_col, details_col = st.columns([0.1, 0.9])
                    with selection_col:
                        st.checkbox("", key=f"doc_selected::{doc['id']}", label_visibility="collapsed")
                    with details_col:
                        render_document_card(doc)

    with st.expander(f"Uncategorized ({len(documents.get('uncategorized', []))})", expanded=False):
        uncategorized_documents = documents.get("uncategorized", [])
        if not uncategorized_documents:
            st.caption("These files are still at the top level of the documents folder.")
        else:
            button_col_1, button_col_2 = st.columns(2)
            if button_col_1.button("Select all", key="select_all_local_uncategorized"):
                for document in uncategorized_documents:
                    st.session_state[f"doc_selected::{document['id']}"] = True
                st.rerun()
            if button_col_2.button("Clear all", key="clear_all_local_uncategorized"):
                for document in uncategorized_documents:
                    st.session_state[f"doc_selected::{document['id']}"] = False
                st.rerun()

            for doc in uncategorized_documents:
                selection_col, details_col = st.columns([0.1, 0.9])
                with selection_col:
                    st.checkbox("", key=f"doc_selected::{doc['id']}", label_visibility="collapsed")
                with details_col:
                    render_document_card(doc)

    return documents


def render_theme_hero() -> None:
    st.markdown(
        """
        <div class="theme-hero">
            <span class="theme-kicker">Sarvam AI x HCLTech inspired workspace</span>
            <h1 class="theme-title">Policy Intelligence Studio</h1>
            <p class="theme-subtitle">
                Split workspace for local policy browsing, OCR ingestion, vector search, and voice interactions.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> dict[str, Any]:
    st.sidebar.title("Configuration")
    api_key = st.sidebar.text_input(
        "Sarvam API Key",
        value=st.session_state.get("api_key", ""),
        type="password",
        help="You can paste your key here for this session or store it in .env as SARVAM_API_KEY.",
    )
    st.session_state["api_key"] = api_key

    language_labels = ["Auto / Same as query"] + list(LANGUAGES.keys())
    selected_label = st.sidebar.selectbox("Response language", options=language_labels, index=0)
    response_language = "auto" if selected_label == "Auto / Same as query" else LANGUAGES[selected_label]
    audio_language_label = st.sidebar.selectbox("Audio reply language", options=build_tts_language_options(), index=0)
    if audio_language_label == "Same as response (if supported)":
        audio_language = "auto"
    else:
        audio_language = LANGUAGES.get(audio_language_label, "en-IN")

    generate_audio = st.sidebar.checkbox("Generate voice reply", value=True)
    stream_responses = st.sidebar.checkbox("Stream chat responses", value=True)
    stream_audio_reply = st.sidebar.checkbox("Stream audio reply (Beta)", value=False)
    speaker = st.sidebar.text_input("TTS speaker", value=DEFAULT_TTS_SPEAKER)
    top_k = 5
    st.sidebar.caption("Top semantic matches shown: 5")
    chat_model = st.sidebar.text_input("Chat model", value=DEFAULT_CHAT_MODEL)
    temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.5, value=0.2, step=0.1)

    if st.sidebar.button("Clear chat history", use_container_width=True):
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": "Hello! I am your AI Policy Assistant. Ask me anything about the uploaded documents.",
            }
        ]
        st.rerun()

    return {
        "response_language": response_language,
        "audio_language": audio_language,
        "generate_audio": generate_audio,
        "stream_responses": stream_responses,
        "stream_audio_reply": stream_audio_reply,
        "speaker": speaker.strip() or DEFAULT_TTS_SPEAKER,
        "top_k": top_k,
        "chat_model": chat_model.strip() or DEFAULT_CHAT_MODEL,
        "temperature": temperature,
    }


def render_status_banner(sarvam: SarvamService, store: DocumentStore) -> None:
    if sarvam.is_configured:
        st.success("Sarvam API key detected. Chat, OCR, translation, speech-to-text, and text-to-speech are enabled.")
    else:
        st.warning(
            "Add your Sarvam API key in the sidebar to enable live chat, OCR, translation, and voice features. "
            "You can still ingest local text and PDF files without it."
        )
    st.caption("Use the Chat tab for local document selection and grounded answers, then the Ingestion tab for vector indexing.")
    if store.embedding_service.backend == "sentence-transformers":
        st.caption(
            f"Semantic retrieval: {store.embedding_service.model_name} "
            f"({store.embedding_service.dimension} dimensions)"
        )
    else:
        st.caption("Semantic retrieval fallback: hashing backend. Install `sentence-transformers` for stronger multilingual search.")


def format_source_label(source: dict[str, Any]) -> str:
    source_name = source.get("source_name", "Unknown source")
    chunk_index = source.get("chunk_index", 0)
    score = source.get("score")
    score_text = f"{score:.3f}" if isinstance(score, float) else "n/a"
    page_start = source.get("page_start")
    page_end = source.get("page_end")
    if page_start is None:
        page_text = "page n/a"
    elif page_start == page_end:
        page_text = f"page {page_start}"
    else:
        page_text = f"pages {page_start}-{page_end}"
    return f"{source_name} | {page_text} | chunk {chunk_index} | score {score_text}"


def format_runtime_error(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if "insufficient_quota_error" in lowered or "no credits available" in lowered:
        return (
            "Voice transcription is temporarily unavailable because the Sarvam account has no speech credits left. "
            "You can still type your question in the chat box, or recharge/add credits and try voice again."
        )
    if "429" in lowered:
        return "Voice transcription is being rate-limited right now. Please wait a little and try again."
    if "invalid_api_key" in lowered or "authentication credentials" in lowered:
        return "Voice transcription could not start because the Sarvam API key is invalid or missing."
    return message


def render_custom_audio_player(
    audio_bytes: bytes,
    mime_type: str,
    player_key: str,
    autoplay: bool = False,
    caption: str | None = None,
) -> None:
    if not audio_bytes:
        return
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    caption_html = f"<div class='audio-caption'>{html.escape(caption)}</div>" if caption else ""
    autoplay_attr = "autoplay" if autoplay else ""
    component_html = f"""
    <div style="border:1px solid #d9d9d9;border-radius:12px;padding:10px 12px;background:#fafafa;">
      {caption_html}
      <audio id="audio-{player_key}" controls {autoplay_attr} style="width:100%;">
        <source src="data:{mime_type};base64,{audio_b64}" type="{mime_type}">
      </audio>
    </div>
    """
    components.html(component_html, height=92 if caption else 78)


def render_message(message: dict[str, Any]) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        sources = message.get("sources") or []
        if sources:
            with st.expander("Sources used"):
                for source in sources:
                    st.write(format_source_label(source))
                    preview = source.get("original_text") or source.get("search_text") or ""
                    st.caption(preview[:400] + ("..." if len(preview) > 400 else ""))
        audio_bytes = message.get("audio_bytes")
        if audio_bytes:
            mime_type = message.get("audio_format") or "audio/wav"
            player_key = hashlib.sha1(
                ((message.get("content") or "") + mime_type + str(len(audio_bytes))).encode("utf-8", errors="ignore")
            ).hexdigest()[:16]
            render_custom_audio_player(
                audio_bytes=audio_bytes,
                mime_type=mime_type,
                player_key=f"history-{player_key}",
                autoplay=False,
                caption="Voice reply",
            )


def render_chat_history() -> None:
    for message in st.session_state["messages"]:
        render_message(message)


def process_voice_prompt(sarvam: SarvamService) -> None:
    st.subheader("Voice Input")
    st.caption("Voice query ke liye audio upload recommended hai. Browser microphone mode kuch systems par unstable ho sakta hai.")

    voice_mode = st.radio(
        "Voice input method",
        options=["Upload audio (Recommended)", "Record with microphone (Beta)"],
        index=0,
        horizontal=True,
    )

    audio_file = None
    if voice_mode == "Record with microphone (Beta)":
        st.info(
            "Agar microphone par generic error aaye, Chrome/Edge use kijiye, mic permission allow kijiye, "
            "ya upload mode par switch kijiye."
        )
        if hasattr(st, "audio_input"):
            audio_file = st.audio_input("Record your question")
        else:
            st.warning("Microphone capture is not available in this Streamlit build. Upload audio use kijiye.")

    uploaded_audio = st.file_uploader(
        "Upload an audio question",
        type=["wav", "mp3", "m4a", "ogg", "aac", "flac"],
        accept_multiple_files=False,
        key="voice_upload",
        disabled=voice_mode != "Upload audio (Recommended)",
    )
    audio_source = uploaded_audio if voice_mode == "Upload audio (Recommended)" else audio_file

    if audio_source is None:
        return

    digest = f"{audio_source.name}:{audio_source.size}"
    if digest == st.session_state.get("last_audio_digest"):
        return

    if not sarvam.is_configured:
        st.error("Voice transcription requires a valid Sarvam API key in the sidebar.")
        return

    try:
        with st.spinner("Transcribing voice query..."):
            transcript = sarvam.transcribe_audio(
                audio_bytes=audio_source.getvalue(),
                filename=audio_source.name,
                language_code=None,
                translate_to_english=False,
            )
    except Exception as exc:
        st.error(format_runtime_error(exc))
        st.caption("Fallback: chat text box me directly apna question type karke continue kar sakte hain.")
        return

    st.session_state["last_audio_digest"] = digest
    st.session_state["last_voice_prompt"] = {
        "text": transcript["transcript"],
        "language_code": transcript.get("language_code") or "auto",
    }
    st.session_state["prompt_draft"] = transcript["transcript"]
    st.success(f"Voice captured: {transcript['transcript']}")


def render_chat_prompt_box() -> str | None:
    st.subheader("Ask a Policy Question")
    st.caption("Type your question below. You can ask in English or Indian languages.")
    return st.chat_input("Ask about schemes, eligibility, or rules...")


def render_chat_upload_box() -> None:
    st.subheader("Add New Policy Documents For This Chat")
    st.caption("Nayi PDF/image/text file upload karke usko OCR, English translation index, aur vector DB me add kijiye.")

    sarvam = get_sarvam_service()
    ingestion = get_ingestion_service()
    uploaded_files = st.file_uploader(
        "Upload files for immediate chat use",
        type=["pdf", "png", "jpg", "jpeg", "zip", "txt", "md", "csv", "json"],
        accept_multiple_files=True,
        key="chat_uploads",
    )
    language_label = st.selectbox("Uploaded document language", options=list(LANGUAGES.keys()), index=0, key="chat_doc_language")
    language_code = LANGUAGES[language_label]

    if st.button("Add Documents To Knowledge Base", use_container_width=True, disabled=not uploaded_files, key="chat_upload_button"):
        if not sarvam.is_configured:
            st.error("Document OCR aur translation ke liye valid Sarvam API key chahiye.")
            return

        success_count = 0
        for uploaded in uploaded_files or []:
            with st.spinner(f"Adding {uploaded.name} to the chat knowledge base..."):
                try:
                    summary = ingestion.ingest_uploaded_file(
                        uploaded_file=uploaded,
                        sarvam=sarvam,
                        language_code=language_code,
                        use_ocr=True,
                        build_translation_index=True,
                    )
                    success_count += 1
                    st.success(
                        f"{summary['source_name']} added | chunks: {summary['chunk_count']} | method: {summary['extraction_method']}"
                    )
                    for warning in summary.get("warnings", []):
                        st.warning(warning)
                except Exception as exc:
                    st.error(f"{uploaded.name} failed: {exc}")

        if success_count:
            st.info("Documents are indexed and ready for immediate chat.")


def build_rag_prompt(query: str, contexts: list[dict[str, Any]], response_language: str, extra_context: str = "") -> str:
    context_lines: list[str] = []
    for idx, item in enumerate(contexts, start=1):
        source_name = item.get("source_name", "Unknown source")
        chunk_index = item.get("chunk_index", 0)
        original_text = item.get("original_text") or ""
        translated_text = item.get("translated_text") or ""
        context_lines.append(
            f"[Source {idx}] file={source_name}, chunk={chunk_index}\n"
            f"Original text:\n{original_text}\n"
            f"English retrieval copy:\n{translated_text}\n"
        )

    language_instruction = (
        "Respond in the same language as the user's latest question."
        if response_language == "auto"
        else f"Respond in {response_language}."
    )

    sections = [
        "You are a policy assistant. Answer only from the retrieved policy context.",
        "If selected local documents are provided, treat their extracted text as evidence too.",
        "If the context is insufficient, say that the answer is not available in the policy documents.",
        "",
        language_instruction,
        "Cite the relevant file names naturally in your answer when possible.",
        "",
    ]
    if extra_context.strip():
        sections.extend([
            "Selected local document evidence:",
            extra_context,
            "",
        ])
    sections.extend([
        "Retrieved context:",
        "\n".join(context_lines),
        f"User question:\n{query}",
    ])
    return "\n".join(sections)


def build_chat_messages(
    chat_history: list[dict[str, Any]],
    rag_prompt: str,
    user_query: str,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    recent_history = chat_history[-6:]

    for message in recent_history:
        role = message.get("role")
        content = (message.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        if not messages and role != "user":
            continue
        if messages and messages[-1]["role"] == role:
            continue
        messages.append({"role": role, "content": content})

    grounded_user_message = f"{rag_prompt}\n\nAnswer the user's latest question using the context above."
    if not messages:
        messages.append({"role": "user", "content": grounded_user_message})
        return messages

    if messages[-1]["role"] == "user":
        messages[-1]["content"] = f"{messages[-1]['content']}\n\n{grounded_user_message}"
    else:
        messages.append({"role": "user", "content": grounded_user_message})

    return messages


def run_chat(
    sarvam: SarvamService,
    store: DocumentStore,
    settings: dict[str, Any],
    user_query: str,
    input_language_code: str,
    local_document_context: str = "",
    stream_callback: Callable[[str, bool], None] | None = None,
    audio_stream_callback: Callable[[bytes, bool], None] | None = None,
) -> dict[str, Any]:
    store_count = store.count()
    if store_count == 0 and not local_document_context.strip():
        return {
            "answer": "Knowledge base abhi empty hai. Pehle Ingestion tab se policy documents upload kijiye, phir chat kijiye.",
            "sources": [],
            "audio_bytes": None,
            "audio_format": None,
        }

    retrieval_query = user_query
    translated_query = ""
    if sarvam.is_configured:
        try:
            translated_query, detected_code = sarvam.translate_for_retrieval(user_query, input_language_code)
            retrieval_query = translated_query or user_query
            input_language_code = detected_code or input_language_code
        except Exception:
            retrieval_query = user_query

    hits = []
    if store_count > 0:
        hits = store.hybrid_search(
            original_query=user_query,
            translated_query=retrieval_query,
            top_k=settings["top_k"],
        )
    rag_prompt = build_rag_prompt(
        query=user_query,
        contexts=hits,
        response_language=settings["response_language"],
        extra_context=local_document_context,
    )

    messages = build_chat_messages(
        chat_history=st.session_state["messages"],
        rag_prompt=rag_prompt,
        user_query=user_query,
    )

    answer_text = ""
    if stream_callback is not None:
        try:
            for chunk in sarvam.stream_chat(
                messages=messages,
                model=settings["chat_model"],
                temperature=settings["temperature"],
            ):
                answer_text += chunk
                stream_callback(answer_text, False)
        except Exception:
            answer_text = ""

    if not answer_text.strip():
        answer = sarvam.chat(
            messages=messages,
            model=settings["chat_model"],
            temperature=settings["temperature"],
        )
        answer_text = answer["content"]
        if stream_callback is not None:
            stream_callback(answer_text, True)

    target_audio_language = settings["audio_language"]
    if target_audio_language == "auto":
        target_audio_language = settings["response_language"]
    if target_audio_language == "auto":
        target_audio_language = input_language_code or "en-IN"
    audio_bytes = None
    audio_text = answer_text
    audio_format = "audio/wav"
    if settings["generate_audio"] and sarvam.is_configured:
        if target_audio_language not in TTS_LANGUAGE_CODES:
            target_audio_language = "en-IN"
            try:
                source_language = settings["response_language"]
                if source_language == "auto":
                    source_language = input_language_code or "en-IN"
                audio_text = sarvam.translate_text(
                    text=answer_text,
                    source_language_code=source_language,
                    target_language_code=target_audio_language,
                )
            except Exception:
                audio_text = answer_text
        try:
            if settings.get("stream_audio_reply") and audio_stream_callback is not None:
                audio_bytes = sarvam.synthesize_speech_streaming(
                    text=audio_text,
                    target_language_code=target_audio_language,
                    speaker=settings["speaker"],
                    chunk_callback=audio_stream_callback,
                )
                audio_format = "audio/mp3"
            else:
                audio_bytes = sarvam.synthesize_speech(
                    text=audio_text,
                    target_language_code=target_audio_language,
                    speaker=settings["speaker"],
                )
                audio_format = "audio/wav"
        except Exception:
            audio_bytes = None

    return {
        "answer": answer_text,
        "sources": hits,
        "audio_bytes": audio_bytes,
        "audio_format": audio_format if audio_bytes else None,
    }


def render_chat_tab(settings: dict[str, Any]) -> None:
    sarvam = get_sarvam_service()
    store = get_document_store()
    col_docs, col_chat = st.columns([3, 5], gap="large")

    with col_docs:
        documents = render_local_document_panel()

    with col_chat:
        st.header("🤖 Policy Assistant")
        selected_documents = get_selected_documents(documents)
        all_documents: list[dict[str, Any]] = []
        for category in LOCAL_DOCUMENT_CATEGORIES + ["uncategorized"]:
            all_documents.extend(documents.get(category, []))

        active_documents = selected_documents if selected_documents else all_documents
        if selected_documents:
            st.caption("Using selected local documents only:")
            st.markdown(
                ", ".join(html.escape(document["name"]) for document in selected_documents),
                unsafe_allow_html=True,
            )
        elif active_documents:
            st.info("No document selected. Currently using all available local documents as reference.")
        elif store.count() > 0:
            st.info("No local documents are available yet. The indexed knowledge base is still ready for chat.")
        else:
            st.warning("No documents are available yet. Upload a PDF or ingest files to begin.")

        chat_container = st.container(height=760, border=True)
        with chat_container:
            render_chat_history()

        typed_prompt = render_chat_prompt_box()
        process_voice_prompt(sarvam)
        voice_prompt = st.session_state.pop("last_voice_prompt", None)

        prompt = typed_prompt or (voice_prompt or {}).get("text")
        input_language = (voice_prompt or {}).get("language_code", "auto")

        if not prompt:
            return

        st.session_state["messages"].append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            if not sarvam.is_configured:
                with st.chat_message("assistant"):
                    st.error("Add your Sarvam API key in the sidebar so I can query Sarvam chat and speech services.")
                return

            local_document_context = build_selected_context(selected_documents or active_documents)

            with st.chat_message("assistant"):
                response_placeholder = st.empty()

                def stream_to_ui(text: str, is_final: bool) -> None:
                    suffix = "" if is_final else "▌"
                    response_placeholder.markdown(f"{text}{suffix}")

                with st.spinner("Reading policy context and drafting an answer..."):
                    result = run_chat(
                        sarvam=sarvam,
                        store=store,
                        settings=settings,
                        user_query=prompt,
                        input_language_code=input_language,
                        local_document_context=local_document_context,
                        stream_callback=stream_to_ui if settings["stream_responses"] else None,
                    )
                response_placeholder.markdown(result["answer"])
                if result["sources"]:
                    with st.expander("Sources used"):
                        for source in result["sources"]:
                            st.write(format_source_label(source))
                            preview = source.get("original_text") or source.get("search_text") or ""
                            st.caption(preview[:400] + ("..." if len(preview) > 400 else ""))
                if result["audio_bytes"]:
                    st.audio(result["audio_bytes"], format="audio/wav")

        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": result["answer"],
                "sources": result["sources"],
                "audio_bytes": result["audio_bytes"],
            }
        )


def render_chat_tab_streaming(settings: dict[str, Any]) -> None:
    sarvam = get_sarvam_service()
    store = get_document_store()
    col_docs, col_chat = st.columns([3, 5], gap="large")

    with col_docs:
        documents = render_local_document_panel()

    with col_chat:
        st.header("🤖 Policy Assistant")
        selected_documents = get_selected_documents(documents)
        all_documents: list[dict[str, Any]] = []
        for category in LOCAL_DOCUMENT_CATEGORIES + ["uncategorized"]:
            all_documents.extend(documents.get(category, []))

        active_documents = selected_documents if selected_documents else all_documents
        if selected_documents:
            st.caption("Using selected local documents only:")
            st.markdown(
                ", ".join(html.escape(document["name"]) for document in selected_documents),
                unsafe_allow_html=True,
            )
        elif active_documents:
            st.info("No document selected. Currently using all available local documents as reference.")
        elif store.count() > 0:
            st.info("No local documents are available yet. The indexed knowledge base is still ready for chat.")
        else:
            st.warning("No documents are available yet. Upload a PDF or ingest files to begin.")

        chat_container = st.container(height=760, border=True)
        with chat_container:
            render_chat_history()

        typed_prompt = render_chat_prompt_box()
        process_voice_prompt(sarvam)
        voice_prompt = st.session_state.pop("last_voice_prompt", None)

        prompt = typed_prompt or (voice_prompt or {}).get("text")
        input_language = (voice_prompt or {}).get("language_code", "auto")

        if not prompt:
            return

        st.session_state["messages"].append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            if not sarvam.is_configured:
                with st.chat_message("assistant"):
                    st.error("Add your Sarvam API key in the sidebar so I can query Sarvam chat and speech services.")
                return

            local_document_context = build_selected_context(selected_documents or active_documents)

            response_id = uuid.uuid4().hex
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                audio_placeholder = st.empty()

                def stream_to_ui(text: str, is_final: bool) -> None:
                    suffix = "" if is_final else "|"
                    response_placeholder.markdown(f"{text}{suffix}")

                stream_state = {"last_length": 0}

                def stream_audio_to_ui(audio_data: bytes, is_final: bool) -> None:
                    minimum_delta = 24000
                    should_refresh = is_final or (len(audio_data) - stream_state["last_length"] >= minimum_delta)
                    if not should_refresh:
                        return
                    stream_state["last_length"] = len(audio_data)
                    with audio_placeholder.container():
                        render_custom_audio_player(
                            audio_bytes=audio_data,
                            mime_type="audio/mp3",
                            player_key=f"stream-{response_id}",
                            autoplay=True,
                            caption="Streaming voice reply",
                        )

                with st.spinner("Reading policy context and drafting an answer..."):
                    result = run_chat(
                        sarvam=sarvam,
                        store=store,
                        settings=settings,
                        user_query=prompt,
                        input_language_code=input_language,
                        local_document_context=local_document_context,
                        stream_callback=stream_to_ui if settings["stream_responses"] else None,
                        audio_stream_callback=stream_audio_to_ui if settings["stream_audio_reply"] else None,
                    )
                response_placeholder.markdown(result["answer"])
                if result["sources"]:
                    with st.expander("Sources used"):
                        for source in result["sources"]:
                            st.write(format_source_label(source))
                            preview = source.get("original_text") or source.get("search_text") or ""
                            st.caption(preview[:400] + ("..." if len(preview) > 400 else ""))
                if result["audio_bytes"]:
                    with audio_placeholder.container():
                        render_custom_audio_player(
                            audio_bytes=result["audio_bytes"],
                            mime_type=result.get("audio_format") or "audio/wav",
                            player_key=f"final-{response_id}",
                            autoplay=False,
                            caption="Voice reply",
                        )

        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": result["answer"],
                "sources": result["sources"],
                "audio_bytes": result["audio_bytes"],
                "audio_format": result.get("audio_format"),
            }
        )


def render_ingestion_tab() -> None:
    st.subheader("Ingest Policies and OCR Documents")
    sarvam = get_sarvam_service()
    ingestion = get_ingestion_service()

    uploaded_files = st.file_uploader(
        "Upload policy files",
        type=["pdf", "png", "jpg", "jpeg", "zip", "txt", "md", "csv", "json"],
        accept_multiple_files=True,
        help="Use OCR for scanned PDFs/images. Plain text and digital PDFs can be parsed locally.",
    )

    language_label = st.selectbox("Document language", options=list(LANGUAGES.keys()), index=0)
    language_code = LANGUAGES[language_label]
    use_ocr = st.checkbox("Use Sarvam Document Intelligence OCR", value=True)
    st.info("English translation index is mandatory in this build so BAAI embeddings can semantically match mixed-language policy documents.")

    if st.button("Ingest selected files", use_container_width=True, disabled=not uploaded_files):
        if use_ocr and not sarvam.is_configured:
            st.error("OCR ingestion needs a Sarvam API key.")
            return

        success_count = 0
        for uploaded in uploaded_files or []:
            with st.spinner(f"Processing {uploaded.name}..."):
                try:
                    summary = ingestion.ingest_uploaded_file(
                        uploaded_file=uploaded,
                        sarvam=sarvam,
                        language_code=language_code,
                        use_ocr=use_ocr,
                        build_translation_index=True,
                    )
                    success_count += 1
                    st.success(
                        f"{summary['source_name']} ingested | chunks: {summary['chunk_count']} | method: {summary['extraction_method']}"
                    )
                    for warning in summary.get("warnings", []):
                        st.warning(warning)
                except Exception as exc:
                    st.error(f"{uploaded.name} failed: {exc}")

        if success_count:
            st.info(f"{success_count} file(s) were added to the vector store.")


def render_library_tab() -> None:
    store = get_document_store()
    st.subheader("Knowledge Base")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Indexed chunks", store.count())
    with col2:
        st.metric("Source files", len(store.list_sources()))

    for source in store.list_sources():
        cols = st.columns([5, 1])
        with cols[0]:
            st.write(
                f"{source['source_name']} | method={source.get('extraction_method', 'unknown')} | "
                f"chunks={source.get('chunk_count', 0)} | language={source.get('language_code', 'n/a')}"
            )
        with cols[1]:
            if st.button("Delete", key=f"delete-{source['document_id']}"):
                store.delete_source(source["document_id"])
                st.rerun()


def main() -> None:
    init_state()
    settings = render_sidebar()
    sarvam = get_sarvam_service()
    store = get_document_store()

    render_theme_hero()
    render_status_banner(sarvam, store)

    chat_tab, ingest_tab, library_tab = st.tabs(["Chat", "Ingestion", "Library"])
    with chat_tab:
        render_chat_tab_streaming(settings)
    with ingest_tab:
        render_ingestion_tab()
    with library_tab:
        render_library_tab()


if __name__ == "__main__":
    main()
