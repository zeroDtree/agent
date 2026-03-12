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
        """Safely read file content with error handling"""

        with open(file_path, "r", encoding=encoding) as f:
            return f.read()


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

        # Parse front matter
        front_matter, markdown_content = self._parse_front_matter(content)

        # Convert Markdown to HTML for enhanced content
        html_content = self._convert_to_html(markdown_content)

        # Extract additional metadata
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
        front_matter = {}

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    front_matter = yaml.safe_load(parts[1]) or {}
                    content = parts[2].strip()
                except yaml.YAMLError as e:
                    print(f"Failed to parse YAML front matter: {e}")

        return front_matter, content

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
            print(f"Failed to convert markdown to HTML: {e}")
            return content

    def _extract_markdown_metadata(self, content: str, front_matter: Dict) -> Dict[str, Any]:
        """Extract additional metadata from markdown content"""
        metadata = {}

        # Extract headers for structure analysis
        headers = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)
        if headers:
            metadata["headers"] = [{"level": len(level), "text": text.strip()} for level, text in headers]

        # Extract code blocks
        code_blocks = re.findall(r"```(\w+)?\n(.*?)```", content, re.DOTALL)
        if code_blocks:
            metadata["code_languages"] = list(set(lang for lang, _ in code_blocks if lang))

        # Extract links
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
        if links:
            metadata["external_links"] = [
                {"text": text, "url": url} for text, url in links if url.startswith(("http", "https"))
            ]

        # Word count and reading time estimation
        word_count = len(re.findall(r"\b\w+\b", content))
        metadata["word_count"] = word_count
        metadata["reading_time"] = max(1, word_count // 200)  # ~200 words per minute

        return metadata


class TextProcessor(DocumentProcessor):
    """Enhanced plain text document processor"""

    SUPPORTED_EXTENSIONS = {".txt", ".text", ".log", ".readme"}

    def can_process(self, file_path: Path) -> bool:
        extension = file_path.suffix.lower()
        filename = file_path.name.lower()
        return extension in self.SUPPORTED_EXTENSIONS or filename in {
            "readme",
            "changelog",
            "license",
        }

    def process(self, file_path: Path) -> Dict[str, Any]:
        """Process plain text file with basic analysis"""
        content = self._safe_read_file(file_path)
        if content is None:
            return self._get_base_result(file_path)

        metadata = self._analyze_text_content(content)

        result = self._get_base_result(file_path, content)
        result["metadata"] = metadata

        return result

    def _analyze_text_content(self, content: str) -> Dict[str, Any]:
        """Analyze text content for basic statistics"""
        lines = content.splitlines()

        return {
            "line_count": len(lines),
            "word_count": len(re.findall(r"\b\w+\b", content)),
            "char_count": len(content),
            "blank_lines": sum(1 for line in lines if not line.strip()),
            "encoding": "utf-8",  # Since we successfully read it
        }


class JSONProcessor(DocumentProcessor):
    """Enhanced JSON document processor"""

    def can_process(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".json"

    def process(self, file_path: Path) -> Dict[str, Any]:
        """Process JSON file with comprehensive metadata extraction"""
        content = self._safe_read_file(file_path)
        if content is None:
            return self._get_base_result(file_path)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON file {file_path}: {e}")
            return self._get_base_result(file_path, content)

        # Extract text content and metadata
        text_content = self._extract_text_from_json(data)
        metadata = self._extract_json_metadata(data, file_path)

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
                "raw_data": data,  # Store original data for advanced processing
            }
        )

        return result

    def _extract_text_from_json(self, data: Any, max_depth: int = 10) -> str:
        """Extract text content from JSON data recursively with depth limit"""
        if max_depth <= 0:
            return str(data)

        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            texts = []
            # Prioritize content fields
            content_fields = ["content", "text", "body", "description", "message"]

            for field in content_fields:
                if field in data:
                    texts.append(self._extract_text_from_json(data[field], max_depth - 1))

            # Extract from other fields
            for key, value in data.items():
                if key.lower() not in content_fields and isinstance(value, (str, dict, list)):
                    texts.append(self._extract_text_from_json(value, max_depth - 1))

            return "\n".join(filter(None, texts))
        elif isinstance(data, list):
            return "\n".join(self._extract_text_from_json(item, max_depth - 1) for item in data)
        else:
            return str(data)

    def _extract_json_metadata(self, data: Any, file_path: Path) -> Dict[str, Any]:
        """Extract comprehensive metadata from JSON structure"""
        metadata = {}

        if isinstance(data, dict):
            # Extract scalar metadata
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)) and key != "content":
                    metadata[key] = value

            # Analyze structure
            metadata.update(
                {
                    "json_structure": self._analyze_json_structure(data),
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
                    "item_types": list(set(type(item).__name__ for item in data)),
                }
            )

        return metadata

    def _analyze_json_structure(self, data: Dict) -> Dict[str, Any]:
        """Analyze JSON structure for schema-like information"""
        structure = {}

        for key, value in data.items():
            if isinstance(value, dict):
                structure[key] = "object"
            elif isinstance(value, list):
                structure[key] = f"array[{len(value)}]"
            else:
                structure[key] = type(value).__name__

        return structure


class CodeProcessor(DocumentProcessor):
    """Enhanced code file processor with comprehensive language support"""

    def can_process(self, file_path: Path) -> bool:
        """Check if this is a code file using optimized lookup"""
        return is_code_file(str(file_path))

    def process(self, file_path: Path) -> Dict[str, Any]:
        """Process code file with comprehensive analysis"""
        content = self._safe_read_file(file_path)
        if content is None:
            return self._get_base_result(file_path)

        # Detect programming language
        language = self._detect_language(file_path)

        # Extract comprehensive metadata
        metadata = self._extract_code_metadata(content, language, file_path)

        # Get file statistics
        file_stats = file_path.stat()

        result = self._get_base_result(file_path, content)
        result.update(
            {
                "metadata": metadata,
                "title": f"{file_path.name} ({language})",
                "language": language,
                "file_type": "code",
                "extension": file_path.suffix.lower(),
                "size": file_stats.st_size,
                "lines": len(content.splitlines()),
                "tags": [language, "code", metadata.get("primary_category", "source")],
                "categories": ["source_code"],
                "description": f"{language.title()} source code file",
            }
        )

        return result

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language with improved accuracy"""
        extension = file_path.suffix.lower()
        filename = file_path.name.lower()

        # Check special filenames first
        lang = get_language_from_filename(filename)
        if lang != "unknown":
            return lang

        # Check extension mapping
        return get_language_from_extension(extension)

    def _extract_code_metadata(self, content: str, language: str, file_path: Path) -> Dict[str, Any]:
        """Extract comprehensive metadata from code content"""
        metadata = {}
        lines = content.splitlines()

        # Extract header comments and docstrings
        header_info = self._extract_header_metadata(lines, language)
        metadata.update(header_info)

        # Generate code statistics
        stats = self._extract_code_stats(content, language)
        metadata["code_stats"] = stats

        # Analyze imports and dependencies
        dependencies = self._extract_dependencies(lines, language)
        if dependencies:
            metadata["dependencies"] = dependencies

        # Extract function and class signatures
        signatures = self._extract_signatures(lines, language)
        if signatures:
            metadata["signatures"] = signatures

        # Detect code complexity indicators
        complexity = self._analyze_complexity(content, language)
        metadata["complexity"] = complexity

        return metadata

    def _extract_header_metadata(self, lines: List[str], language: str) -> Dict[str, Any]:
        """Extract metadata from file headers and comments"""
        metadata = {}

        # Get comment patterns for the language
        single_comment = COMMENT_PATTERNS.get("single_line", {}).get(language)
        block_start = COMMENT_PATTERNS.get("block_start", {}).get(language)
        block_end = COMMENT_PATTERNS.get("block_end", {}).get(language)

        if single_comment:
            metadata.update(self._extract_single_line_metadata(lines, single_comment))

        if block_start and block_end:
            metadata.update(self._extract_block_comment_metadata(lines, block_start, block_end))

        return metadata

    def _extract_single_line_metadata(self, lines: List[str], comment_char: str) -> Dict[str, Any]:
        """Extract metadata from single-line comments"""
        metadata = {}

        for line in lines[:30]:  # Check first 30 lines
            stripped = line.strip()
            if stripped.startswith(comment_char):
                comment = stripped[len(comment_char) :].strip()

                # Look for common metadata patterns
                for pattern, key in [
                    (r"@?author:?\s*(.+)", "author"),
                    (r"@?description:?\s*(.+)", "description"),
                    (r"@?version:?\s*(.+)", "version"),
                    (r"@?license:?\s*(.+)", "license"),
                    (r"@?copyright:?\s*(.+)", "copyright"),
                ]:
                    match = re.match(pattern, comment, re.IGNORECASE)
                    if match:
                        metadata[key] = match.group(1).strip()
                        break

        return metadata

    def _extract_block_comment_metadata(self, lines: List[str], start: str, end: str) -> Dict[str, Any]:
        """Extract metadata from block comments"""
        metadata = {}
        in_block = False

        for line in lines[:50]:  # Check first 50 lines
            stripped = line.strip()

            if start in stripped:
                in_block = True
                continue
            if end in stripped:
                in_block = False
                continue

            if in_block:
                # Clean comment content
                comment = stripped.lstrip("*").strip()
                if comment:
                    # Look for metadata patterns
                    for pattern, key in [
                        (r"@?author:?\s*(.+)", "author"),
                        (r"@?description:?\s*(.+)", "description"),
                        (r"@?version:?\s*(.+)", "version"),
                    ]:
                        match = re.match(pattern, comment, re.IGNORECASE)
                        if match:
                            metadata[key] = match.group(1).strip()
                            break

        return metadata

    def _extract_code_stats(self, content: str, language: str) -> Dict[str, Any]:
        """Generate comprehensive code statistics"""
        lines = content.splitlines()
        stats = {
            "total_lines": len(lines),
            "blank_lines": 0,
            "comment_lines": 0,
            "code_lines": 0,
            "functions": 0,
            "classes": 0,
            "imports": 0,
            "complexity_indicators": 0,
        }

        single_comment = COMMENT_PATTERNS.get("single_line", {}).get(language)
        block_start = COMMENT_PATTERNS.get("block_start", {}).get(language)
        block_end = COMMENT_PATTERNS.get("block_end", {}).get(language)

        in_block_comment = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                stats["blank_lines"] += 1
                continue

            # Check for block comments
            if block_start and block_start in stripped:
                in_block_comment = True
            if block_end and block_end in stripped:
                in_block_comment = False
                stats["comment_lines"] += 1
                continue

            if in_block_comment:
                stats["comment_lines"] += 1
                continue

            # Check for single-line comments
            if single_comment and stripped.startswith(single_comment):
                stats["comment_lines"] += 1
                continue

            # This is a code line
            stats["code_lines"] += 1

            # Count language-specific constructs
            self._count_language_constructs(stripped, language, stats)

        return stats

    def _count_language_constructs(self, line: str, language: str, stats: Dict[str, Any]) -> None:
        """Count language-specific constructs like functions, classes, etc."""
        line.lower()

        if language == "python":
            if line.strip().startswith("def "):
                stats["functions"] += 1
            elif line.strip().startswith("class "):
                stats["classes"] += 1
            elif line.strip().startswith(("import ", "from ")):
                stats["imports"] += 1
            elif any(keyword in line for keyword in ["if ", "for ", "while ", "try:", "except"]):
                stats["complexity_indicators"] += 1

        elif language in ["javascript", "typescript"]:
            if "function " in line or "=>" in line:
                stats["functions"] += 1
            elif line.strip().startswith("class "):
                stats["classes"] += 1
            elif line.strip().startswith(("import ", "require(")):
                stats["imports"] += 1
            elif any(keyword in line for keyword in ["if(", "if ", "for(", "while(", "switch("]):
                stats["complexity_indicators"] += 1

        elif language == "java":
            if re.search(r"\b\w+\s*\([^)]*\)\s*\{", line):  # Method signature
                stats["functions"] += 1
            elif line.strip().startswith(("public class", "class ", "interface ")):
                stats["classes"] += 1
            elif line.strip().startswith("import "):
                stats["imports"] += 1
            elif any(keyword in line for keyword in ["if(", "if ", "for(", "while(", "switch("]):
                stats["complexity_indicators"] += 1

    def _extract_dependencies(self, lines: List[str], language: str) -> List[str]:
        """Extract imported modules and dependencies"""
        dependencies = []

        for line in lines:
            stripped = line.strip()

            if language == "python":
                if stripped.startswith("import "):
                    dep = stripped[7:].split(" as ")[0].split(".")[0]
                    dependencies.append(dep)
                elif stripped.startswith("from "):
                    dep = stripped[5:].split(" import ")[0].split(".")[0]
                    dependencies.append(dep)

            elif language in ["javascript", "typescript"]:
                if stripped.startswith("import "):
                    match = re.search(r'from [\'"]([^\'"]+)[\'"]', stripped)
                    if match:
                        dependencies.append(match.group(1))
                elif "require(" in stripped:
                    match = re.search(r'require\([\'"]([^\'"]+)[\'"]\)', stripped)
                    if match:
                        dependencies.append(match.group(1))

            elif language == "java":
                if stripped.startswith("import "):
                    dep = stripped[7:].rstrip(";").split(".")[0]
                    dependencies.append(dep)

        return list(set(dependencies))  # Remove duplicates

    def _extract_signatures(self, lines: List[str], language: str) -> List[Dict[str, str]]:
        """Extract function and class signatures"""
        signatures = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            if language == "python":
                if stripped.startswith("def ") or stripped.startswith("class "):
                    signatures.append(
                        {
                            "type": ("function" if stripped.startswith("def ") else "class"),
                            "signature": stripped,
                            "line": i + 1,
                        }
                    )

            elif language in ["javascript", "typescript"]:
                if "function " in stripped or "=>" in stripped or stripped.startswith("class "):
                    sig_type = "class" if stripped.startswith("class ") else "function"
                    signatures.append({"type": sig_type, "signature": stripped, "line": i + 1})

        return signatures

    def _analyze_complexity(self, content: str, language: str) -> Dict[str, Any]:
        """Analyze code complexity indicators"""
        complexity = {
            "cyclomatic_complexity": 0,
            "nesting_level": 0,
            "long_functions": 0,
        }

        lines = content.splitlines()
        max_indent = 0
        function_lines = 0
        in_function = False

        for line in lines:
            # Calculate indentation
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent)

            stripped = line.strip()

            # Count complexity indicators
            if language == "python":
                if any(
                    keyword in stripped
                    for keyword in [
                        "if ",
                        "elif ",
                        "for ",
                        "while ",
                        "try:",
                        "except",
                        "with ",
                    ]
                ):
                    complexity["cyclomatic_complexity"] += 1

                if stripped.startswith("def "):
                    in_function = True
                    function_lines = 0
                elif in_function:
                    if stripped and not stripped.startswith(" ") and not stripped.startswith("\t"):
                        if function_lines > 50:  # Long function threshold
                            complexity["long_functions"] += 1
                        in_function = False
                    else:
                        function_lines += 1

        complexity["nesting_level"] = max_indent // 4 if language == "python" else max_indent // 2

        return complexity


# =============================================================================
# Processor Factory and Registry
# =============================================================================


class ProcessorFactory:
    """Factory class for document processors with automatic registration"""

    def __init__(self):
        self._processors = [
            MarkdownProcessor(),
            JSONProcessor(),
            CodeProcessor(),
            TextProcessor(),  # Keep as fallback
        ]

    def get_processor(self, file_path: Path) -> Optional[DocumentProcessor]:
        """Get appropriate processor for file path"""
        for processor in self._processors:
            if processor.can_process(file_path):
                return processor
        return None

    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process file using appropriate processor"""
        processor = self.get_processor(file_path)
        if processor:
            return processor.process(file_path)

        # Fallback for unsupported files
        print(f"No processor found for {file_path}")
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
    extensions = set()

    for processor in factory._processors:
        if hasattr(processor, "SUPPORTED_EXTENSIONS"):
            extensions.update(processor.SUPPORTED_EXTENSIONS)

    return extensions
