"""
Backward-compatible re-export shim.
New code should import directly from vector_db_base or vector_db_chroma.
"""

from utils.vector_db_base import VectorDatabaseFactory, VectorDatabaseInterface
from utils.vector_db_chroma import ChromaVectorDatabase

__all__ = [
    "VectorDatabaseInterface",
    "VectorDatabaseFactory",
    "ChromaVectorDatabase",
]
