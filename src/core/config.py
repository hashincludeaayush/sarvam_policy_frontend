from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    data_dir: Path
    uploads_dir: Path
    ocr_dir: Path
    audio_dir: Path
    model_cache_dir: Path
    vector_store_dir: Path
    collection_name: str
    sarvam_api_key: str
    chunk_size: int
    chunk_overlap: int
    embedding_backend: str
    embedding_model: str
    embedding_dimensions: int


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    root_dir = Path(__file__).resolve().parents[2]
    load_dotenv(root_dir / ".env")

    data_dir = root_dir / "data"
    uploads_dir = data_dir / "uploads"
    ocr_dir = data_dir / "ocr"
    audio_dir = data_dir / "audio"
    model_cache_dir = data_dir / "models"
    vector_store_dir = data_dir / "vector_store"

    for path in (data_dir, uploads_dir, ocr_dir, audio_dir, model_cache_dir, vector_store_dir):
        path.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        root_dir=root_dir,
        data_dir=data_dir,
        uploads_dir=uploads_dir,
        ocr_dir=ocr_dir,
        audio_dir=audio_dir,
        model_cache_dir=model_cache_dir,
        vector_store_dir=vector_store_dir,
        collection_name=os.getenv("VECTOR_COLLECTION", "policy_knowledge_base"),
        sarvam_api_key=os.getenv("SARVAM_API_KEY", ""),
        chunk_size=int(os.getenv("CHUNK_SIZE", "1200")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
        embedding_backend=os.getenv("EMBEDDING_BACKEND", "auto"),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL",
            "BAAI/bge-large-en-v1.5",
        ),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "1024")),
    )
