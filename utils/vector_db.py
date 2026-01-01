"""
Vector Database Abstraction Layer
Provides a unified interface for different vector database backends
"""

import shutil
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from langchain_core.documents import Document

from utils.logger import get_logger

logger = get_logger(name=__name__)


class VectorDatabaseInterface(ABC):
    """Abstract interface for vector databases"""

    @abstractmethod
    def create_from_documents(self, documents: List[Document]) -> bool:
        """Create database from documents"""

    @abstractmethod
    def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to existing database"""

    @abstractmethod
    def delete_documents(self, filter_criteria: Dict[str, Any]) -> bool:
        """Delete documents matching criteria"""

    @abstractmethod
    def search(self, query: str, k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Tuple[Document, float]]:
        """Search for similar documents"""

    @abstractmethod
    def clear(self) -> bool:
        """Clear all data from database"""

    @abstractmethod
    def exists(self) -> bool:
        """Check if database exists"""

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""


class ChromaVectorDatabase(VectorDatabaseInterface):
    """ChromaDB implementation of vector database"""

    def __init__(
        self,
        persist_directory: str,
        embedding_function: Any = None,
        name: str = "default",
    ):
        self.persist_directory = Path(persist_directory)
        self.embedding_function = embedding_function
        self.name = name
        self.vectorstore = None

    def _ensure_directory_writable(self) -> bool:
        """Ensure database directory is writable"""
        try:
            self.persist_directory.mkdir(parents=True, exist_ok=True)

            # Test write permission
            test_file = self.persist_directory / f".test_write_{int(time.time())}"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Directory '{self.persist_directory}' is not writable: {e}")
            return False

    def _cleanup_corrupted_files(self) -> bool:
        """Clean up potentially corrupted database files"""
        try:
            corrupted_files = []
            chroma_files = ["chroma.sqlite3", "chroma.sqlite3-shm", "chroma.sqlite3-wal"]

            for filename in chroma_files:
                file_path = self.persist_directory / filename
                if file_path.exists():
                    try:
                        with open(file_path, "rb") as f:
                            f.read(1)
                    except (PermissionError, OSError):
                        corrupted_files.append(file_path)

            for file_path in corrupted_files:
                try:
                    file_path.unlink()
                    logger.info(f"Removed corrupted database file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not remove corrupted file {file_path}: {e}")
                    return False

            return True
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            return False

    def _load_existing_vectorstore(self) -> bool:
        """Load existing vectorstore from disk"""
        if self.vectorstore is not None:
            return True

        if not self.exists():
            return False

        # Get embedding function, using lazy getter if available
        embedding_func = self.embedding_function
        if embedding_func is None and hasattr(self, "_lazy_embedding_getter"):
            embedding_func = self._lazy_embedding_getter()
            self.embedding_function = embedding_func

        if embedding_func is None:
            logger.warning(f"Cannot load vectorstore for '{self.name}': no embedding function provided")
            return False

        try:
            self.vectorstore = Chroma(
                persist_directory=str(self.persist_directory), embedding_function=embedding_func
            )
            logger.info(f"Loaded existing vectorstore for '{self.name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to load existing vectorstore for '{self.name}': {e}")
            return False

    def create_from_documents(self, documents: List[Document]) -> bool:
        """Create database from documents"""
        if not documents:
            logger.warning(f"No documents provided for database creation '{self.name}'")
            return False

        if not self._ensure_directory_writable():
            return False

        self._cleanup_corrupted_files()

        # Get embedding function, using lazy getter if available
        embedding_func = self.embedding_function
        if embedding_func is None and hasattr(self, "_lazy_embedding_getter"):
            embedding_func = self._lazy_embedding_getter()
            self.embedding_function = embedding_func

        if embedding_func is None:
            logger.error(f"Cannot create database '{self.name}': no embedding function provided")
            return False

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.vectorstore = Chroma.from_documents(
                    documents=documents,
                    embedding=embedding_func,
                    persist_directory=str(self.persist_directory),
                )
                logger.info(f"Created vector database '{self.name}' with {len(documents)} documents")
                return True

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed to create database '{self.name}': {e}")

                if attempt < max_retries - 1:
                    try:
                        if self.persist_directory.exists():
                            shutil.rmtree(self.persist_directory)
                        self.persist_directory.mkdir(parents=True, exist_ok=True)
                        time.sleep(1)
                    except Exception as cleanup_error:
                        logger.warning(f"Cleanup failed: {cleanup_error}")

        return False

    def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to existing database"""
        if not documents:
            return True

        # Ensure vectorstore is loaded
        if self.vectorstore is None:
            if not self._load_existing_vectorstore():
                logger.error(f"Cannot add documents: vectorstore not initialized for '{self.name}'")
                return False

        try:
            self.vectorstore.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to '{self.name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to add documents to '{self.name}': {e}")
            return False

    def delete_documents(self, filter_criteria: Dict[str, Any]) -> bool:
        """Delete documents matching criteria"""
        # Ensure vectorstore is loaded
        if self.vectorstore is None:
            if not self._load_existing_vectorstore():
                logger.error(f"Cannot delete documents: vectorstore not initialized for '{self.name}'")
                return False

        try:
            collection = self.vectorstore._collection
            collection.delete(where=filter_criteria)
            logger.info(f"Deleted documents from '{self.name}' with filter: {filter_criteria}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents from '{self.name}': {e}")
            return False

    def search(self, query: str, k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Tuple[Document, float]]:
        """Search for similar documents"""
        # Ensure vectorstore is loaded
        if self.vectorstore is None:
            if not self._load_existing_vectorstore():
                logger.warning(f"Cannot search: vectorstore not initialized for '{self.name}'")
                return []

        try:
            if filter_metadata:
                results = self.vectorstore.similarity_search_with_score(query, k=k, filter=filter_metadata)
            else:
                results = self.vectorstore.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Search failed in '{self.name}': {e}")
            return []

    def clear(self) -> bool:
        """Clear all data from database"""
        try:
            if self.vectorstore is not None:
                try:
                    if hasattr(self.vectorstore, "_collection"):
                        self.vectorstore._collection = None
                    if hasattr(self.vectorstore, "_client"):
                        self.vectorstore._client = None
                except Exception as e:
                    logger.warning(f"Error closing vectorstore connection: {e}")
                finally:
                    self.vectorstore = None

            if self.persist_directory.exists():
                shutil.rmtree(self.persist_directory)
                logger.info(f"Cleared database '{self.name}'")
                self.persist_directory.mkdir(parents=True, exist_ok=True)

            return True
        except Exception as e:
            logger.error(f"Failed to clear database '{self.name}': {e}")
            return False

    def exists(self) -> bool:
        """Check if database exists"""
        chroma_db_file = self.persist_directory / "chroma.sqlite3"
        return chroma_db_file.exists()

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {
            "name": self.name,
            "type": "ChromaDB",
            "exists": self.exists(),
            "directory": str(self.persist_directory),
            "directory_exists": self.persist_directory.exists(),
        }

        # Try to get collection count without loading embedding model
        if self.vectorstore is not None:
            try:
                collection = self.vectorstore._collection
                stats["collection_count"] = collection.count()
            except Exception as e:
                stats["collection_count"] = f"Error: {e}"
        elif self.exists():
            # Try to get count directly from ChromaDB without embedding function
            try:
                import chromadb
                client = chromadb.PersistentClient(path=str(self.persist_directory))
                # Try to list all collections and get the first one
                collections = client.list_collections()
                if collections:
                    # Use the first collection found
                    collection = collections[0]
                    stats["collection_count"] = collection.count()
                else:
                    stats["collection_count"] = 0
            except Exception as e:
                # Fallback: try loading with embedding function if available
                if self.embedding_function is not None:
                    try:
                        if self._load_existing_vectorstore():
                            collection = self.vectorstore._collection
                            stats["collection_count"] = collection.count()
                        else:
                            stats["collection_count"] = "Not initialized"
                    except Exception as load_error:
                        stats["collection_count"] = f"Error: {load_error}"
                else:
                    stats["collection_count"] = "Not initialized (no embedding function)"
        else:
            stats["collection_count"] = 0

        return stats


class VectorDatabaseFactory:
    """Factory for creating vector database instances"""

    @staticmethod
    def create_database(
        db_type: str,
        persist_directory: str,
        embedding_function: Any = None,
        name: str = "default",
        **kwargs,
    ) -> VectorDatabaseInterface:
        """Create a vector database instance"""

        if db_type.lower() == "chroma":
            return ChromaVectorDatabase(
                persist_directory=persist_directory,
                embedding_function=embedding_function,
                name=name,
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    @staticmethod
    def get_available_types() -> List[str]:
        """Get list of available database types"""
        return ["chroma"]
