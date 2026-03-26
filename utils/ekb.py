"""
Generic embedding knowledge base system.
Converts various document types into a vector database for AI retrieval.
"""

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.doc_processor import CodeProcessor, DocumentProcessor, JSONProcessor, MarkdownProcessor, TextProcessor
from utils.gitignore import GitIgnoreChecker
from utils.logger import get_logger
from utils.regex_pattern_filter import FilterOrder, RegexPatternFilter
from utils.vector_db import VectorDatabaseFactory

logger = get_logger(name=__name__)


class EKBConfig:
    def __init__(
        self,
        name: str = "default",
        source_paths: Optional[list[str]] = None,
        vector_db_path: str = "data/vector_db",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        embedding_device: str = "cpu",
        chunk_size: int = 2000,
        chunk_overlap: int = 100,
        search_k: int = 10,
        rerank_top_k: int = 5,
        db_type: str = "chroma",
        debug_mode: bool = False,
        exclude_patterns: Optional[list[str]] = None,
        include_patterns: Optional[list[str]] = None,
        filter_order: FilterOrder = FilterOrder.EXCLUDE_FIRST,
        use_gitignore: bool = True,
    ):
        self.name = name
        self.source_paths = source_paths
        self.vector_db_path = vector_db_path
        self.embedding_model = embedding_model
        self.embedding_device = embedding_device
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.search_k = search_k
        self.rerank_top_k = rerank_top_k
        self.db_type = db_type
        self.debug_mode = debug_mode
        self.exclude_patterns = exclude_patterns
        self.include_patterns = include_patterns
        self.filter_order = filter_order
        self.use_gitignore = use_gitignore


class EmbeddingKnowledgeBase:
    """Generic embedding knowledge base manager."""

    def __init__(
        self,
        config: EKBConfig,
        custom_processors: Optional[list[DocumentProcessor]] = None,
    ):
        self.config = config

        if config.source_paths is None:
            raise ValueError("Source paths are required")

        self.source_paths = [
            Path(p) for p in (config.source_paths if isinstance(config.source_paths, list) else [config.source_paths])
        ]
        self.vector_db_path = Path(config.vector_db_path) / config.name
        self.vector_db_path.mkdir(parents=True, exist_ok=True)

        self.pattern_filter = RegexPatternFilter(
            exclude_patterns=config.exclude_patterns,
            include_patterns=config.include_patterns,
            filter_order=config.filter_order,
        )
        self.git_ignore_checker = GitIgnoreChecker(working_directory=Path.cwd()) if config.use_gitignore else None

        self.processors: list[DocumentProcessor] = [
            MarkdownProcessor(),
            TextProcessor(),
            JSONProcessor(),
            CodeProcessor(),
        ]
        if custom_processors:
            self.processors.extend(custom_processors)

        self._embeddings: Optional[HuggingFaceEmbeddings] = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        )

        self.db_type = config.db_type
        self.debug_mode = config.debug_mode

        self.vector_db = VectorDatabaseFactory.create_database(
            db_type=config.db_type,
            persist_directory=str(self.vector_db_path),
            embedding_function=None,
            name=config.name,
            debug_mode=config.debug_mode,
        )
        self.vector_db._lazy_embedding_getter = lambda: self.embeddings

        self.config_file = self.vector_db_path / "config.json"
        self.metadata_file = self.vector_db_path / "metadata.json"
        self._load_config()
        self._load_metadata()
        self._save_config()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        """Lazy-initialised embedding model."""
        if self._embeddings is None:
            logger.info(
                f"Initializing embedding model '{self.config.embedding_model}' "
                f"on device '{self.config.embedding_device}'"
            )
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.config.embedding_model,
                model_kwargs={"device": self.config.embedding_device},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embeddings

    # ------------------------------------------------------------------
    # Config / metadata persistence
    # ------------------------------------------------------------------

    def _load_metadata(self) -> None:
        self.metadata: dict[str, Any] = {}
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.warning(f"[{self.config.name}] Failed to load metadata: {e}")

    def _save_metadata(self) -> None:
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[{self.config.name}] Failed to save metadata: {e}")

    def _load_config(self) -> None:
        self.saved_config: dict[str, Any] = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.saved_config = json.load(f)
                logger.info(f"[{self.config.name}] Loaded config: {self.saved_config}")
            except Exception as e:
                logger.warning(f"[{self.config.name}] Failed to load config: {e}")
        else:
            logger.info(f"[{self.config.name}] No config file found, using defaults")

    def _save_config(self) -> None:
        new_config: dict[str, Any] = {
            "source_paths": [str(p) for p in self.source_paths],
            "exclude_patterns": self.config.exclude_patterns,
            "include_patterns": self.config.include_patterns,
            "filter_order": self.config.filter_order.value,
            "use_gitignore": self.config.use_gitignore,
        }

        if self.has_config_changed(**new_config):
            new_config["created_at"] = self.saved_config.get("created_at", datetime.now().isoformat())
            self._clear_database()
            self.metadata = {}
        else:
            new_config = copy.deepcopy(self.saved_config)
            new_config["updated_at"] = datetime.now().isoformat()

        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(new_config, f, ensure_ascii=False, indent=2)
            self.saved_config = new_config
            logger.info(f"[{self.config.name}] Saved config: {new_config}")
        except Exception as e:
            logger.warning(f"[{self.config.name}] Failed to save config: {e}")

    def has_config_changed(
        self,
        source_paths: Optional[list[str]] = None,
        exclude_patterns: Optional[list[str]] = None,
        include_patterns: Optional[list[str]] = None,
        filter_order: Optional[str] = None,
        use_gitignore: Optional[bool] = None,
        **_kwargs: Any,
    ) -> bool:
        """Return True if any supplied parameter differs from the saved config."""
        checks: list[tuple[Any, str, Any]] = [
            (source_paths, "source_paths", lambda a, b: set(a or []) != set(b or [])),
            (exclude_patterns, "exclude_patterns", lambda a, b: set(a or []) != set(b or [])),
            (include_patterns, "include_patterns", lambda a, b: set(a or []) != set(b or [])),
            (filter_order, "filter_order", lambda a, b: a != b),
            (use_gitignore, "use_gitignore", lambda a, b: a != b),
        ]

        changed = False
        for value, key, differs in checks:
            if value is None:
                continue
            saved = self.saved_config.get(key)
            if differs(value, saved):
                logger.info(f"[{self.config.name}] Config changed — {key}: {saved!r} -> {value!r}")
                changed = True

        return changed

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def _clear_database(self) -> None:
        if self.vector_db.clear():
            logger.info(f"[{self.config.name}] Database cleared.")
        else:
            logger.warning(f"[{self.config.name}] Failed to clear database.")

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------

    def _get_file_hash(self, file_path: Path) -> str:
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash {file_path}: {e}")
            return ""

    def _find_processor(self, file_path: Path) -> Optional[DocumentProcessor]:
        return next((p for p in self.processors if p.can_process(file_path)), None)

    def _should_ignore_file(self, file_path: Path, source_root: Path) -> bool:
        if self.git_ignore_checker and self.git_ignore_checker.is_available():
            if self.git_ignore_checker.should_ignore(file_path, source_root):
                logger.debug(f"Ignored by .gitignore: {file_path}")
                return True

        if not self.pattern_filter.should_include_file(file_path, source_root):
            logger.debug(f"Ignored by pattern filter: {file_path}")
            return True

        return False

    def _get_unique_file_key(self, file_path: Path) -> str:
        for i, source_path in enumerate(self.source_paths):
            try:
                return f"source_{i}:{file_path.relative_to(source_path)}"
            except ValueError:
                continue
        return f"absolute:{file_path}"

    def _get_display_source(self, file_path: Path) -> str:
        for source_path in self.source_paths:
            try:
                return str(file_path.relative_to(source_path))
            except ValueError:
                continue
        return str(file_path)

    def _should_update_file(self, file_path: Path) -> bool:
        file_key = self._get_unique_file_key(file_path)
        stored_hash = self.metadata.get(file_key, {}).get("hash", "")
        return self._get_file_hash(file_path) != stored_hash

    def get_supported_extensions(self) -> list[str]:
        extensions: set[str] = set()
        for processor in self.processors:
            if hasattr(processor, "supported_extensions"):
                se = getattr(processor, "supported_extensions")
                if callable(se):
                    extensions.update(se())
        extensions.update([".md", ".markdown", ".txt", ".text", ".json"])
        return list(extensions)

    # ------------------------------------------------------------------
    # Document building helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_metadata(raw: dict[str, Any]) -> dict[str, Any]:
        """Keep only metadata values that are ChromaDB-compatible scalars."""
        result: dict[str, Any] = {}
        for key, value in raw.items():
            if value is None or value == "":
                continue
            result[key] = value if isinstance(value, (str, int, float, bool)) else str(value)
        return result

    def _build_documents_from_parsed(
        self,
        parsed_content: dict[str, Any],
        file_path: Path,
        chunks: list[str],
    ) -> list[Document]:
        """Convert chunks from a processed file into Document objects."""
        file_key = self._get_unique_file_key(file_path)
        display_source = self._get_display_source(file_path)
        documents: list[Document] = []

        tags_str = ", ".join(str(t) for t in parsed_content.get("tags", []) if parsed_content.get("tags"))
        cats_str = ", ".join(str(c) for c in parsed_content.get("categories", []) if parsed_content.get("categories"))

        header = f"Title: {parsed_content['title']}\n"
        if tags_str:
            header += f"Tags: {tags_str}\n"
        if cats_str:
            header += f"Categories: {cats_str}\n"
        if parsed_content.get("author"):
            header += f"Author: {parsed_content['author']}\n"
        header += "\n"

        for i, chunk in enumerate(chunks):
            try:
                base_metadata: dict[str, Any] = {
                    "source": display_source,
                    "file_key": file_key,
                    "title": str(parsed_content["title"]),
                    "date": str(parsed_content.get("date", "")),
                    "tags": tags_str,
                    "categories": cats_str,
                    "author": str(parsed_content.get("author", "")),
                    "description": str(parsed_content.get("description", "")),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "file_path": str(file_path),
                    "file_type": file_path.suffix.lower(),
                }
                for key, value in parsed_content.get("metadata", {}).items():
                    if key not in base_metadata and isinstance(value, (str, int, float, bool)):
                        base_metadata[key] = value

                documents.append(
                    Document(
                        page_content=header + chunk,
                        metadata=self._filter_metadata(base_metadata),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to build document for {file_path} chunk {i}: {e}")

        return documents

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_documents_from_texts(
        self,
        texts: list[str],
        metadatas: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Add documents directly from text strings."""
        if metadatas is None:
            metadatas = [{}] * len(texts)

        new_documents: list[Document] = []
        for i, (text, metadata) in enumerate(zip(texts, metadatas)):
            chunks = self.text_splitter.split_text(text)
            for j, chunk in enumerate(chunks):
                raw = {
                    "source": metadata.get("source", f"text_input_{i}"),
                    "title": metadata.get("title", f"Document {i + 1}"),
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                    **metadata,
                }
                new_documents.append(Document(page_content=chunk, metadata=self._filter_metadata(raw)))

        if new_documents:
            if not self.vector_db.exists():
                self.vector_db.create_from_documents(new_documents)
            else:
                self.vector_db.add_documents(new_documents)

        return {
            "success": True,
            "message": f"Added {len(texts)} text documents",
            "new_documents_count": len(new_documents),
        }

    def update_knowledge_base(self, file_patterns: Optional[list[str]] = None) -> dict[str, Any]:
        """Update knowledge base from source paths."""
        logger.info(f"[{self.config.name}] Starting knowledge base update")

        all_files: list[Path] = []
        for source_path in self.source_paths:
            if not source_path.exists():
                logger.warning(f"Source path does not exist: {source_path}")
                continue

            if source_path.is_file():
                if not self._should_ignore_file(source_path, source_path.parent):
                    all_files.append(source_path)
            else:
                patterns = file_patterns or ["*.md", "*.txt", "*.json", "*.markdown"]
                for pattern in patterns:
                    found_files = list(source_path.rglob(pattern))

                    if len(found_files) > 5:
                        git_ignore_results: dict[str, bool] = {}
                        if self.git_ignore_checker and self.git_ignore_checker.is_available():
                            git_ignore_results = self.git_ignore_checker.check_multiple_files(found_files, source_path)
                        pattern_results = self.pattern_filter.check_multiple_files(found_files, source_path)

                        for fp in found_files:
                            key = str(fp)
                            if git_ignore_results.get(key, False):
                                logger.debug(f"Ignored by .gitignore: {fp}")
                                continue
                            if not pattern_results.get(key, False):
                                logger.debug(f"Ignored by pattern filter: {fp}")
                                continue
                            all_files.append(fp)
                    else:
                        for fp in found_files:
                            if not self._should_ignore_file(fp, source_path):
                                all_files.append(fp)

        logger.info(f"[{self.config.name}] Found {len(all_files)} files")

        updated_files: list[str] = []
        new_documents: list[Document] = []

        for file_path in all_files:
            if not self._should_update_file(file_path):
                continue

            processor = self._find_processor(file_path)
            if processor is None:
                logger.warning(f"No processor for: {file_path}")
                continue

            logger.info(f"Processing: {file_path}")
            parsed_content = processor.process(file_path)
            chunks = self.text_splitter.split_text(parsed_content["content"])
            new_documents.extend(self._build_documents_from_parsed(parsed_content, file_path, chunks))

            file_key = self._get_unique_file_key(file_path)
            self.metadata[file_key] = {
                "hash": self._get_file_hash(file_path),
                "last_updated": datetime.now().isoformat(),
                "title": parsed_content["title"],
                "chunks_count": len(chunks),
                "file_type": file_path.suffix.lower(),
                "file_path": str(file_path),
                "display_source": self._get_display_source(file_path),
            }
            updated_files.append(file_key)

        if new_documents:
            if not self.vector_db.exists():
                success = self.vector_db.create_from_documents(new_documents)
            else:
                for file_key in updated_files:
                    if not self.vector_db.delete_documents({"file_key": file_key}):
                        logger.warning(f"[{self.config.name}] Failed to delete old docs for {file_key}")
                success = self.vector_db.add_documents(new_documents)

            if not success:
                return {
                    "success": False,
                    "message": f"Failed to update vector database '{self.config.name}'",
                    "updated_files": updated_files,
                    "new_documents_count": 0,
                    "total_files_processed": len(all_files),
                }

            self._save_metadata()
            logger.info(
                f"[{self.config.name}] Update complete — {len(updated_files)} files, {len(new_documents)} chunks"
            )

        return {
            "success": True,
            "message": f"Knowledge base '{self.config.name}' update completed",
            "updated_files": updated_files,
            "new_documents_count": len(new_documents),
            "total_files_processed": len(all_files),
        }

    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Search the knowledge base and return ranked results."""
        if not self.vector_db.exists():
            return []

        try:
            initial_k = max(k * 2, self.config.search_k)
            docs = self.vector_db.search(query, k=initial_k, filter_metadata=filter_metadata)

            results = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                    "relevance_score": self._calculate_relevance_score(query, doc, score),
                }
                for doc, score in docs
            ]
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            return results[:k]
        except Exception as e:
            logger.error(f"[{self.config.name}] Search failed: {e}")
            return []

    def _calculate_relevance_score(self, query: str, doc: Document, vector_score: float) -> float:
        """Combine vector similarity with keyword/title/metadata signals."""
        try:
            content = doc.page_content.lower()
            query_lower = query.lower()
            query_words = query_lower.split()
            metadata = doc.metadata

            base_score = 1.0 / (1.0 + vector_score)

            matched_words = sum(1 for w in query_words if w in content)
            keyword_score = matched_words / len(query_words) if query_words else 0.0

            title = metadata.get("title", "").lower()
            if title and query_lower in title:
                title_score = 2.0
            else:
                title_score = sum(0.5 for w in query_words if w in title)

            metadata_score = 0.0
            for field in ("tags", "categories", "author", "description"):
                field_val = metadata.get(field, "").lower()
                if not field_val:
                    continue
                if query_lower in field_val:
                    metadata_score += 1.0
                else:
                    metadata_score += sum(0.3 for w in query_words if w in field_val)

            return base_score * 0.4 + keyword_score * 0.3 + title_score * 0.2 + metadata_score * 0.1

        except Exception as e:
            logger.warning(f"Failed to calculate relevance score: {e}")
            return 1.0 / (1.0 + vector_score)

    def get_stats(self) -> dict[str, Any]:
        if not self.vector_db.exists():
            return {"total_documents": 0, "total_files": 0}

        try:
            db_stats = self.vector_db.get_stats()
            file_types: dict[str, int] = {}
            for meta in self.metadata.values():
                ft = meta.get("file_type", "unknown")
                file_types[ft] = file_types.get(ft, 0) + 1

            return {
                "name": self.config.name,
                "total_documents": db_stats.get("collection_count", 0),
                "total_files": len(self.metadata),
                "file_types": file_types,
                "source_paths": [str(p) for p in self.source_paths],
                "vector_db_path": str(self.vector_db_path),
                "supported_extensions": self.get_supported_extensions(),
                "last_updated": max(
                    (meta.get("last_updated", "") for meta in self.metadata.values()),
                    default="",
                ),
            }
        except Exception as e:
            logger.error(f"[{self.config.name}] Failed to get stats: {e}")
            return {"error": str(e)}

    def get_database_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "name": self.config.name,
            "db_type": self.db_type,
            "debug_mode": self.debug_mode,
            "vector_db_path": str(self.vector_db_path),
            "database_exists": self.vector_db.exists(),
        }
        try:
            info.update(self.vector_db.get_stats())
        except Exception as e:
            info["db_stats_error"] = str(e)
        return info

    def switch_database_backend(self, new_db_type: str, debug_mode: Optional[bool] = None) -> bool:
        """Switch to a different vector database backend."""
        try:
            if debug_mode is not None:
                self.debug_mode = debug_mode

            logger.info(f"[{self.config.name}] Switching backend: '{self.db_type}' -> '{new_db_type}'")

            new_vector_db = VectorDatabaseFactory.create_database(
                db_type=new_db_type,
                persist_directory=str(self.vector_db_path),
                embedding_function=None,
                name=self.config.name,
                debug_mode=self.debug_mode,
            )
            new_vector_db._lazy_embedding_getter = lambda: self.embeddings

            self.db_type = new_db_type
            self.vector_db = new_vector_db
            logger.info(f"[{self.config.name}] Switched to '{new_db_type}' backend.")
            return True

        except Exception as e:
            logger.error(f"[{self.config.name}] Failed to switch backend: {e}")
            return False
