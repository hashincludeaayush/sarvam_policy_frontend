from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from src.core.config import AppConfig
from src.services.document_store import DocumentStore
from src.services.sarvam_service import SarvamService


class IngestionService:
    def __init__(self, config: AppConfig, store: DocumentStore) -> None:
        self.config = config
        self.store = store

    def ingest_uploaded_file(
        self,
        uploaded_file: Any,
        sarvam: SarvamService,
        language_code: str,
        use_ocr: bool,
        build_translation_index: bool = True,
    ) -> dict[str, Any]:
        document_id = uuid.uuid4().hex
        saved_path = self._save_upload(uploaded_file, document_id)
        ingested_at = datetime.now(timezone.utc).isoformat()

        extraction_warnings: list[str] = []
        if use_ocr and saved_path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".zip"}:
            try:
                segments, extraction_method = sarvam.extract_document_segments(
                    file_path=saved_path,
                    language_code=language_code,
                    output_dir=self.config.ocr_dir,
                )
            except Exception as exc:
                if saved_path.suffix.lower() == ".pdf":
                    segments = self._extract_local_segments(saved_path)
                    extraction_method = "local-parser-fallback"
                    extraction_warnings.append(f"OCR fallback applied: {exc}")
                else:
                    raise
        else:
            segments = self._extract_local_segments(saved_path)
            extraction_method = "local-parser"

        if not any((segment.get("text") or "").strip() for segment in segments):
            raise ValueError("No text could be extracted from this file.")

        chunk_payloads = self._build_chunk_payloads(
            segments=segments,
            language_code=language_code,
            sarvam=sarvam,
            enabled=build_translation_index,
        )

        records: list[dict[str, Any]] = []
        file_size_bytes = saved_path.stat().st_size
        original_filename = self._original_filename(saved_path)
        for idx, payload in enumerate(chunk_payloads):
            chunk = payload["original_text"]
            translated_text = payload["translated_text"]
            page_start = payload["page_start"]
            page_end = payload["page_end"]
            location_prefix = self._build_location_prefix(original_filename, page_start, page_end)
            search_text = f"{location_prefix}\n{translated_text or chunk}".strip()
            records.append(
                {
                    "chunk_id": f"{document_id}:{idx}",
                    "document_id": document_id,
                    "chunk_index": idx,
                    "source_name": original_filename,
                    "stored_filename": saved_path.name,
                    "file_extension": saved_path.suffix.lower(),
                    "file_size_bytes": file_size_bytes,
                    "language_code": language_code,
                    "extraction_method": extraction_method,
                    "ingested_at": ingested_at,
                    "page_start": page_start,
                    "page_end": page_end,
                    "char_count": len(chunk),
                    "word_count": len(chunk.split()),
                    "original_text": chunk,
                    "translated_text": translated_text,
                    "translation_index_language": "en-IN",
                    "search_text": search_text,
                }
            )

        self.store.upsert_documents(records)
        return {
            "document_id": document_id,
            "source_name": original_filename,
            "chunk_count": len(records),
            "extraction_method": extraction_method,
            "warnings": extraction_warnings,
        }

    def _save_upload(self, uploaded_file: Any, document_id: str) -> Path:
        safe_name = uploaded_file.name.replace(" ", "_")
        destination = self.config.uploads_dir / f"{document_id}_{safe_name}"
        destination.write_bytes(uploaded_file.getvalue())
        return destination

    def _extract_local_segments(self, path: Path) -> list[dict[str, Any]]:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return [{"text": path.read_text(encoding="utf-8", errors="ignore"), "page_start": None, "page_end": None}]
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            return [{"text": json.dumps(data, ensure_ascii=False, indent=2), "page_start": None, "page_end": None}]
        if suffix == ".csv":
            rows: list[str] = []
            with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    rows.append(" | ".join(row))
            return [{"text": "\n".join(rows), "page_start": None, "page_end": None}]
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            pages: list[dict[str, Any]] = []
            for page_number, page in enumerate(reader.pages, start=1):
                pages.append(
                    {
                        "text": page.extract_text() or "",
                        "page_start": page_number,
                        "page_end": page_number,
                    }
                )
            return pages
        raise ValueError(f"Unsupported file type for local parsing: {suffix}")

    def _build_chunk_payloads(
        self,
        segments: list[dict[str, Any]],
        language_code: str,
        sarvam: SarvamService,
        enabled: bool,
    ) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for segment in segments:
            segment_text = (segment.get("text") or "").strip()
            if not segment_text:
                continue
            chunks = self._chunk_text(segment_text)
            translated_chunks = self._build_translation_index(
                chunks=chunks,
                language_code=language_code,
                sarvam=sarvam,
                enabled=enabled,
            )
            for index, chunk in enumerate(chunks):
                payloads.append(
                    {
                        "original_text": chunk,
                        "translated_text": translated_chunks[index] if index < len(translated_chunks) else "",
                        "page_start": segment.get("page_start"),
                        "page_end": segment.get("page_end"),
                    }
                )
        return payloads

    def _chunk_text(self, text: str) -> list[str]:
        paragraphs = self._normalize_paragraphs(text)
        if not paragraphs:
            return []

        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
            if len(candidate) <= self.config.chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current.strip())
                overlap_text = self._tail_overlap(current)
                current = f"{overlap_text}\n\n{paragraph}".strip() if overlap_text else paragraph
            else:
                chunks.extend(self._split_long_paragraph(paragraph))
                current = ""

            if len(current) > self.config.chunk_size:
                chunks.extend(self._split_long_paragraph(current))
                current = ""

        if current:
            chunks.append(current.strip())
        return [chunk for chunk in chunks if chunk.strip()]

    def _build_translation_index(
        self,
        chunks: list[str],
        language_code: str,
        sarvam: SarvamService,
        enabled: bool,
    ) -> list[str]:
        if not enabled:
            return chunks
        if language_code == "en-IN":
            return chunks
        if not sarvam.is_configured:
            raise ValueError("English translation index requires a valid Sarvam API key for non-English documents.")

        translated: list[str] = []
        for chunk in chunks:
            translated.append(
                sarvam.translate_text(
                    text=chunk,
                    source_language_code=language_code,
                    target_language_code="en-IN",
                )
            )
        return translated

    @staticmethod
    def _normalize_paragraphs(text: str) -> list[str]:
        normalized = text.replace("\r\n", "\n")
        raw_parts = normalized.split("\n\n")
        paragraphs: list[str] = []
        for part in raw_parts:
            cleaned = " ".join(part.split())
            if cleaned:
                paragraphs.append(cleaned)
        if paragraphs:
            return paragraphs
        fallback = " ".join(text.split())
        return [fallback] if fallback else []

    def _split_long_paragraph(self, text: str) -> list[str]:
        compact = " ".join(text.split())
        if len(compact) <= self.config.chunk_size:
            return [compact]

        chunks: list[str] = []
        step = max(1, self.config.chunk_size - self.config.chunk_overlap)
        start = 0
        while start < len(compact):
            end = min(start + self.config.chunk_size, len(compact))
            chunk = compact[start:end]
            if end < len(compact):
                boundary = chunk.rfind(" ")
                if boundary > self.config.chunk_size // 2:
                    chunk = chunk[:boundary]
                    end = start + boundary
            chunks.append(chunk.strip())
            if end >= len(compact):
                break
            start = max(end - self.config.chunk_overlap, start + step)
        return [chunk for chunk in chunks if chunk]

    def _tail_overlap(self, text: str) -> str:
        compact = " ".join(text.split())
        if len(compact) <= self.config.chunk_overlap:
            return compact
        tail = compact[-self.config.chunk_overlap :]
        boundary = tail.find(" ")
        return tail[boundary + 1 :].strip() if boundary != -1 else tail.strip()

    @staticmethod
    def _original_filename(path: Path) -> str:
        parts = path.name.split("_", 1)
        return parts[1] if len(parts) == 2 else path.name

    @staticmethod
    def _build_location_prefix(source_name: str, page_start: int | None, page_end: int | None) -> str:
        if page_start is None:
            return f"Source: {source_name}"
        if page_start == page_end:
            return f"Source: {source_name}\nPage: {page_start}"
        return f"Source: {source_name}\nPages: {page_start}-{page_end}"
