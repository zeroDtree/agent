import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class GitIgnoreChecker:
    """Git-based ignore checker using 'git check-ignore' command"""

    def __init__(self, working_directory: Optional[Path] = None):
        """
        Initialize Git ignore checker

        Args:
            working_directory: Directory where git commands should be run (default: current directory)
        """
        self.working_directory = working_directory or Path.cwd()
        self._git_available = self._check_git_available()

        if self._git_available:
            print(
                f"Git ignore checker initialized for directory: {self.working_directory} which will be used when source_root is not provided"
            )
        else:
            print("Git not available or not in a git repository")

    def _check_git_available(self) -> bool:
        """Check if git is available and we're in a git repository"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def should_ignore(self, file_path: Path, source_root: Optional[Path] = None) -> bool:
        """Check if file should be ignored using git check-ignore"""
        if not self._git_available:
            return False

        try:
            # Use source_root as working directory if provided, otherwise use
            # default
            git_cwd = source_root if source_root else self.working_directory

            # Convert to relative path from git working directory
            try:
                relative_to_wd = file_path.relative_to(git_cwd)
                path_for_git = str(relative_to_wd)
            except ValueError:
                # File is outside git working directory, use absolute path
                path_for_git = str(file_path)

            # Run git check-ignore
            result = subprocess.run(
                ["git", "check-ignore", path_for_git],
                cwd=git_cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Return code 0 means file is ignored
            return result.returncode == 0

        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            print(f"Git check-ignore failed for {file_path}: {e}")
            return False

    def check_multiple_files(self, file_paths: List[Path], source_root: Optional[Path] = None) -> Dict[str, bool]:
        """Check multiple files at once for better performance"""
        if not self._git_available or not file_paths:
            return {str(path): False for path in file_paths}

        try:
            # Prepare paths for git
            git_paths = []
            path_mapping = {}

            # Use source_root as working directory if provided, otherwise use
            # default
            git_cwd = source_root if source_root else self.working_directory

            for file_path in file_paths:
                try:
                    # Convert to relative path from git working directory
                    relative_to_wd = file_path.relative_to(git_cwd)
                    path_for_git = str(relative_to_wd)
                except ValueError:
                    # File is outside git working directory, use absolute path
                    path_for_git = str(file_path)

                git_paths.append(path_for_git)
                path_mapping[path_for_git] = str(file_path)

            # Run git check-ignore with stdin
            git_input = "\n".join(git_paths)
            result = subprocess.run(
                ["git", "check-ignore", "--stdin"],
                input=git_input,
                cwd=git_cwd,
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Parse results
            ignored_paths = set()
            if result.returncode == 0 and result.stdout.strip():
                ignored_paths = set(result.stdout.strip().split("\n"))

            # Build result mapping
            results = {}
            for git_path in git_paths:
                original_path = path_mapping[git_path]
                results[original_path] = git_path in ignored_paths

            return results

        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            print(f"Git check-ignore batch failed: {e}")
            return {str(path): False for path in file_paths}

    def get_ignore_info(self, file_path: Path, source_root: Optional[Path] = None) -> Optional[Dict[str, str]]:
        """Get detailed ignore information including which pattern matched"""
        if not self._git_available:
            return None

        try:
            # Use source_root as working directory if provided, otherwise use
            # default
            git_cwd = source_root if source_root else self.working_directory

            # Convert to relative path from git working directory
            try:
                relative_to_wd = file_path.relative_to(git_cwd)
                path_for_git = str(relative_to_wd)
            except ValueError:
                # File is outside git working directory, use absolute path
                path_for_git = str(file_path)

            # Run git check-ignore with verbose output
            result = subprocess.run(
                ["git", "check-ignore", "--verbose", path_for_git],
                cwd=git_cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout:
                # Parse verbose output: <source>:<linenum>:<pattern> <tab>
                # <pathname>
                line = result.stdout.strip()
                if "\t" in line:
                    pattern_info, pathname = line.split("\t", 1)
                    parts = pattern_info.split(":", 2)
                    if len(parts) >= 3:
                        return {
                            "source_file": parts[0],
                            "line_number": parts[1],
                            "pattern": parts[2],
                            "pathname": pathname,
                            "ignored": True,
                        }

            return {"ignored": False}

        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            print(f"Git check-ignore verbose failed for {file_path}: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Git ignore checker is available"""
        return self._git_available
