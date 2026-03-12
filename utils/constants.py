"""
Global constants for the project
Contains file patterns, configurations, and other shared constants
"""

from typing import Dict, List, Set

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

# Generate consolidated extension sets
_ALL_CODE_EXTENSIONS = set()
for extensions in LANGUAGE_EXTENSIONS.values():
    _ALL_CODE_EXTENSIONS.update(extensions)

# Add special extensions
_ALL_CODE_EXTENSIONS.update(
    {
        # Additional file types
        ".asm",
        ".s",
        ".S",  # Assembly
        ".proto",  # Protocol Buffers
        ".thrift",  # Thrift
        ".graphql",
        ".gql",  # GraphQL
        ".tf",
        ".tfvars",  # Terraform
        ".dockerfile",  # Docker
        ".mk",  # Make
        ".cmake",  # CMake
        ".gradle",  # Gradle
        ".sbt",  # SBT
        ".vim",  # Vim
        ".el",  # Emacs Lisp
        ".cfg",
        ".conf",
        ".config",
        ".ini",  # Configuration
        ".mod",
        ".sum",  # Go modules
        ".gemspec",  # Ruby gems
        ".vb",  # VB.NET
    }
)

CODE_EXTENSIONS: Set[str] = frozenset(_ALL_CODE_EXTENSIONS)

# =============================================================================
# Extended Language Mapping (for edge cases)
# =============================================================================

ADDITIONAL_LANGUAGE_EXTENSIONS: Dict[str, str] = {
    # Python variants
    ".pyi": "python",
    ".pyx": "python",
    # JavaScript variants
    ".mjs": "javascript",
    ".cjs": "javascript",
    # C++ variants
    ".cxx": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    # Other variants
    ".kts": "kotlin",
    ".vb": "vbnet",
    ".mod": "go",
    ".sum": "go",
    ".gemspec": "ruby",
    ".phtml": "php",
    ".mm": "objc",
    ".sc": "scala",
    ".cljs": "clojure",
    ".cljc": "clojure",
    ".edn": "clojure",
    ".lhs": "haskell",
    ".mli": "ocaml",
    ".ocaml": "ocaml",
    ".fsx": "fsharp",
    ".fsi": "fsharp",
    ".pm": "perl",
    ".perl": "perl",
    ".htm": "html",
    ".xhtml": "html",
    ".xsl": "xml",
    ".xslt": "xml",
    ".dockerfile": "dockerfile",
    ".mk": "make",
    ".cmake": "cmake",
    ".gradle": "gradle",
    ".sbt": "sbt",
    ".vimrc": "vim",
    ".emacs": "elisp",
    ".s": "assembly",
    ".S": "assembly",
    ".proto": "protobuf",
    ".thrift": "thrift",
    ".gql": "graphql",
    ".tfvars": "terraform",
    ".conf": "config",
    ".config": "config",
    ".ini": "config",
}


# Document file extensions
DOCUMENT_EXTENSIONS: Set[str] = frozenset({".md", ".markdown", ".txt", ".text", ".json", ".rst", ".asciidoc", ".adoc"})

# =============================================================================
# File Pattern Lists (for glob operations)
# =============================================================================


def _generate_code_patterns() -> List[str]:
    """Generate comprehensive code file patterns for glob operations"""
    patterns = []

    # Add patterns from language extensions
    for extensions in LANGUAGE_EXTENSIONS.values():
        patterns.extend(f"*{ext}" for ext in extensions)

    # Add additional patterns
    additional_patterns = [
        # Assembly
        "*.asm",
        "*.s",
        "*.S",
        # Protocol Buffers & APIs
        "*.proto",
        "*.thrift",
        "*.graphql",
        "*.gql",
        # Infrastructure
        "*.tf",
        "*.tfvars",
        "*.dockerfile",
        # Build systems
        "*.mk",
        "*.cmake",
        "*.gradle",
        "*.sbt",
        # Configuration
        "*.cfg",
        "*.conf",
        "*.config",
        "*.ini",
        # Special files (without extensions)
        "Dockerfile",
        "Makefile",
        "CMakeLists.txt",
        "build.gradle",
    ]

    patterns.extend(additional_patterns)
    return sorted(set(patterns))


def _generate_document_patterns() -> List[str]:
    """Generate document file patterns for glob operations"""
    return sorted([f"*{ext}" for ext in DOCUMENT_EXTENSIONS])


# Generate pattern lists
CODE_FILE_PATTERNS: List[str] = _generate_code_patterns()
DOCUMENT_FILE_PATTERNS: List[str] = _generate_document_patterns()

# =============================================================================
# Language Categories (for semantic grouping)
# =============================================================================

LANGUAGE_CATEGORIES: Dict[str, List[str]] = {
    "web_frontend": ["html", "css", "scss", "sass", "less", "javascript", "typescript"],
    "web_backend": ["python", "java", "csharp", "go", "rust", "php", "ruby"],
    "mobile": ["swift", "kotlin", "dart", "javascript"],
    "systems": ["c", "cpp", "rust", "go", "assembly"],
    "functional": ["haskell", "scala", "clojure", "ocaml", "fsharp", "elm"],
    "scripting": ["python", "ruby", "lua", "perl", "shell", "powershell"],
    "data_science": ["r", "julia", "python", "sql"],
    "markup": ["html", "xml", "yaml", "json", "toml", "markdown"],
    "config": ["yaml", "json", "toml", "config"],
}

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
        "javascript": "//",
        "typescript": "//",
        "java": "//",
        "cpp": "//",
        "c": "//",
        "csharp": "//",
        "go": "//",
        "rust": "//",
        "scala": "//",
        "sql": "--",
        "lua": "--",
        "haskell": "--",
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
        "css": "*/",
        "scss": "*/",
        "less": "*/",
    },
}

# =============================================================================
# Utility Functions
# =============================================================================


def get_language_from_extension(extension: str) -> str:
    """Get language name from file extension"""
    extension = extension.lower()

    # Check primary language extensions
    for lang, extensions in LANGUAGE_EXTENSIONS.items():
        if extension in extensions:
            return lang

    # Check additional mappings
    return ADDITIONAL_LANGUAGE_EXTENSIONS.get(extension, extension.lstrip(".") or "unknown")


def get_language_from_filename(filename: str) -> str:
    """Get language name from special filename"""
    return SPECIAL_FILENAMES.get(filename.lower(), "unknown")


def is_code_file(file_path: str) -> bool:
    """Check if file is a code file based on extension"""
    from pathlib import Path

    path = Path(file_path)
    extension = path.suffix.lower()

    if extension in CODE_EXTENSIONS:
        return True

    # Check special filenames
    filename = path.name.lower()
    return filename in SPECIAL_FILENAMES


def is_document_file(file_path: str) -> bool:
    """Check if file is a document file based on extension"""
    from pathlib import Path

    extension = Path(file_path).suffix.lower()
    return extension in DOCUMENT_EXTENSIONS


def get_language_category(language: str) -> List[str]:
    """Get categories that a language belongs to"""
    categories = []
    for category, languages in LANGUAGE_CATEGORIES.items():
        if language in languages:
            categories.append(category)
    return categories
