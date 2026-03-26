"""
Generic embedding knowledge base system.
Converts various document types to a vector database for AI retrieval.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from langchain_core.tools import tool

from utils.ekb import EKBConfig, EmbeddingKnowledgeBase
from utils.logger import get_logger
from utils.regex_pattern_filter import FilterOrder

logger = get_logger(__name__)

_knowledge_bases: Dict[str, EmbeddingKnowledgeBase] = {}

_CONFIG_BASE = Path("data/vector_db")

# Metadata fields to render in search results
_OPTIONAL_METADATA_FIELDS = [
    ("date", "📅"),
    ("author", "👤"),
    ("tags", "🏷️"),
    ("categories", "📂"),
]


def _load_kb_config(name: str) -> EKBConfig:
    """Load EKBConfig from a saved JSON file, or return a minimal config."""
    config_file = _CONFIG_BASE / name / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return EKBConfig(
                name=name,
                source_paths=saved.get("source_paths"),
                exclude_patterns=saved.get("exclude_patterns"),
                include_patterns=saved.get("include_patterns"),
                filter_order=FilterOrder(saved.get("filter_order", "exclude_first")),
                use_gitignore=saved.get("use_gitignore", True),
                db_type=saved.get("db_type", "chroma"),
                debug_mode=saved.get("debug_mode", False),
            )
        except Exception as e:
            logger.warning(f"Failed to load config for '{name}': {e}, using minimal config")

    return EKBConfig(name=name, source_paths=None)


def get_knowledge_base(name: str = "default") -> Optional[EmbeddingKnowledgeBase]:
    """Return a cached or newly-created knowledge base instance.

    Returns None if the knowledge base does not exist or cannot be loaded.
    """
    if name in _knowledge_bases:
        return _knowledge_bases[name]

    config = _load_kb_config(name)

    if config.source_paths is None:
        logger.info(f"No saved configuration found for '{name}'; knowledge base is unavailable.")
        return None

    try:
        kb = EmbeddingKnowledgeBase(config=config)
        _knowledge_bases[name] = kb
        return kb
    except Exception as e:
        logger.error(f"Failed to initialise knowledge base '{name}': {e}")
        return None


def _require_kb(name: str) -> tuple[Optional[EmbeddingKnowledgeBase], Optional[str]]:
    """Return (kb, None) on success or (None, error_message) on failure."""
    kb = get_knowledge_base(name)
    if kb is None:
        msg = (
            f"Knowledge base '{name}' does not exist or has no configuration. "
            "Please create it first via the management interface."
        )
        return None, msg
    return kb, None


@tool
def search_knowledge_base(query: str, name: str = "default", limit: int = 5) -> str:
    """Search for relevant content in a knowledge base.

    Args:
        query: Natural-language search query.
        name: Name of the knowledge base (default: "default").
        limit: Maximum number of results to return.
    """
    kb, err = _require_kb(name)
    if err:
        return f"❌ {err}"
    assert kb is not None

    try:
        results = kb.search(query, k=limit)
    except Exception as e:
        logger.error(f"Error searching knowledge base '{name}': {e}")
        return f"❌ Error during search in '{name}': {e}"

    if not results:
        return f"🔍 No content related to '{query}' found in knowledge base '{name}'."

    lines = [f"🔍 Found {len(results)} relevant result(s) in '{name}':\n"]
    for i, result in enumerate(results, 1):
        metadata = result["metadata"]
        score = result.get("relevance_score", result["score"])

        lines.append(f"**{i}. {metadata.get('title', 'No title')}**")
        lines.append(f"📁 File: {metadata.get('source', 'Unknown')}")
        for field, icon in _OPTIONAL_METADATA_FIELDS:
            value = metadata.get(field)
            if value:
                lines.append(f"{icon} {field.title()}: {value}")
        lines.append(f"📊 Relevance: {score:.3f}")
        lines.append(f"📄 Content:\n{result['content']}\n")
        lines.append("---\n")

    return "\n".join(lines)


@tool
def add_text_to_knowledge_base(name: str, texts: str, titles: str = "") -> str:
    """Add plain-text content directly to a knowledge base.

    Args:
        name: Name of the knowledge base.
        texts: Pipe-separated list of text content to add (e.g. "text1|text2").
        titles: Pipe-separated list of titles for each text entry (optional).
    """
    kb, err = _require_kb(name)
    if err:
        return f"❌ {err}"
    assert kb is not None

    try:
        text_list = [t.strip() for t in texts.split("|") if t.strip()]
        title_list = [t.strip() for t in titles.split("|") if t.strip()] if titles else []
        metadatas = [{"title": title_list[i]} if i < len(title_list) else {} for i in range(len(text_list))]

        result = kb.add_documents_from_texts(text_list, metadatas)
        if result["success"]:
            return (
                f"✅ Added {len(text_list)} text document(s) to knowledge base '{name}'.\n"
                f"📄 New chunks: {result['new_documents_count']}"
            )
        return f"❌ Failed to add texts to knowledge base '{name}': {result['message']}"
    except Exception as e:
        logger.error(f"Error adding texts to knowledge base '{name}': {e}")
        return f"❌ Error adding texts to knowledge base '{name}': {e}"


@tool
def get_knowledge_base_stats(name: str = "default") -> str:
    """Get statistics for a knowledge base.

    Args:
        name: Name of the knowledge base (default: "default").
    """
    kb, err = _require_kb(name)
    if err:
        return f"❌ {err}"
    assert kb is not None

    try:
        stats = kb.get_stats()
        if "error" in stats:
            return f"❌ Failed to get statistics for '{name}': {stats['error']}"

        lines = [
            f"📊 Knowledge base '{name}' statistics:",
            f"📄 Total documents: {stats['total_documents']}",
            f"📁 Total files: {stats['total_files']}",
            f"📂 Source paths: {', '.join(stats['source_paths'])}",
            f"🗂️ Vector database path: {stats['vector_db_path']}",
        ]
        if stats.get("file_types"):
            file_types = ", ".join(f"{ext}({count})" for ext, count in stats["file_types"].items())
            lines.append(f"📊 File types: {file_types}")
        lines.append(f"🕒 Last updated: {stats['last_updated']}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error getting statistics for '{name}': {e}")
        return f"❌ Error getting statistics for '{name}': {e}"


@tool
def list_knowledge_bases() -> str:
    """List all available knowledge bases on the filesystem."""
    try:
        if not _CONFIG_BASE.exists():
            return "📝 No knowledge bases found."

        kb_dirs = sorted(d for d in _CONFIG_BASE.iterdir() if d.is_dir())
        if not kb_dirs:
            return "📝 No knowledge bases found."

        lines = [f"📚 Found {len(kb_dirs)} knowledge base(s):\n"]
        for kb_dir in kb_dirs:
            name = kb_dir.name
            kb = get_knowledge_base(name)
            if kb is None:
                lines.append(f"**{name}** (⚠️  No valid configuration)\n")
                continue
            try:
                stats = kb.get_stats()
                lines.extend(
                    [
                        f"**{name}**",
                        f"  📄 Documents: {stats.get('total_documents', 0)}",
                        f"  📁 Files: {stats.get('total_files', 0)}",
                        f"  📂 Sources: {', '.join(stats.get('source_paths', []))}",
                        f"  🕒 Updated: {stats.get('last_updated', 'Never')}",
                        "",
                    ]
                )
            except Exception as e:
                lines.append(f"**{name}** (⚠️  Error: {e})\n")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing knowledge bases: {e}")
        return f"❌ Error listing knowledge bases: {e}"


@tool
def get_database_debug_info(name: str = "default") -> str:
    """Get low-level debugging information about a knowledge base's vector store.

    Args:
        name: Name of the knowledge base (default: "default").
    """
    kb, err = _require_kb(name)
    if err:
        return f"❌ {err}"
    assert kb is not None

    try:
        info = kb.get_database_info()
        lines = [
            f"🔍 Database debug info for '{name}':",
            "",
            f"📊 Database type: {info.get('type', 'Unknown')}",
            f"🗂️ Name: {info.get('name', 'Unknown')}",
            f"📁 Directory: {info.get('directory', 'Unknown')}",
            f"✅ Exists: {info.get('exists', False)}",
            f"📂 Directory exists: {info.get('directory_exists', False)}",
            f"🔢 Collection count: {info.get('collection_count', 'Unknown')}",
            f"🐛 Debug mode: {info.get('debug_mode', False)}",
            f"🔌 Database status: {'Exists' if info.get('database_exists', False) else 'Not found'}",
        ]
        if info.get("db_stats_error"):
            lines.append(f"⚠️ Error getting stats: {info['db_stats_error']}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error getting debug info for '{name}': {e}")
        return f"❌ Error getting debug info for '{name}': {e}"


@tool
def switch_database_backend(name: str = "default", db_type: str = "chroma", debug_mode: bool = False) -> str:
    """Switch the vector database backend for a knowledge base.

    Args:
        name: Name of the knowledge base (default: "default").
        db_type: Target backend type (e.g. "chroma").
        debug_mode: Whether to enable debug mode on the new backend.
    """
    kb, err = _require_kb(name)
    if err:
        return f"❌ {err}"
    assert kb is not None

    try:
        if kb.switch_database_backend(db_type, debug_mode):
            return f"✅ Switched '{name}' to '{db_type}' backend (debug_mode={debug_mode})."
        return f"❌ Failed to switch '{name}' to '{db_type}' backend."
    except Exception as e:
        logger.error(f"Error switching database backend for '{name}': {e}")
        return f"❌ Error switching database backend for '{name}': {e}"
