"""
ChromaDB implementation of VectorDatabaseInterface.
"""

import shutil
import time
from pathlib import Path
from typing import Any, Callable

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from langchain_core.documents import Document

from utils.logger import get_logger
from utils.vector_db_base import VectorDatabaseInterface

logger = get_logger(name=__name__)

_MAX_CREATE_RETRIES = 3
_CHROMA_DB_FILE = "chroma.sqlite3"
_CHROMA_WAL_FILES = ("chroma.sqlite3", "chroma.sqlite3-shm", "chroma.sqlite3-wal")


class ChromaVectorDatabase(VectorDatabaseInterface):
    """ChromaDB-backed vector database."""

    def __init__(
        self,
        persist_directory: str,
        embedding_function: Any = None,
        name: str = "default",
        **kwargs: Any,
    ):
        self.persist_directory = Path(persist_directory)
        self.embedding_function = embedding_function
        self.name = name
        self._vectorstore: Chroma | None = None
        # Optional callable that lazily provides an embedding function.
        self._lazy_embedding_getter: Callable[[], Any] | None = None

    # ------------------------------------------------------------------
    # VectorDatabaseInterface
    # ------------------------------------------------------------------

    def create_from_documents(self, documents: list[Document]) -> bool:
        if not documents:
            logger.warning(f"[{self.name}] No documents provided — skipping creation.")
            return False

        if not self._ensure_directory_writable():
            return False

        self._cleanup_corrupted_files()

        embedding_func = self._resolve_embedding()
        if embedding_func is None:
            logger.error(f"[{self.name}] Cannot create database: no embedding function provided.")
            return False

        for attempt in range(1, _MAX_CREATE_RETRIES + 1):
            try:
                self._vectorstore = Chroma.from_documents(
                    documents=documents,
                    embedding=embedding_func,
                    persist_directory=str(self.persist_directory),
                )
                logger.info(f"[{self.name}] Created with {len(documents)} documents.")
                return True
            except Exception as exc:
                logger.error(f"[{self.name}] Attempt {attempt}/{_MAX_CREATE_RETRIES} failed: {exc}")
                if attempt < _MAX_CREATE_RETRIES:
                    self._reset_directory()
                    time.sleep(1)

        return False

    def add_documents(self, documents: list[Document]) -> bool:
        if not documents:
            return True

        if not self._ensure_vectorstore():
            return False

        vs = self._vectorstore
        assert vs is not None
        try:
            vs.add_documents(documents)
            logger.info(f"[{self.name}] Added {len(documents)} documents.")
            return True
        except Exception as exc:
            logger.error(f"[{self.name}] Failed to add documents: {exc}")
            return False

    def delete_documents(self, filter_criteria: dict[str, Any]) -> bool:
        if not self._ensure_vectorstore():
            return False

        vs = self._vectorstore
        assert vs is not None
        try:
            vs._collection.delete(where=filter_criteria)
            logger.info(f"[{self.name}] Deleted documents matching: {filter_criteria}")
            return True
        except Exception as exc:
            logger.error(f"[{self.name}] Failed to delete documents: {exc}")
            return False

    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: dict | None = None,
    ) -> list[tuple[Document, float]]:
        if not self._ensure_vectorstore():
            return []

        vs = self._vectorstore
        assert vs is not None
        try:
            if filter_metadata:
                return vs.similarity_search_with_score(query, k=k, filter=filter_metadata)
            return vs.similarity_search_with_score(query, k=k)
        except Exception as exc:
            logger.error(f"[{self.name}] Search failed: {exc}")
            return []

    def clear(self) -> bool:
        try:
            self._release_vectorstore()
            if self.persist_directory.exists():
                shutil.rmtree(self.persist_directory)
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"[{self.name}] Cleared.")
            return True
        except Exception as exc:
            logger.error(f"[{self.name}] Failed to clear: {exc}")
            return False

    def exists(self) -> bool:
        return (self.persist_directory / _CHROMA_DB_FILE).exists()

    def get_stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {
            "name": self.name,
            "type": "ChromaDB",
            "exists": self.exists(),
            "directory": str(self.persist_directory),
            "directory_exists": self.persist_directory.exists(),
            "collection_count": self._get_collection_count(),
        }
        return stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_embedding(self) -> Any:
        """Return the embedding function, invoking the lazy getter if needed."""
        if self.embedding_function is None and self._lazy_embedding_getter is not None:
            self.embedding_function = self._lazy_embedding_getter()
        return self.embedding_function

    def _ensure_vectorstore(self) -> bool:
        """Load the vectorstore from disk if it is not already in memory.
        Returns True if the vectorstore is ready to use."""
        if self._vectorstore is not None:
            return True

        if not self.exists():
            logger.warning(f"[{self.name}] Database does not exist on disk.")
            return False

        embedding_func = self._resolve_embedding()
        if embedding_func is None:
            logger.warning(f"[{self.name}] Cannot load vectorstore: no embedding function provided.")
            return False

        try:
            self._vectorstore = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=embedding_func,
            )
            logger.info(f"[{self.name}] Loaded existing vectorstore.")
            return True
        except Exception as exc:
            logger.error(f"[{self.name}] Failed to load vectorstore: {exc}")
            return False

    def _release_vectorstore(self) -> None:
        """Safely release the in-memory vectorstore handle."""
        if self._vectorstore is None:
            return
        try:
            self._vectorstore.delete_collection()
        except Exception as exc:
            logger.warning(f"[{self.name}] Error releasing vectorstore: {exc}")
        finally:
            self._vectorstore = None

    def _ensure_directory_writable(self) -> bool:
        try:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            probe = self.persist_directory / f".write_probe_{int(time.time())}"
            probe.write_text("probe")
            probe.unlink()
            return True
        except Exception as exc:
            logger.error(f"[{self.name}] Directory '{self.persist_directory}' is not writable: {exc}")
            return False

    def _cleanup_corrupted_files(self) -> None:
        """Remove any Chroma WAL files that cannot be opened."""
        for filename in _CHROMA_WAL_FILES:
            path = self.persist_directory / filename
            if not path.exists():
                continue
            try:
                path.open("rb").read(1)
            except (PermissionError, OSError):
                try:
                    path.unlink()
                    logger.info(f"[{self.name}] Removed corrupted file: {path}")
                except Exception as exc:
                    logger.warning(f"[{self.name}] Could not remove corrupted file {path}: {exc}")

    def _reset_directory(self) -> None:
        """Wipe and recreate the persist directory between retry attempts."""
        try:
            if self.persist_directory.exists():
                shutil.rmtree(self.persist_directory)
            self.persist_directory.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning(f"[{self.name}] Directory reset failed: {exc}")

    def _get_collection_count(self) -> int | str:
        """Return document count using the least expensive available method."""
        if self._vectorstore is not None:
            try:
                return self._vectorstore._collection.count()
            except Exception as exc:
                return f"Error: {exc}"

        if not self.exists():
            return 0

        # Try reading count directly via chromadb client (no embedding needed).
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(self.persist_directory))
            collections = client.list_collections()
            return collections[0].count() if collections else 0
        except Exception:
            pass

        # Last resort: load the full vectorstore.
        if self._resolve_embedding() and self._ensure_vectorstore():
            vs = self._vectorstore
            if vs is not None:
                try:
                    return vs._collection.count()
                except Exception as exc:
                    return f"Error: {exc}"

        return "Not initialized (no embedding function)"
