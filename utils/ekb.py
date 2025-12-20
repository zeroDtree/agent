"""
Generic embedding knowledge base system
Convert various document types to vector database for AI retrieval
"""

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

from utils.doc_processor import CodeProcessor, DocumentProcessor, JSONProcessor, MarkdownProcessor, TextProcessor
from utils.gitignore import GitIgnoreChecker
from utils.regex_pattern_filter import FilterOrder, RegexPatternFilter
from utils.vector_db import VectorDatabaseFactory


class EKBConfig:
    def __init__(
        self,
        name: str = "default",
        source_paths: Optional[List[str]] = None,
        vector_db_path: str = "data/vector_db",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        chunk_size: int = 2000,
        chunk_overlap: int = 100,
        search_k: int = 10,
        rerank_top_k: int = 5,
        db_type: str = "chroma",
        debug_mode: bool = False,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        filter_order: FilterOrder = FilterOrder.EXCLUDE_FIRST,
        use_gitignore: bool = True,
    ):
        self.name = name
        self.source_paths = source_paths
        self.vector_db_path = vector_db_path
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.search_k = search_k
        self.rerank_top_k = rerank_top_k
        self.db_type = db_type
        self.debug_mode = debug_mode
        # filter
        self.exclude_patterns = exclude_patterns
        self.include_patterns = include_patterns
        self.filter_order = filter_order
        self.use_gitignore = use_gitignore


class EmbeddingKnowledgeBase:
    """Generic embedding knowledge base manager"""

    def __init__(
        self,
        config: EKBConfig,
        custom_processors: Optional[List[DocumentProcessor]] = None,
    ):
        self.config = config

        # Initialize source paths - will be updated from saved config if available
        if self.config.source_paths is not None:
            self.source_paths = [
                Path(p)
                for p in (
                    self.config.source_paths
                    if isinstance(self.config.source_paths, list)
                    else [self.config.source_paths]
                )
            ]
        else:
            raise ValueError("Source paths are required")
        self.vector_db_path = Path(self.config.vector_db_path) / self.config.name
        self.vector_db_path.mkdir(parents=True, exist_ok=True)

        self.pattern_filter = RegexPatternFilter(
            exclude_patterns=self.config.exclude_patterns,
            include_patterns=self.config.include_patterns,
            filter_order=self.config.filter_order,
        )
        self.git_ignore_checker = GitIgnoreChecker(working_directory=Path.cwd()) if self.config.use_gitignore else None

        self.processors = [
            MarkdownProcessor(),
            TextProcessor(),
            JSONProcessor(),
            CodeProcessor(),
        ]
        if custom_processors:
            self.processors.extend(custom_processors)

        # Initialize embedding model
        embedding_model = self.config.embedding_model
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        chunk_size = self.config.chunk_size
        chunk_overlap = self.config.chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        )

        # Store database configuration
        self.db_type = self.config.db_type
        self.debug_mode = self.config.debug_mode

        # Initialize vector database using abstraction layer
        self.vector_db = VectorDatabaseFactory.create_database(
            db_type=self.config.db_type,
            persist_directory=str(self.vector_db_path),
            embedding_function=self.embeddings,
            name=self.config.name,
            debug_mode=self.config.debug_mode,
        )

        # Configuration and metadata file path
        self.config_file = self.vector_db_path / "config.json"
        self.metadata_file = self.vector_db_path / "metadata.json"
        self._load_config()
        self._load_metadata()

        self._save_config()

    def _load_metadata(self):
        """Load metadata"""
        self.metadata = {}
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except Exception as e:
                print(f"Failed to load metadata for '{self.config.name}': {e}")
                self.metadata = {}

    def _save_metadata(self):
        """Save metadata"""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save metadata for '{self.config.name}': {e}")

    def _load_config(self):
        """Load configuration from file"""
        self.saved_config = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.saved_config = json.load(f)
                print(f"Loaded config for '{self.config.name}': {self.saved_config}")
            except Exception as e:
                print(f"Failed to load config for '{self.config.name}': {e}")
                self.saved_config = {}
        else:
            print(f"No config file found for '{self.config.name}', using defaults")

    def _clear_database(self):
        """Clear database using abstraction layer"""
        try:
            if self.vector_db.clear():
                print(f"Successfully cleared database '{self.config.name}'")
            else:
                print(f"Failed to clear database '{self.config.name}'")
        except Exception as e:
            print(f"Failed to clear database for '{self.config.name}': {e}")

    def _save_config(self):
        """Save current configuration to file"""
        config = {
            "source_paths": [str(p) for p in self.source_paths],
            "exclude_patterns": self.config.exclude_patterns,
            "include_patterns": self.config.include_patterns,
            "filter_order": self.config.filter_order.value,
            "use_gitignore": self.config.use_gitignore,
        }
        if self.has_config_changed(**config):
            config["created_at"] = self.saved_config.get("created_at", datetime.now().isoformat())
            self._clear_database()
            self.metadata = {}
        else:
            config = copy.deepcopy(self.saved_config)
            config["updated_at"] = datetime.now().isoformat()
        try:
            if not self.config_file.parent.exists():
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.config_file.exists():
                self.config_file.touch()
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.saved_config = config
            print(f"Saved config for '{self.config.name}': {config}")
        except Exception as e:
            print(f"Failed to save config for '{self.config.name}': {e}")

    def has_config_changed(
        self,
        source_paths: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        filter_order: Optional[FilterOrder] = None,
        use_gitignore: Optional[bool] = None,
    ) -> bool:
        """Check if any configuration parameter has changed from saved config"""
        changed = False

        # Check source paths
        if source_paths is not None and source_paths:
            saved_paths = self.saved_config.get("source_paths", [])
            if set(source_paths) != set(saved_paths):
                print(f"Source paths changed: {saved_paths} -> {source_paths}")
                changed = True

        # Check exclude patterns
        if exclude_patterns is not None and exclude_patterns:
            saved_excludes = self.saved_config.get("exclude_patterns", [])
            if set(exclude_patterns) != set(saved_excludes):
                print(f"Exclude patterns changed: {saved_excludes} -> {exclude_patterns}")
                changed = True

        # Check include patterns
        if include_patterns is not None and include_patterns:
            saved_includes = self.saved_config.get("include_patterns", [])
            if set(include_patterns) != set(saved_includes):
                print(f"Include patterns changed: {saved_includes} -> {include_patterns}")
                changed = True

        # Check filter order
        if filter_order is not None:
            saved_order = self.saved_config.get("filter_order", "exclude_first")
            if filter_order != saved_order:
                print(f"Filter order changed: {saved_order} -> {filter_order.value}")
                changed = True

        # Check gitignore setting
        if use_gitignore is not None:
            saved_gitignore = self.saved_config.get("use_gitignore", True)
            if use_gitignore != saved_gitignore:
                print(f"Gitignore setting changed: {saved_gitignore} -> {use_gitignore}")
                changed = True

        return changed

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate file hash"""
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            print(f"Failed to calculate file hash {file_path}: {e}")
            return ""

    def _find_processor(self, file_path: Path) -> Optional[DocumentProcessor]:
        """Find appropriate processor for file"""
        for processor in self.processors:
            if processor.can_process(file_path):
                return processor
        return None

    def _should_ignore_file(self, file_path: Path, source_root: Path) -> bool:
        """Check if file should be ignored using both gitignore and regex pattern filters"""
        # Step 1: Check gitignore if enabled (independent filtering)
        if self.git_ignore_checker and self.git_ignore_checker.is_available():
            if self.git_ignore_checker.should_ignore(file_path, source_root):
                print(f"File ignored by .gitignore: {file_path}")
                return True

        # Step 2: Check include/exclude patterns (independent filtering)
        should_include = self.pattern_filter.should_include_file(file_path, source_root)

        if not should_include:
            print(f"File ignored by include/exclude patterns: {file_path}")
            return True

        return False

    def _get_unique_file_key(self, file_path: Path) -> str:
        """Get unique key for file across all source paths"""
        # Try to find which source path this file belongs to
        for i, source_path in enumerate(self.source_paths):
            try:
                relative_path = str(file_path.relative_to(source_path))
                return f"source_{i}:{relative_path}"
            except ValueError:
                continue

        # If file doesn't belong to any source path, use absolute path
        return f"absolute:{str(file_path)}"

    def _should_update_file(self, file_path: Path) -> bool:
        """Check if file needs to be updated"""
        file_hash = self._get_file_hash(file_path)
        file_key = self._get_unique_file_key(file_path)

        if file_key not in self.metadata:
            return True

        stored_hash = self.metadata[file_key].get("hash", "")
        return file_hash != stored_hash

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        extensions = set()
        for processor in self.processors:
            if hasattr(processor, "supported_extensions"):
                extensions.update(processor.supported_extensions())

        # Default extensions
        default_extensions = [".md", ".markdown", ".txt", ".text", ".json"]
        extensions.update(default_extensions)
        return list(extensions)

    def add_documents_from_texts(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Add documents directly from text strings"""
        if metadatas is None:
            metadatas = [{}] * len(texts)

        new_documents = []
        for i, (text, metadata) in enumerate(zip(texts, metadatas)):
            # Split text into chunks
            chunks = self.text_splitter.split_text(text)

            for j, chunk in enumerate(chunks):
                # Create enhanced metadata
                enhanced_metadata = {
                    "source": metadata.get("source", f"text_input_{i}"),
                    "title": metadata.get("title", f"Document {i+1}"),
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                    **metadata,
                }

                # Filter metadata to ensure compatibility
                filtered_metadata = {}
                for key, value in enhanced_metadata.items():
                    if value is None:
                        continue
                    elif isinstance(value, (str, int, float, bool)):
                        filtered_metadata[key] = value
                    else:
                        filtered_metadata[key] = str(value)

                doc = Document(page_content=chunk, metadata=filtered_metadata)
                new_documents.append(doc)

        # Add to vector database using abstraction layer
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

    def update_knowledge_base(self, file_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """Update knowledge base from source paths"""
        print(f"Starting knowledge base '{self.config.name}' update")

        # Collect all files from source paths
        all_files = []
        for source_path in self.source_paths:
            if not source_path.exists():
                print(f"Source path does not exist: {source_path}")
                continue

            if source_path.is_file():
                # Check if single file should be ignored
                if not self._should_ignore_file(source_path, source_path.parent):
                    all_files.append(source_path)
                else:
                    print(f"Ignoring file due to ignore patterns: {source_path}")
            else:
                # Scan directory for supported files
                patterns = file_patterns or ["*.md", "*.txt", "*.json", "*.markdown"]
                for pattern in patterns:
                    found_files = list(source_path.rglob(pattern))

                    # Use batch checking for better performance with both
                    # filters
                    if len(found_files) > 5:
                        # Batch check with gitignore if available
                        git_ignore_results = {}
                        if self.git_ignore_checker and self.git_ignore_checker.is_available():
                            git_ignore_results = self.git_ignore_checker.check_multiple_files(found_files, source_path)

                        # Batch check with include/exclude patterns
                        pattern_include_results = self.pattern_filter.check_multiple_files(found_files, source_path)

                        for file_path in found_files:
                            # Check gitignore first
                            if git_ignore_results.get(str(file_path), False):
                                print(f"File ignored by .gitignore: {file_path}")
                                continue

                            # Check include/exclude patterns
                            if not pattern_include_results.get(str(file_path), False):
                                print(f"File ignored by include/exclude patterns: {file_path}")
                                continue

                            all_files.append(file_path)
                    else:
                        # Individual checking for smaller sets
                        for file_path in found_files:
                            if not self._should_ignore_file(file_path, source_path):
                                all_files.append(file_path)
                            else:
                                print(f"File ignored by filters: {file_path}")

        print(f"Found {len(all_files)} files")

        updated_files = []
        new_documents = []

        for file_path in all_files:
            if not self._should_update_file(file_path):
                continue

            processor = self._find_processor(file_path)
            if processor is None:
                print(f"No processor found for file: {file_path}")
                continue

            print(f"Processing file: {file_path}")

            # Process file
            parsed_content = processor.process(file_path)

            # Split text
            chunks = self.text_splitter.split_text(parsed_content["content"])

            # Create document objects
            for i, chunk in enumerate(chunks):
                try:
                    # Get unique file key and display-friendly source path
                    file_key = self._get_unique_file_key(file_path)

                    # Get relative path for display (prefer first matching
                    # source)
                    display_source = None
                    for source_path in self.source_paths:
                        try:
                            display_source = str(file_path.relative_to(source_path))
                            break
                        except ValueError:
                            continue
                    if display_source is None:
                        display_source = str(file_path)

                    # Process metadata
                    metadata = {
                        "source": display_source,
                        "file_key": file_key,  # Add unique key for internal tracking
                        "title": str(parsed_content["title"]),
                        "date": str(parsed_content.get("date", "")),
                        "tags": (
                            ", ".join(str(tag) for tag in parsed_content.get("tags", []))
                            if parsed_content.get("tags")
                            else ""
                        ),
                        "categories": (
                            ", ".join(str(cat) for cat in parsed_content.get("categories", []))
                            if parsed_content.get("categories")
                            else ""
                        ),
                        "author": str(parsed_content.get("author", "")),
                        "description": str(parsed_content.get("description", "")),
                        "chunk_index": int(i),
                        "total_chunks": int(len(chunks)),
                        "file_path": str(file_path),
                        "file_type": file_path.suffix.lower(),
                    }

                    # Add custom metadata from file
                    if "metadata" in parsed_content:
                        for key, value in parsed_content["metadata"].items():
                            if key not in metadata and isinstance(value, (str, int, float, bool)):
                                metadata[key] = value

                    # Filter metadata
                    filtered_metadata = {}
                    for key, value in metadata.items():
                        if value is None or value == "":
                            continue
                        elif isinstance(value, (str, int, float, bool)):
                            filtered_metadata[key] = value
                        else:
                            filtered_metadata[key] = str(value)

                    # Enhanced content with metadata
                    enhanced_content = f"Title: {parsed_content['title']}\n"
                    if parsed_content.get("tags"):
                        enhanced_content += f"Tags: {', '.join(str(tag) for tag in parsed_content['tags'])}\n"
                    if parsed_content.get("categories"):
                        enhanced_content += (
                            f"Categories: {', '.join(str(cat) for cat in parsed_content['categories'])}\n"
                        )
                    if parsed_content.get("author"):
                        enhanced_content += f"Author: {parsed_content['author']}\n"
                    enhanced_content += f"\n{chunk}"

                    doc = Document(page_content=enhanced_content, metadata=filtered_metadata)
                    new_documents.append(doc)

                except Exception as e:
                    print(f"Failed to create document {file_path} chunk {i}: {e}")
                    continue

            # Update metadata using unique file key
            file_key = self._get_unique_file_key(file_path)

            self.metadata[file_key] = {
                "hash": self._get_file_hash(file_path),
                "last_updated": datetime.now().isoformat(),
                "title": parsed_content["title"],
                "chunks_count": len(chunks),
                "file_type": file_path.suffix.lower(),
                "file_path": str(file_path),  # Store full path for reference
                "display_source": display_source,  # Store display-friendly source
            }

            updated_files.append(file_key)

        if new_documents:
            # Create or update vector database using abstraction layer
            if not self.vector_db.exists():
                # Create new database
                if self.vector_db.create_from_documents(new_documents):
                    print(
                        f"Successfully created vector database '{self.config.name}' with {len(new_documents)} documents"
                    )
                else:
                    print(f"Failed to create vector database '{self.config.name}'")
                    return {
                        "success": False,
                        "message": f"Failed to create vector database '{self.config.name}'",
                        "updated_files": [],
                        "new_documents_count": 0,
                        "total_files_processed": len(all_files),
                    }
            else:
                # Update existing database
                # Delete old documents
                for file_key in updated_files:
                    if not self.vector_db.delete_documents({"file_key": file_key}):
                        print(f"Failed to delete old document {file_key}")

                # Add new documents
                if not self.vector_db.add_documents(new_documents):
                    print(f"Failed to add new documents to '{self.config.name}'")
                    return {
                        "success": False,
                        "message": f"Failed to add documents to '{self.config.name}'",
                        "updated_files": updated_files,
                        "new_documents_count": 0,
                        "total_files_processed": len(all_files),
                    }

            # Save metadata
            self._save_metadata()

            print(
                f"Knowledge base '{self.config.name}' update completed, processed {len(updated_files)} files, created {len(new_documents)} document chunks"
            )

        return {
            "success": True,
            "message": f"Knowledge base '{self.config.name}' update completed",
            "updated_files": updated_files,
            "new_documents_count": len(new_documents),
            "total_files_processed": len(all_files),
        }

    def search(self, query: str, k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search knowledge base using abstraction layer"""
        if not self.vector_db.exists():
            return []

        try:
            # Use larger k value for initial search
            search_k = self.config.search_k
            initial_k = max(k * 2, search_k)

            # Perform similarity search using abstraction layer
            docs = self.vector_db.search(query, k=initial_k, filter_metadata=filter_metadata)

            results = []
            for doc, score in docs:
                # Calculate comprehensive score
                final_score = self._calculate_relevance_score(query, doc, score)

                results.append(
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": float(score),
                        "relevance_score": final_score,
                    }
                )

            # Re-sort by relevance score
            results.sort(key=lambda x: x["relevance_score"], reverse=True)

            # Return top k results
            return results[:k]
        except Exception as e:
            print(f"Search failed in '{self.config.name}': {e}")
            return []

    def _calculate_relevance_score(self, query: str, doc, vector_score: float) -> float:
        """Calculate document relevance score"""
        try:
            content = doc.page_content.lower()
            query_lower = query.lower()
            metadata = doc.metadata

            # Base vector similarity score
            base_score = 1.0 / (1.0 + vector_score)

            # Keyword matching score
            keyword_score = 0.0
            query_words = query_lower.split()
            for word in query_words:
                if word in content:
                    keyword_score += 1.0
            keyword_score = keyword_score / len(query_words) if query_words else 0.0

            # Title matching score
            title_score = 0.0
            title = metadata.get("title", "").lower()
            if title and query_lower in title:
                title_score = 2.0
            elif title:
                for word in query_words:
                    if word in title:
                        title_score += 0.5

            # Metadata matching score
            metadata_score = 0.0
            searchable_fields = ["tags", "categories", "author", "description"]
            for field in searchable_fields:
                field_value = metadata.get(field, "").lower()
                if field_value:
                    if query_lower in field_value:
                        metadata_score += 1.0
                    else:
                        for word in query_words:
                            if word in field_value:
                                metadata_score += 0.3

            # Comprehensive score
            final_score = (
                base_score * 0.4  # Vector similarity 40%
                + keyword_score * 0.3  # Keyword matching 30%
                + title_score * 0.2  # Title matching 20%
                + metadata_score * 0.1  # Metadata matching 10%
            )

            return final_score

        except Exception as e:
            print(f"Failed to calculate relevance score: {e}")
            return 1.0 / (1.0 + vector_score)

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        if not self.vector_db.exists():
            return {"total_documents": 0, "total_files": 0}

        try:
            # Get document count from database abstraction layer
            db_stats = self.vector_db.get_stats()
            total_docs = db_stats.get("collection_count", 0)

            # Analyze file types
            file_types = {}
            for meta in self.metadata.values():
                file_type = meta.get("file_type", "unknown")
                file_types[file_type] = file_types.get(file_type, 0) + 1

            return {
                "name": self.config.name,
                "total_documents": total_docs,
                "total_files": len(self.metadata),
                "file_types": file_types,
                "source_paths": [str(p) for p in self.source_paths],
                "vector_db_path": str(self.vector_db_path),
                "supported_extensions": self.get_supported_extensions(),
                "last_updated": max(
                    [meta.get("last_updated", "") for meta in self.metadata.values()],
                    default="",
                ),
            }
        except Exception as e:
            print(f"Failed to get statistics for '{self.config.name}': {e}")
            return {"error": str(e)}

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information for debugging"""
        info = {
            "name": self.config.name,
            "db_type": self.db_type,
            "debug_mode": self.debug_mode,
            "vector_db_path": str(self.vector_db_path),
            "database_exists": self.vector_db.exists(),
        }

        # Get detailed stats from the database abstraction layer
        try:
            db_stats = self.vector_db.get_stats()
            info.update(db_stats)
        except Exception as e:
            info["db_stats_error"] = str(e)

        return info

    def switch_database_backend(self, new_db_type: str, debug_mode: Optional[bool] = None) -> bool:
        """Switch to a different database backend"""
        try:
            if debug_mode is not None:
                self.debug_mode = debug_mode

            print(f"Switching database backend from '{self.db_type}' to '{new_db_type}' for '{self.config.name}'")

            # Create new database instance
            new_vector_db = VectorDatabaseFactory.create_database(
                db_type=new_db_type,
                persist_directory=str(self.vector_db_path),
                embedding_function=self.embeddings,
                name=self.config.name,
                debug_mode=self.debug_mode,
            )

            # If successful, update references
            self.db_type = new_db_type
            self.vector_db = new_vector_db

            # Database backend switched successfully

            print(f"Successfully switched to '{new_db_type}' backend for '{self.config.name}'")
            return True

        except Exception as e:
            print(f"Failed to switch database backend for '{self.config.name}': {e}")
            return False
