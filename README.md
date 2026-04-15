# Sarvam Policy Assistant

This project is a Streamlit app for:

- multilingual policy Q&A over a persistent local vector store
- OCR ingestion from the UI using Sarvam Document Intelligence
- chat in Indian languages with Sarvam chat models
- text and voice interaction using Sarvam speech APIs
- storing OCR output in the same searchable knowledge base used by chat

## What is included

- `app.py`: main Streamlit application
- `src/services/sarvam_service.py`: Sarvam SDK wrapper for chat, translation, OCR, STT, and TTS
- `src/services/document_store.py`: persistent Chroma-backed vector store
- `src/services/ingestion_service.py`: upload, OCR/local parsing, chunking, and indexing pipeline
- `data/`: local storage for uploaded files, OCR artifacts, audio, and vector data

## Architecture

1. User uploads policy files from the Streamlit UI.
2. Scanned PDFs and images go through Sarvam Document Intelligence OCR when possible.
3. Extracted text is chunked and each chunk is translated to English for retrieval using Sarvam Translate.
4. English search chunks are embedded with `BAAI/bge-large-en-v1.5` when available, with a hashing fallback if the model cannot be loaded.
5. Each chunk is saved with metadata such as document id, filename, page range, ingestion time, and text statistics.
6. User asks questions through text or voice input.
7. The app translates the user query to English for retrieval, reranks results, and uses the top 5 matches.
8. The answer is shown as text and can also be synthesized to speech.

## Setup

### 1. Create and activate a virtual environment

```powershell
cd c:\Users\vmadmin\Downloads\sarvam_policy_assistant
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment

```powershell
Copy-Item .env.example .env
```

Then set your Sarvam key in `.env`:

```env
SARVAM_API_KEY=your_key_here
```

Optional embedding settings:

```env
EMBEDDING_BACKEND=auto
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
```

### 4. Run the app

```powershell
streamlit run app.py
```

## Usage notes

- Paste the Sarvam API key in the sidebar or keep it in `.env`.
- Use the `Ingestion` tab to upload PDFs, images, or text files.
- Enable OCR for scanned policy documents. Large PDFs are automatically split into OCR-safe batches.
- Every ingested document is prepared with an English retrieval index so mixed-language documents work better with English embeddings.
- Use the `Chat` tab for text or voice questions. You can also upload fresh documents there and chat immediately.
- Use the `Chat` tab to browse local policy folders, select evidence documents, and ask grounded questions in the split studio view.
- Use `Upload audio (Recommended)` for the most reliable voice-query flow.
- Enable `Stream chat responses` for token-like text streaming and `Stream audio reply (Beta)` for progressive audio updates.
- Streaming audio uses sentence-sized TTS chunks and a custom browser audio player for lower perceived latency.
- The app retrieves and shows the top 5 grounded matches with page-aware metadata.
- If the selected audio language is unsupported by TTS, the app falls back to English audio.
- Streaming audio is delivered as progressive MP3 updates in the current UI. Depending on the browser, playback may restart from the latest chunk as the audio element refreshes.

## Important implementation note

On the first run, `sentence-transformers` may download the `BAAI/bge-large-en-v1.5` model. If that is unavailable, the app still works using a hashing fallback, but retrieval quality will be lower than the transformer-backed path.
