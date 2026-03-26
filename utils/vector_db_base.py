"""
Vector Database Abstraction Layer
Public interfaces and factory — import from here in application code.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, cast

from langchain_core.documents import Document


class VectorDatabaseInterface(ABC):
    """Abstract interface for vector database backends."""

    _lazy_embedding_getter: Callable[[], Any] | None = None

    @abstractmethod
    def create_from_documents(self, documents: list[Document]) -> bool:
        """Create (or recreate) the database from a list of documents."""

    @abstractmethod
    def add_documents(self, documents: list[Document]) -> bool:
        """Append documents to an existing database."""

    @abstractmethod
    def delete_documents(self, filter_criteria: dict[str, Any]) -> bool:
        """Delete documents whose metadata matches *filter_criteria*."""

    @abstractmethod
    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: dict | None = None,
    ) -> list[tuple[Document, float]]:
        """Return the *k* most similar documents together with their scores."""

    @abstractmethod
    def clear(self) -> bool:
        """Remove all data from the database."""

    @abstractmethod
    def exists(self) -> bool:
        """Return True if the database has been persisted to disk."""

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Return a dictionary of database statistics."""


class VectorDatabaseFactory:
    """Factory for creating VectorDatabaseInterface instances."""

    _REGISTRY: dict[str, type[VectorDatabaseInterface]] = {}

    @classmethod
    def register(cls, db_type: str, implementation: type[VectorDatabaseInterface]) -> None:
        """Register a new backend under *db_type* (case-insensitive)."""
        cls._REGISTRY[db_type.lower()] = implementation

    @staticmethod
    def create_database(
        db_type: str,
        persist_directory: str,
        embedding_function: Any = None,
        name: str = "default",
        **kwargs,
    ) -> VectorDatabaseInterface:
        """Instantiate and return a vector database of the requested type."""
        from utils.vector_db_chroma import ChromaVectorDatabase  # local import to avoid circular deps

        registry: dict[str, type[VectorDatabaseInterface]] = {
            "chroma": ChromaVectorDatabase,
        }
        registry.update(VectorDatabaseFactory._REGISTRY)

        key = db_type.lower()
        if key not in registry:
            raise ValueError(f"Unsupported database type: '{db_type}'. Available: {list(registry)}")

        ctor = cast(Callable[..., VectorDatabaseInterface], registry[key])
        return ctor(
            persist_directory=persist_directory,
            embedding_function=embedding_function,
            name=name,
            **kwargs,
        )

    @staticmethod
    def get_available_types() -> list[str]:
        """Return the list of registered backend names."""
        return ["chroma"] + list(VectorDatabaseFactory._REGISTRY)
