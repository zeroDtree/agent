"""
Document processors for various file types
Handles parsing and metadata extraction from different document formats
"""

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import markdown
import yaml

from utils.constants import COMMENT_PATTERNS, get_language_from_extension, get_language_from_filename, is_code_file
from utils.logger import get_logger

logger = get_logger(name=__name__)


class DocumentProcessor(ABC):
    """Abstract base class for document processors"""

    @abstractmethod
    def can_process(self, file_path: Path) -> bool:
        """Check if this processor can handle the given file"""

    @abstractmethod
    def process(self, file_path: Path) -> Dict[str, Any]:
        """Process the file and return structured content"""

    def _get_base_result(self, file_path: Path, content: str = "") -> Dict[str, Any]:
        """Get base result structure with common fields"""
        return {
            "content": content,
            "metadata": {},
            "title": file_path.stem,
            "date": "",
            "tags": [],
            "categories": [],
            "author": "",
            "description": "",
        }

    def _safe_read_file(self, file_path: Path, encoding: str = "utf-8") -> Optional[str]:
        """Read file content, returning None on any IO or encoding error."""
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("Failed to read file %s: %s", file_path, e)
            return None


class MarkdownProcessor(DocumentProcessor):
    """Markdown document processor with enhanced front matter support"""

    SUPPORTED_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd"}

    def can_process(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def process(self, file_path: Path) -> Dict[str, Any]:
        """Parse Markdown file with comprehensive front matter support"""
        content = self._safe_read_file(file_path)
        if content is None:
            return self._get_base_result(file_path)

        front_matter, markdown_content = self._parse_front_matter(content)
        html_content = self._convert_to_html(markdown_content)
        metadata = self._extract_markdown_metadata(markdown_content, front_matter)

        result = self._get_base_result(file_path, markdown_content)
        result.update(
            {
                "html_content": html_content,
                "metadata": {**front_matter, **metadata},
                "title": front_matter.get("title", file_path.stem),
                "date": front_matter.get("date", ""),
                "tags": front_matter.get("tags", []),
                "categories": front_matter.get("categories", []),
                "author": front_matter.get("author", ""),
                "description": front_matter.get("description", ""),
            }
        )
        return result

    def _parse_front_matter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Parse YAML front matter from markdown content"""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    front_matter = yaml.safe_load(parts[1]) or {}
                    return front_matter, parts[2].strip()
                except yaml.YAMLError as e:
                    logger.warning("Failed to parse YAML front matter: %s", e)
        return {}, content

    def _convert_to_html(self, content: str) -> str:
        """Convert Markdown to HTML with extensions"""
        try:
            return markdown.markdown(
                content,
                extensions=["codehilite", "tables", "fenced_code", "toc", "attr_list"],
                extension_configs={
                    "codehilite": {"css_class": "highlight"},
                    "toc": {"marker": "[TOC]"},
                },
            )
        except Exception as e:
            logger.warning("Failed to convert markdown to HTML: %s", e)
            return content

    def _extract_markdown_metadata(self, content: str, front_matter: Dict) -> Dict[str, Any]:
        """Extract additional metadata from markdown content"""
        metadata: Dict[str, Any] = {}

        headers = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)
        if headers:
            metadata["headers"] = [{"level": len(level), "text": text.strip()} for level, text in headers]

        code_blocks = re.findall(r"```(\w+)?\n(.*?)```", content, re.DOTALL)
        if code_blocks:
            metadata["code_languages"] = list({lang for lang, _ in code_blocks if lang})

        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
        if links:
            metadata["external_links"] = [
                {"text": text, "url": url} for text, url in links if url.startswith(("http://", "https://"))
            ]

        word_count = len(re.findall(r"\b\w+\b", content))
        metadata["word_count"] = word_count
        metadata["reading_time"] = max(1, word_count // 200)

        return metadata


class TextProcessor(DocumentProcessor):
    """Enhanced plain text document processor"""

    SUPPORTED_EXTENSIONS = {".txt", ".text", ".log", ".readme"}
    SUPPORTED_FILENAMES = {"readme", "changelog", "license"}

    def can_process(self, file_path: Path) -> bool:
        return (
            file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS or file_path.name.lower() in self.SUPPORTED_FILENAMES
        )

    def process(self, file_path: Path) -> Dict[str, Any]:
        content = self._safe_read_file(file_path)
        if content is None:
            return self._get_base_result(file_path)

        result = self._get_base_result(file_path, content)
        result["metadata"] = self._analyze_text_content(content)
        return result

    def _analyze_text_content(self, content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        return {
            "line_count": len(lines),
            "word_count": len(re.findall(r"\b\w+\b", content)),
            "char_count": len(content),
            "blank_lines": sum(1 for line in lines if not line.strip()),
            "encoding": "utf-8",
        }


class JSONProcessor(DocumentProcessor):
    """Enhanced JSON document processor"""

    def can_process(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".json"

    def process(self, file_path: Path) -> Dict[str, Any]:
        content = self._safe_read_file(file_path)
        if content is None:
            return self._get_base_result(file_path)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON file %s: %s", file_path, e)
            return self._get_base_result(file_path, content)

        text_content = self._extract_text_from_json(data)
        metadata = self._extract_json_metadata(data)

        result = self._get_base_result(file_path, text_content)
        result.update(
            {
                "metadata": metadata,
                "title": metadata.get("title", file_path.stem),
                "date": metadata.get("date", ""),
                "tags": metadata.get("tags", []),
                "categories": metadata.get("categories", []),
                "author": metadata.get("author", ""),
                "description": metadata.get("description", ""),
                "raw_data": data,
            }
        )
        return result

    def _extract_text_from_json(self, data: Any, max_depth: int = 10) -> str:
        """Extract text content from JSON data recursively with depth limit"""
        if max_depth <= 0:
            return str(data)
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            texts = []
            content_fields = {"content", "text", "body", "description", "message"}
            for field in content_fields:
                if field in data:
                    texts.append(self._extract_text_from_json(data[field], max_depth - 1))
            for key, value in data.items():
                if key not in content_fields and isinstance(value, (str, dict, list)):
                    texts.append(self._extract_text_from_json(value, max_depth - 1))
            return "\n".join(filter(None, texts))
        if isinstance(data, list):
            return "\n".join(self._extract_text_from_json(item, max_depth - 1) for item in data)
        return str(data)

    def _extract_json_metadata(self, data: Any) -> Dict[str, Any]:
        """Extract metadata from JSON structure"""
        metadata: Dict[str, Any] = {}

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)) and key != "content":
                    metadata[key] = value
            metadata.update(
                {
                    "json_structure": {
                        k: (
                            "object"
                            if isinstance(v, dict)
                            else f"array[{len(v)}]" if isinstance(v, list) else type(v).__name__
                        )
                        for k, v in data.items()
                    },
                    "total_keys": len(data),
                    "nested_objects": sum(1 for v in data.values() if isinstance(v, dict)),
                    "arrays": sum(1 for v in data.values() if isinstance(v, list)),
                }
            )
        elif isinstance(data, list):
            metadata.update(
                {
                    "json_structure": "array",
                    "array_length": len(data),
                    "item_types": list({type(item).__name__ for item in data}),
                }
            )

        return metadata


class CodeProcessor(DocumentProcessor):
    """Enhanced code file processor with comprehensive language support"""

    # Metadata keys that may appear in header comments
    _HEADER_PATTERNS = [
        (r"@?author:?\s*(.+)", "author"),
        (r"@?description:?\s*(.+)", "description"),
        (r"@?version:?\s*(.+)", "version"),
        (r"@?license:?\s*(.+)", "license"),
        (r"@?copyright:?\s*(.+)", "copyright"),
    ]

    def can_process(self, file_path: Path) -> bool:
        return is_code_file(str(file_path))

    def process(self, file_path: Path) -> Dict[str, Any]:
        content = self._safe_read_file(file_path)
        if content is None:
            return self._get_base_result(file_path)

        language = self._detect_language(file_path)
        metadata = self._extract_code_metadata(content, language)

        result = self._get_base_result(file_path, content)
        result.update(
            {
                "metadata": metadata,
                "title": f"{file_path.name} ({language})",
                "language": language,
                "file_type": "code",
                "extension": file_path.suffix.lower(),
                "size": file_path.stat().st_size,
                "lines": len(content.splitlines()),
                "tags": [language, "code"],
                "categories": ["source_code"],
                "description": f"{language.title()} source code file",
            }
        )
        return result

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from filename then extension."""
        lang = get_language_from_filename(file_path.name.lower())
        if lang != "unknown":
            return lang
        return get_language_from_extension(file_path.suffix.lower())

    def _extract_code_metadata(self, content: str, language: str) -> Dict[str, Any]:
        lines = content.splitlines()
        metadata: Dict[str, Any] = {}

        metadata.update(self._extract_header_metadata(lines, language))
        metadata["code_stats"] = self._extract_code_stats(content, language)

        dependencies = self._extract_dependencies(lines, language)
        if dependencies:
            metadata["dependencies"] = dependencies

        signatures = self._extract_signatures(lines, language)
        if signatures:
            metadata["signatures"] = signatures

        metadata["complexity"] = self._analyze_complexity(content, language)
        return metadata

    def _extract_header_metadata(self, lines: List[str], language: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        single_comment = COMMENT_PATTERNS["single_line"].get(language)
        block_start = COMMENT_PATTERNS["block_start"].get(language)
        block_end = COMMENT_PATTERNS["block_end"].get(language)

        if single_comment:
            metadata.update(self._scan_single_line_comments(lines[:30], single_comment))
        if block_start and block_end:
            metadata.update(self._scan_block_comments(lines[:50], block_start, block_end))

        return metadata

    def _scan_single_line_comments(self, lines: List[str], comment_char: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        prefix_len = len(comment_char)
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith(comment_char):
                continue
            comment = stripped[prefix_len:].strip()
            for pattern, key in self._HEADER_PATTERNS:
                m = re.match(pattern, comment, re.IGNORECASE)
                if m:
                    metadata[key] = m.group(1).strip()
                    break
        return metadata

    def _scan_block_comments(self, lines: List[str], start: str, end: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        in_block = False
        for line in lines:
            stripped = line.strip()
            if start in stripped:
                in_block = True
                continue
            if end in stripped:
                in_block = False
                continue
            if not in_block:
                continue
            comment = stripped.lstrip("*").strip()
            if not comment:
                continue
            for pattern, key in self._HEADER_PATTERNS:
                m = re.match(pattern, comment, re.IGNORECASE)
                if m:
                    metadata[key] = m.group(1).strip()
                    break
        return metadata

    def _extract_code_stats(self, content: str, language: str) -> Dict[str, Any]:
        lines = content.splitlines()
        stats: Dict[str, Any] = {
            "total_lines": len(lines),
            "blank_lines": 0,
            "comment_lines": 0,
            "code_lines": 0,
            "functions": 0,
            "classes": 0,
            "imports": 0,
            "complexity_indicators": 0,
        }

        single_comment = COMMENT_PATTERNS["single_line"].get(language)
        block_start = COMMENT_PATTERNS["block_start"].get(language)
        block_end = COMMENT_PATTERNS["block_end"].get(language)
        in_block_comment = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                stats["blank_lines"] += 1
                continue
            if block_start and block_start in stripped:
                in_block_comment = True
            if block_end and block_end in stripped:
                in_block_comment = False
                stats["comment_lines"] += 1
                continue
            if in_block_comment:
                stats["comment_lines"] += 1
                continue
            if single_comment and stripped.startswith(single_comment):
                stats["comment_lines"] += 1
                continue
            stats["code_lines"] += 1
            self._count_language_constructs(stripped, language, stats)

        return stats

    def _count_language_constructs(self, line: str, language: str, stats: Dict[str, Any]) -> None:
        if language == "python":
            if line.startswith("def "):
                stats["functions"] += 1
            elif line.startswith("class "):
                stats["classes"] += 1
            elif line.startswith(("import ", "from ")):
                stats["imports"] += 1
            elif any(kw in line for kw in ("if ", "elif ", "for ", "while ", "try:", "except")):
                stats["complexity_indicators"] += 1

        elif language in ("javascript", "typescript"):
            if "function " in line or "=>" in line:
                stats["functions"] += 1
            elif line.startswith("class "):
                stats["classes"] += 1
            elif line.startswith(("import ", "require(")):
                stats["imports"] += 1
            elif any(kw in line for kw in ("if(", "if ", "for(", "while(", "switch(")):
                stats["complexity_indicators"] += 1

        elif language == "java":
            if re.search(r"\b\w+\s*\([^)]*\)\s*\{", line):
                stats["functions"] += 1
            elif line.startswith(("public class", "class ", "interface ")):
                stats["classes"] += 1
            elif line.startswith("import "):
                stats["imports"] += 1
            elif any(kw in line for kw in ("if(", "if ", "for(", "while(", "switch(")):
                stats["complexity_indicators"] += 1

    def _extract_dependencies(self, lines: List[str], language: str) -> List[str]:
        deps: List[str] = []
        for line in lines:
            stripped = line.strip()
            if language == "python":
                if stripped.startswith("import "):
                    deps.append(stripped[7:].split(" as ")[0].split(".")[0].strip())
                elif stripped.startswith("from "):
                    deps.append(stripped[5:].split(" import ")[0].split(".")[0].strip())
            elif language in ("javascript", "typescript"):
                if stripped.startswith("import "):
                    m = re.search(r'from [\'"]([^\'"]+)[\'"]', stripped)
                    if m:
                        deps.append(m.group(1))
                elif "require(" in stripped:
                    m = re.search(r'require\([\'"]([^\'"]+)[\'"]\)', stripped)
                    if m:
                        deps.append(m.group(1))
            elif language == "java":
                if stripped.startswith("import "):
                    deps.append(stripped[7:].rstrip(";").split(".")[0])
        return list(set(deps))

    def _extract_signatures(self, lines: List[str], language: str) -> List[Dict[str, Any]]:
        signatures = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if language == "python":
                if stripped.startswith("def ") or stripped.startswith("class "):
                    signatures.append(
                        {
                            "type": "function" if stripped.startswith("def ") else "class",
                            "signature": stripped,
                            "line": i + 1,
                        }
                    )
            elif language in ("javascript", "typescript"):
                if "function " in stripped or "=>" in stripped or stripped.startswith("class "):
                    sig_type = "class" if stripped.startswith("class ") else "function"
                    signatures.append({"type": sig_type, "signature": stripped, "line": i + 1})
        return signatures

    def _analyze_complexity(self, content: str, language: str) -> Dict[str, Any]:
        complexity: Dict[str, Any] = {
            "cyclomatic_complexity": 0,
            "nesting_level": 0,
            "long_functions": 0,
        }

        lines = content.splitlines()
        max_indent = 0
        function_lines = 0
        in_function = False

        for line in lines:
            indent = len(line) - len(line.lstrip())
            if indent > max_indent:
                max_indent = indent

            stripped = line.strip()
            if language == "python":
                if any(kw in stripped for kw in ("if ", "elif ", "for ", "while ", "try:", "except", "with ")):
                    complexity["cyclomatic_complexity"] += 1

                if stripped.startswith("def "):
                    if in_function and function_lines > 50:
                        complexity["long_functions"] += 1
                    in_function = True
                    function_lines = 0
                elif in_function:
                    if stripped and not line[0] in (" ", "\t"):
                        if function_lines > 50:
                            complexity["long_functions"] += 1
                        in_function = False
                    else:
                        function_lines += 1

        if in_function and function_lines > 50:
            complexity["long_functions"] += 1

        complexity["nesting_level"] = max_indent // 4 if language == "python" else max_indent // 2
        return complexity


# =============================================================================
# Processor Factory and Registry
# =============================================================================


class ProcessorFactory:
    """Factory class for document processors with automatic registration"""

    def __init__(self, custom_processors: Optional[List[DocumentProcessor]] = None):
        self._processors: List[DocumentProcessor] = [
            MarkdownProcessor(),
            JSONProcessor(),
            CodeProcessor(),
            TextProcessor(),  # fallback
        ]
        if custom_processors:
            self._processors = custom_processors + self._processors

    def get_processor(self, file_path: Path) -> Optional[DocumentProcessor]:
        """Return the first processor that can handle the given file."""
        for processor in self._processors:
            if processor.can_process(file_path):
                return processor
        return None

    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process file using the appropriate processor."""
        processor = self.get_processor(file_path)
        if processor:
            return processor.process(file_path)

        logger.debug("No processor found for %s", file_path)
        return {
            "content": "",
            "metadata": {"error": "Unsupported file type"},
            "title": file_path.stem,
            "file_type": "unsupported",
        }


# Default factory instance
default_processor_factory = ProcessorFactory()


# =============================================================================
# Convenience Functions
# =============================================================================


def process_document(file_path: Path) -> Dict[str, Any]:
    """Process a document using the default factory"""
    return default_processor_factory.process_file(file_path)


def get_supported_extensions() -> Set[str]:
    """Get all supported file extensions"""
    factory = ProcessorFactory()
    extensions: Set[str] = set()
    for processor in factory._processors:
        if hasattr(processor, "SUPPORTED_EXTENSIONS"):
            extensions.update(processor.SUPPORTED_EXTENSIONS)
    return extensions
