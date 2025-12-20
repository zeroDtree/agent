import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(name=__name__)


class FilterOrder(Enum):
    """Order of applying exclude and include filters"""

    # Apply exclude patterns first, then include patterns
    EXCLUDE_FIRST = "exclude_first"
    # Apply include patterns first, then exclude patterns
    INCLUDE_FIRST = "include_first"


class RegexPatternFilter:
    """Advanced regex-based file pattern filter supporting include/exclude patterns with configurable order"""

    def __init__(
        self,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        filter_order: FilterOrder = FilterOrder.EXCLUDE_FIRST,
    ):
        """
        Initialize regex pattern filter

        Args:
            exclude_patterns: List of regex patterns to exclude files
            include_patterns: List of regex patterns to include files
            filter_order: Order to apply exclude/include filters
        """
        self.exclude_patterns = exclude_patterns or []
        self.include_patterns = include_patterns or []
        self.filter_order = filter_order

        # Compile regex patterns for better performance
        self.compiled_exclude_patterns = []
        self.compiled_include_patterns = []

        # Compile exclude patterns
        for pattern in self.exclude_patterns:
            try:
                compiled_pattern = re.compile(pattern)
                self.compiled_exclude_patterns.append(compiled_pattern)
                logger.debug(f"Compiled exclude pattern: {pattern}")
            except re.error as e:
                logger.warning(f"Invalid exclude regex pattern '{pattern}': {e}")

        # Compile include patterns
        for pattern in self.include_patterns:
            try:
                compiled_pattern = re.compile(pattern)
                self.compiled_include_patterns.append(compiled_pattern)
                logger.debug(f"Compiled include pattern: {pattern}")
            except re.error as e:
                logger.warning(f"Invalid include regex pattern '{pattern}': {e}")

        logger.info(
            f"RegexPatternFilter initialized with {len(self.compiled_exclude_patterns)} exclude patterns, "
            f"{len(self.compiled_include_patterns)} include patterns, order: {filter_order.value}"
        )

    def should_include_file(self, file_path: Path, source_root: Optional[Path] = None) -> bool:
        """
        Determine if file should be included based on patterns and filter order

        Args:
            file_path: Path to the file to check
            source_root: Root directory for relative path calculation

        Returns:
            True if file should be included, False otherwise
        """
        # Get relative path for pattern matching
        if source_root and file_path.is_absolute():
            try:
                relative_path = file_path.relative_to(source_root)
                path_str = str(relative_path)
            except ValueError:
                # File is outside source root, use absolute path
                path_str = str(file_path)
        else:
            path_str = str(file_path)

        # Normalize path separators for cross-platform compatibility
        path_str = path_str.replace("\\", "/")

        if self.filter_order == FilterOrder.EXCLUDE_FIRST:
            return self._apply_exclude_first(path_str)
        else:
            return self._apply_include_first(path_str)

    def _apply_exclude_first(self, path_str: str) -> bool:
        """Apply exclude patterns first, then include patterns"""
        # Step 1: Check exclude patterns - if any matches, file is excluded
        for pattern in self.compiled_exclude_patterns:
            if pattern.search(path_str):
                logger.debug(f"File excluded by pattern {pattern.pattern}: {path_str}")

                # Step 2: Check if any include pattern overrides the exclusion
                for include_pattern in self.compiled_include_patterns:
                    if include_pattern.search(path_str):
                        logger.debug(f"File re-included by pattern {include_pattern.pattern}: {path_str}")
                        return True

                # No include pattern matched, file remains excluded
                return False

        # Step 3: No exclude pattern matched
        # If we have include patterns, file must match at least one to be
        # included
        if self.compiled_include_patterns:
            for pattern in self.compiled_include_patterns:
                if pattern.search(path_str):
                    logger.debug(f"File included by pattern {pattern.pattern}: {path_str}")
                    return True

            # No include pattern matched, file is excluded
            logger.debug(f"File excluded (no include pattern matched): {path_str}")
            return False

        # No exclude patterns matched and no include patterns defined, file is
        # included
        return True

    def _apply_include_first(self, path_str: str) -> bool:
        """Apply include patterns first, then exclude patterns"""
        # Step 1: If we have include patterns, file must match at least one
        if self.compiled_include_patterns:
            include_matched = False
            for pattern in self.compiled_include_patterns:
                if pattern.search(path_str):
                    logger.debug(f"File included by pattern {pattern.pattern}: {path_str}")
                    include_matched = True
                    break

            if not include_matched:
                logger.debug(f"File excluded (no include pattern matched): {path_str}")
                return False

        # Step 2: Check exclude patterns - if any matches, file is excluded
        for pattern in self.compiled_exclude_patterns:
            if pattern.search(path_str):
                logger.debug(f"File excluded by pattern {pattern.pattern}: {path_str}")
                return False

        # File passed all filters
        return True

    def check_multiple_files(self, file_paths: List[Path], source_root: Optional[Path] = None) -> Dict[str, bool]:
        """Check multiple files at once for better performance"""
        results = {}
        for file_path in file_paths:
            results[str(file_path)] = self.should_include_file(file_path, source_root)
        return results

    def get_filter_info(self) -> Dict[str, Any]:
        """Get information about current filter configuration"""
        return {
            "exclude_patterns": self.exclude_patterns,
            "include_patterns": self.include_patterns,
            "filter_order": self.filter_order.value,
            "compiled_exclude_count": len(self.compiled_exclude_patterns),
            "compiled_include_count": len(self.compiled_include_patterns),
        }
