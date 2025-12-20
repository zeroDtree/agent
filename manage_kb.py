#!/usr/bin/env python3
"""
Knowledge Base Management CLI Tool
A simple, elegant command-line interface for managing embedding knowledge bases.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from utils.ekb import EKBConfig, EmbeddingKnowledgeBase
from utils.regex_pattern_filter import FilterOrder


def parse_list_arg(arg: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated string into list"""
    return [item.strip() for item in arg.split(",")] if arg else None


def load_config_from_json(name: str) -> EKBConfig:
    """Load EKBConfig from saved JSON configuration file based on database name"""
    config_file = Path("data/vector_db") / name / "config.json"

    if not config_file.exists():
        print(f"⚠️  No saved configuration found for '{name}', using minimal config")
        return EKBConfig(name=name, source_paths=None)

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)

        print(f"📄 Loaded configuration from {config_file}")

        # Create EKBConfig from saved configuration
        return EKBConfig(
            name=name,
            source_paths=saved_config.get("source_paths"),
            exclude_patterns=saved_config.get("exclude_patterns"),
            include_patterns=saved_config.get("include_patterns"),
            filter_order=FilterOrder(saved_config.get("filter_order", "exclude_first")),
            use_gitignore=saved_config.get("use_gitignore", True),
        )

    except Exception as e:
        print(f"❌ Failed to load configuration for '{name}': {e}")
        print(f"⚠️  Using minimal config instead")
        return EKBConfig(name=name, source_paths=None)


def create_kb_config(args) -> EKBConfig:
    """Create EKBConfig from command line arguments"""
    return EKBConfig(
        name=args.name,
        source_paths=parse_list_arg(args.source_paths),
        exclude_patterns=parse_list_arg(args.exclude),
        include_patterns=parse_list_arg(args.include),
        filter_order=FilterOrder(args.filter_order) if args.filter_order else FilterOrder.EXCLUDE_FIRST,
        use_gitignore=not getattr(args, "no_gitignore", False),
    )


def cmd_update(args) -> int:
    """Create or update knowledge base"""
    try:
        config = create_kb_config(args)
        kb = EmbeddingKnowledgeBase(config)

        patterns = parse_list_arg(args.patterns) if hasattr(args, "patterns") else None
        result = kb.update_knowledge_base(file_patterns=patterns)

        if result["success"]:
            print(f"✅ {result['message']}")
            print(f"📄 Processed {result['total_files_processed']} files")
            print(f"📝 Updated {len(result['updated_files'])} files")
            print(f"🔄 Created {result['new_documents_count']} document chunks")
            return 0
        else:
            print(f"❌ {result['message']}")
            return 1

    except Exception as e:
        print(f"❌ Update failed: {e}")
        return 1


def cmd_search(args) -> int:
    """Search knowledge base"""
    try:
        # Load configuration from saved JSON file
        config = load_config_from_json(args.name)
        kb = EmbeddingKnowledgeBase(config)

        results = kb.search(args.query, k=args.limit)

        if not results:
            print(f"🔍 No results found for '{args.query}' in '{args.name}'")
            return 0

        print(f"🔍 Found {len(results)} results in '{args.name}':\n")

        for i, result in enumerate(results, 1):
            metadata = result["metadata"]
            content = result["content"]
            score = result.get("relevance_score", result["score"])

            print(f"**{i}. {metadata.get('title', 'Untitled')}**")
            print(f"📁 Source: {metadata.get('source', 'Unknown')}")

            if metadata.get("tags"):
                print(f"🏷️  Tags: {metadata.get('tags')}")
            if metadata.get("author"):
                print(f"👤 Author: {metadata.get('author')}")

            print(f"📊 Relevance: {score:.3f}")
            print(f"📄 Content:\n{content[:500]}{'...' if len(content) > 500 else ''}\n")
            print("─" * 60)

        return 0

    except Exception as e:
        print(f"❌ Search failed: {e}")
        return 1


def cmd_add(args) -> int:
    """Add text content to knowledge base"""
    try:
        # Load configuration from saved JSON file
        config = load_config_from_json(args.name)
        kb = EmbeddingKnowledgeBase(config)

        texts = [t.strip() for t in args.texts.split("|")]
        titles = [t.strip() for t in args.titles.split("|")] if args.titles else []
        sources = [s.strip() for s in args.sources.split("|")] if args.sources else []

        # Prepare metadata
        metadatas = []
        for i, _ in enumerate(texts):
            metadata = {}
            if i < len(titles) and titles[i]:
                metadata["title"] = titles[i]
            if i < len(sources) and sources[i]:
                metadata["source"] = sources[i]
            metadatas.append(metadata)

        result = kb.add_documents_from_texts(texts, metadatas)

        if result["success"]:
            print(f"✅ Added {len(texts)} text documents to '{args.name}'")
            print(f"📝 Created {result['new_documents_count']} document chunks")
            return 0
        else:
            print(f"❌ Failed to add texts: {result['message']}")
            return 1

    except Exception as e:
        print(f"❌ Add operation failed: {e}")
        return 1


def cmd_status(args) -> int:
    """Show knowledge base statistics"""
    try:
        # Load configuration from saved JSON file
        config = load_config_from_json(args.name)
        kb = EmbeddingKnowledgeBase(config)

        stats = kb.get_stats()

        if "error" in stats:
            print(f"❌ Error getting stats: {stats['error']}")
            return 1

        print(f"📊 Knowledge Base '{args.name}' Status:")
        print(f"📄 Documents: {stats['total_documents']}")
        print(f"📁 Files: {stats['total_files']}")
        print(f"📂 Sources: {', '.join(stats['source_paths'])}")
        print(f"🗂️  Database: {stats['vector_db_path']}")

        if stats.get("file_types"):
            types_str = ", ".join(f"{ext}({count})" for ext, count in stats["file_types"].items())
            print(f"📋 File types: {types_str}")

        if stats.get("last_updated"):
            print(f"🕒 Last updated: {stats['last_updated']}")

        return 0

    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return 1


def cmd_list(args) -> int:
    """List all knowledge bases"""
    try:
        data_dir = Path("data/vector_db")
        if not data_dir.exists():
            print("📝 No knowledge bases found")
            return 0

        kb_dirs = [d for d in data_dir.iterdir() if d.is_dir()]

        if not kb_dirs:
            print("📝 No knowledge bases found")
            return 0

        print(f"📚 Found {len(kb_dirs)} knowledge base(s):\n")

        for kb_dir in sorted(kb_dirs):
            name = kb_dir.name
            try:
                # Load configuration from saved JSON file
                config = load_config_from_json(name)
                kb = EmbeddingKnowledgeBase(config)
                stats = kb.get_stats()

                print(f"**{name}**")
                print(f"  📄 Documents: {stats.get('total_documents', 0)}")
                print(f"  📁 Files: {stats.get('total_files', 0)}")

                if stats.get("source_paths"):
                    print(f"  📂 Sources: {', '.join(stats['source_paths'])}")
                if stats.get("last_updated"):
                    print(f"  🕒 Updated: {stats['last_updated']}")

                print()

            except Exception as e:
                print(f"**{name}** (⚠️  Error: {e})\n")

        return 0

    except Exception as e:
        print(f"❌ List operation failed: {e}")
        return 1


def setup_parsers() -> argparse.ArgumentParser:
    """Setup command line argument parsers"""
    parser = argparse.ArgumentParser(
        description="Knowledge Base Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s update -s "docs,src" -p "*.md,*.py" -n my_kb
  %(prog)s search "machine learning" -n my_kb -l 10
  %(prog)s add my_kb "Some content|More content" -t "Title 1|Title 2"
  %(prog)s status -n my_kb
  %(prog)s list
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Update command
    update_parser = subparsers.add_parser("update", help="Create or update knowledge base")
    update_parser.add_argument("-n", "--name", default="default", help="Knowledge base name")
    update_parser.add_argument("-s", "--source-paths", help="Comma-separated source paths")
    update_parser.add_argument("-p", "--patterns", help="Comma-separated file patterns (e.g., *.md,*.txt)")
    update_parser.add_argument("-e", "--exclude", help="Comma-separated exclude patterns")
    update_parser.add_argument("-i", "--include", help="Comma-separated include patterns")
    update_parser.add_argument(
        "--filter-order", choices=["exclude_first", "include_first"], help="Filter application order"
    )
    update_parser.add_argument("--no-gitignore", action="store_true", help="Disable .gitignore filtering")
    update_parser.set_defaults(func=cmd_update)

    # Search command
    search_parser = subparsers.add_parser("search", help="Search knowledge base")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-n", "--name", default="default", help="Knowledge base name")
    search_parser.add_argument("-l", "--limit", type=int, default=5, help="Result limit")
    search_parser.set_defaults(func=cmd_search)

    # Add command
    add_parser = subparsers.add_parser("add", help="Add text content to knowledge base")
    add_parser.add_argument("name", help="Knowledge base name")
    add_parser.add_argument("texts", help="Pipe-separated text content")
    add_parser.add_argument("-t", "--titles", default="", help="Pipe-separated titles")
    add_parser.add_argument("-s", "--sources", default="", help="Pipe-separated source identifiers")
    add_parser.set_defaults(func=cmd_add)

    # Status command
    status_parser = subparsers.add_parser("status", help="Show knowledge base statistics")
    status_parser.add_argument("-n", "--name", default="default", help="Knowledge base name")
    status_parser.set_defaults(func=cmd_status)

    # List command
    list_parser = subparsers.add_parser("list", help="List all knowledge bases")
    list_parser.set_defaults(func=cmd_list)

    return parser


def main() -> int:
    """Main entry point"""
    parser = setup_parsers()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
