"""
Global constants for the project
Contains file patterns, configurations, and other shared constants
"""

from typing import Dict, FrozenSet, List

# =============================================================================
# Core Language Support Matrix
# =============================================================================

# Primary language-to-extensions mapping
LANGUAGE_EXTENSIONS: Dict[str, List[str]] = {
    # Web Technologies
    "html": [".html", ".htm", ".xhtml"],
    "css": [".css"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    # Backend Languages
    "python": [".py", ".pyi", ".pyx"],
    "java": [".java"],
    "csharp": [".cs"],
    "go": [".go"],
    "rust": [".rs"],
    "php": [".php", ".phtml"],
    # Systems Programming
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cxx", ".cc", ".hpp", ".hxx"],
    # Mobile Development
    "swift": [".swift"],
    "kotlin": [".kt", ".kts"],
    "dart": [".dart"],
    # Functional Languages
    "haskell": [".hs", ".lhs"],
    "scala": [".scala", ".sc"],
    "clojure": [".clj", ".cljs", ".cljc", ".edn"],
    "ocaml": [".ml", ".mli", ".ocaml"],
    "fsharp": [".fs", ".fsx", ".fsi"],
    "elm": [".elm"],
    # Scripting Languages
    "ruby": [".rb"],
    "lua": [".lua"],
    "perl": [".pl", ".pm", ".perl"],
    "shell": [".sh", ".bash", ".zsh", ".fish"],
    "powershell": [".ps1", ".psm1"],
    # Data & Science
    "r": [".r", ".R"],
    "julia": [".jl"],
    "sql": [".sql"],
    # Markup & Data
    "yaml": [".yaml", ".yml"],
    "xml": [".xml", ".xsl", ".xslt"],
    "json": [".json"],
    "toml": [".toml"],
    # CSS Preprocessors
    "scss": [".scss"],
    "sass": [".sass"],
    "less": [".less"],
}

# Special file name patterns (case-insensitive)
SPECIAL_FILENAMES: Dict[str, str] = {
    # Build Systems
    "makefile": "make",
    "cmake": "cmake",
    "cmakelists.txt": "cmake",
    "build.gradle": "gradle",
    "build.gradle.kts": "kotlin",
    # Package Managers
    "package.json": "json",
    "composer.json": "json",
    "cargo.toml": "toml",
    "pyproject.toml": "toml",
    "requirements.txt": "text",
    "gemfile": "ruby",
    "gemfile.lock": "text",
    "pipfile": "toml",
    # Configuration
    "dockerfile": "dockerfile",
    "vagrantfile": "ruby",
    "rakefile": "ruby",
    ".gitignore": "text",
    ".env": "text",
    # Editor Configs
    ".vimrc": "vim",
    ".emacs": "elisp",
}

# =============================================================================
# File Extension Sets (for fast lookups)
# =============================================================================

# Build the extension→language reverse map in a single pass
_EXTENSION_TO_LANGUAGE: Dict[str, str] = {}
for _lang, _exts in LANGUAGE_EXTENSIONS.items():
    for _ext in _exts:
        _EXTENSION_TO_LANGUAGE[_ext] = _lang

# Extra extensions not covered by LANGUAGE_EXTENSIONS
_EXTRA_EXTENSIONS: Dict[str, str] = {
    ".asm": "assembly",
    ".s": "assembly",
    ".S": "assembly",
    ".proto": "protobuf",
    ".thrift": "thrift",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".tf": "terraform",
    ".tfvars": "terraform",
    ".dockerfile": "dockerfile",
    ".mk": "make",
    ".cmake": "cmake",
    ".gradle": "gradle",
    ".sbt": "sbt",
    ".vim": "vim",
    ".el": "elisp",
    ".cfg": "config",
    ".conf": "config",
    ".config": "config",
    ".ini": "config",
    ".mod": "go",
    ".sum": "go",
    ".gemspec": "ruby",
    ".vb": "vbnet",
    ".mm": "objc",
    ".vimrc": "vim",
    ".emacs": "elisp",
}

_EXTENSION_TO_LANGUAGE.update(_EXTRA_EXTENSIONS)

# Immutable set of all known code extensions
CODE_EXTENSIONS: FrozenSet[str] = frozenset(_EXTENSION_TO_LANGUAGE)

# Document file extensions
DOCUMENT_EXTENSIONS: FrozenSet[str] = frozenset(
    {".md", ".markdown", ".txt", ".text", ".json", ".rst", ".asciidoc", ".adoc"}
)

# =============================================================================
# Comment Patterns (for metadata extraction)
# =============================================================================

COMMENT_PATTERNS: Dict[str, Dict[str, str]] = {
    "single_line": {
        "python": "#",
        "ruby": "#",
        "perl": "#",
        "r": "#",
        "shell": "#",
        "powershell": "#",
        "cmake": "#",
        "make": "#",
        "toml": "#",
        "yaml": "#",
        "dockerfile": "#",
        "coffeescript": "#",
        "javascript": "//",
        "typescript": "//",
        "java": "//",
        "cpp": "//",
        "c": "//",
        "csharp": "//",
        "go": "//",
        "rust": "//",
        "scala": "//",
        "kotlin": "//",
        "swift": "//",
        "dart": "//",
        "php": "//",
        "objc": "//",
        "sql": "--",
        "lua": "--",
        "haskell": "--",
        "elm": "--",
        "fsharp": "//",
    },
    "block_start": {
        "javascript": "/*",
        "typescript": "/*",
        "java": "/*",
        "cpp": "/*",
        "c": "/*",
        "csharp": "/*",
        "go": "/*",
        "rust": "/*",
        "scala": "/*",
        "kotlin": "/*",
        "swift": "/*",
        "dart": "/*",
        "php": "/*",
        "objc": "/*",
        "css": "/*",
        "scss": "/*",
        "less": "/*",
    },
    "block_end": {
        "javascript": "*/",
        "typescript": "*/",
        "java": "*/",
        "cpp": "*/",
        "c": "*/",
        "csharp": "*/",
        "go": "*/",
        "rust": "*/",
        "scala": "*/",
        "kotlin": "*/",
        "swift": "*/",
        "dart": "*/",
        "php": "*/",
        "objc": "*/",
        "css": "*/",
        "scss": "*/",
        "less": "*/",
    },
}

# =============================================================================
# Utility Functions
# =============================================================================


def get_language_from_extension(extension: str) -> str:
    """Get language name from file extension."""
    return _EXTENSION_TO_LANGUAGE.get(extension.lower(), extension.lstrip(".") or "unknown")


def get_language_from_filename(filename: str) -> str:
    """Get language name from special filename."""
    return SPECIAL_FILENAMES.get(filename.lower(), "unknown")


def is_code_file(file_path: str) -> bool:
    """Check if file is a code file based on extension or special filename."""
    from pathlib import Path

    path = Path(file_path)
    if path.suffix.lower() in CODE_EXTENSIONS:
        return True
    return path.name.lower() in SPECIAL_FILENAMES


def is_document_file(file_path: str) -> bool:
    """Check if file is a document file based on extension."""
    from pathlib import Path

    return Path(file_path).suffix.lower() in DOCUMENT_EXTENSIONS
