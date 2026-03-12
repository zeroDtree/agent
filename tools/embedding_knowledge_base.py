"""
Generic embedding knowledge base system
Convert various document types to vector database for AI retrieval
"""

from typing import Dict

from langchain_core.tools import tool

from utils.ekb import EKBConfig, EmbeddingKnowledgeBase
from utils.logger import get_logger
from utils.regex_pattern_filter import FilterOrder

logger = get_logger(__name__)

# Global knowledge base instances cache
_knowledge_bases: Dict[str, EmbeddingKnowledgeBase] = {}


def get_knowledge_base(name: str = "default") -> EmbeddingKnowledgeBase:
    """Get or create knowledge base instance from saved configuration"""
    if name in _knowledge_bases:
        return _knowledge_bases[name]

    # Load configuration from saved JSON file (similar to manage_kb.py)
    import json
    from pathlib import Path

    config_file = Path("data/vector_db") / name / "config.json"

    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                saved_config = json.load(f)

            config = EKBConfig(
                name=name,
                source_paths=saved_config.get("source_paths"),
                exclude_patterns=saved_config.get("exclude_patterns"),
                include_patterns=saved_config.get("include_patterns"),
                filter_order=FilterOrder(saved_config.get("filter_order", "exclude_first")),
                use_gitignore=saved_config.get("use_gitignore", True),
                db_type=saved_config.get("db_type", "chroma"),
                debug_mode=saved_config.get("debug_mode", False),
            )
        except Exception as e:
            logger.warning(f"Failed to load config for '{name}': {e}, using minimal config")
            config = EKBConfig(name=name, source_paths=None)
    else:
        logger.info(f"No saved configuration found for '{name}', using minimal config")
        config = EKBConfig(name=name, source_paths=None)

    kb = EmbeddingKnowledgeBase(config=config)
    _knowledge_bases[name] = kb

    return kb


@tool
def search_knowledge_base(query: str, name: str = "default", limit: int = 5) -> str:
    """Search for relevant content in knowledge base

    Args:
        query: Search query
        name: Name of the knowledge base (default: "default")
        limit: Limit on number of results returned
    """
    try:
        kb = get_knowledge_base(name)
        results = kb.search(query, k=limit)

        if not results:
            return f"🔍 No content related to '{query}' found in knowledge base '{name}'"

        response = f"🔍 Found {len(results)} relevant results in '{name}':\n\n"

        for i, result in enumerate(results, 1):
            metadata = result["metadata"]
            content = result["content"]
            score = result.get("relevance_score", result["score"])

            response += f"**{i}. {metadata.get('title', 'No title')}**\n"
            response += f"📁 File: {metadata.get('source', 'Unknown')}\n"

            # Add optional metadata fields
            for field, icon in [("date", "📅"), ("author", "👤"), ("tags", "🏷️"), ("categories", "📂")]:
                if metadata.get(field):
                    response += f"{icon} {field.title()}: {metadata[field]}\n"

            response += f"📊 Relevance: {score:.3f}\n"
            response += f"📄 Content:\n{content}\n\n"
            response += "---\n\n"

        return response
    except Exception as e:
        logger.error(f"Error searching knowledge base '{name}': {e}")
        return f"❌ Error during search in '{name}': {str(e)}"


@tool
def add_text_to_knowledge_base(name: str, texts: str, titles: str = "") -> str:
    """Add text content directly to knowledge base

    Args:
        name: Name of the knowledge base
        texts: Pipe-separated list of text content to add
        titles: Pipe-separated list of titles for each text (optional)
    """
    try:
        kb = get_knowledge_base(name)

        text_list = [t.strip() for t in texts.split("|") if t.strip()]
        title_list = [t.strip() for t in titles.split("|") if t.strip()] if titles else []

        # Prepare metadata with titles if provided
        metadatas = [{"title": title_list[i]} if i < len(title_list) else {} for i in range(len(text_list))]

        result = kb.add_documents_from_texts(text_list, metadatas)

        if result["success"]:
            return (
                f"✅ Added {len(text_list)} text documents to knowledge base '{name}'!\n"
                f"📄 New document chunks: {result['new_documents_count']}"
            )
        else:
            return f"❌ Failed to add texts to knowledge base '{name}': {result['message']}"
    except Exception as e:
        logger.error(f"Error adding texts to knowledge base '{name}': {e}")
        return f"❌ Error adding texts to knowledge base '{name}': {str(e)}"


@tool
def get_knowledge_base_stats(name: str = "default") -> str:
    """Get knowledge base statistics

    Args:
        name: Name of the knowledge base (default: "default")
    """
    try:
        kb = get_knowledge_base(name)
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
        return f"❌ Error getting statistics for '{name}': {str(e)}"


@tool
def list_knowledge_bases() -> str:
    """List all available knowledge bases from filesystem"""
    try:
        from pathlib import Path

        data_dir = Path("data/vector_db")
        if not data_dir.exists():
            return "📝 No knowledge bases found"

        kb_dirs = [d for d in data_dir.iterdir() if d.is_dir()]

        if not kb_dirs:
            return "📝 No knowledge bases found"

        lines = [f"📚 Found {len(kb_dirs)} knowledge base(s):\n"]

        for kb_dir in sorted(kb_dirs):
            name = kb_dir.name
            try:
                kb = get_knowledge_base(name)
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
        return f"❌ Error listing knowledge bases: {str(e)}"


@tool
def get_database_debug_info(name: str = "default") -> str:
    """Get database debugging information

    Args:
        name: Name of the knowledge base (default: "default")
    """
    try:
        kb = get_knowledge_base(name)
        info = kb.get_database_info()

        lines = [
            f"🔍 Database Debug Info for '{name}':",
            "",
            f"📊 Database Type: {info.get('type', 'Unknown')}",
            f"🗂️ Name: {info.get('name', 'Unknown')}",
            f"📁 Directory: {info.get('directory', 'Unknown')}",
            f"✅ Exists: {info.get('exists', False)}",
            f"📂 Directory Exists: {info.get('directory_exists', False)}",
            f"🔢 Collection Count: {info.get('collection_count', 'Unknown')}",
            f"🐛 Debug Mode: {info.get('debug_mode', False)}",
            f"🔌 Database Status: {'Exists' if info.get('database_exists', False) else 'Not Found'}",
        ]

        if info.get("db_stats_error"):
            lines.append(f"⚠️ Error getting stats: {info['db_stats_error']}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error getting debug info for '{name}': {e}")
        return f"❌ Error getting debug info for '{name}': {str(e)}"


@tool
def switch_database_backend(name: str = "default", db_type: str = "chroma", debug_mode: bool = False) -> str:
    """Switch database backend for a knowledge base

    Args:
        name: Name of the knowledge base (default: "default")
        db_type: Database type to switch to (e.g., "chroma")
        debug_mode: Enable debug mode
    """
    try:
        kb = get_knowledge_base(name)
        success = kb.switch_database_backend(db_type, debug_mode)

        if success:
            return f"✅ Successfully switched '{name}' to '{db_type}' backend with debug_mode={debug_mode}"
        else:
            return f"❌ Failed to switch '{name}' to '{db_type}' backend"
    except Exception as e:
        logger.error(f"Error switching database backend for '{name}': {e}")
        return f"❌ Error switching database backend for '{name}': {str(e)}"
