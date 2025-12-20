<code_style language="python">

# Python Code Style Guidelines

## General Principles

- All Python code must use English for variable names, function names, comments, and documentation
- Follow PEP 8 standards as the foundation for code style
- Prioritize code readability and maintainability

## Naming Conventions

- **Variables and functions**: Use `snake_case`
  - Examples: `user_name`, `calculate_total_price()`, `is_valid`
- **Classes**: Use `PascalCase`
  - Examples: `UserManager`, `DatabaseConnection`, `HttpClient`
- **Constants**: Use `UPPER_SNAKE_CASE`
  - Examples: `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`, `API_BASE_URL`
- **Private attributes/methods**: Prefix with single underscore `_`
  - Examples: `_internal_method()`, `_private_variable`
- **Module names**: Use lowercase with underscores
  - Examples: `user_manager.py`, `database_utils.py`

## Documentation Standards

- **Docstrings**: Always use triple single quotes `'''` instead of triple double quotes `"""`
- **Function docstrings**: Include purpose, parameters, return values, and examples when helpful

  ```python
  def calculate_distance(x1, y1, x2, y2):
      '''
      Calculate the Euclidean distance between two points.

      Args:
          x1 (float): X coordinate of first point
          y1 (float): Y coordinate of first point
          x2 (float): X coordinate of second point
          y2 (float): Y coordinate of second point

      Returns:
          float: The Euclidean distance between the two points

      Example:
          >>> calculate_distance(0, 0, 3, 4)
          5.0
      '''
  ```

- **Class docstrings**: Describe the class purpose and key attributes/methods
- **Module docstrings**: Include at the top of each module to describe its purpose

## Code Formatting

- **Line length**: Maximum 88 characters (compatible with Black formatter)
- **Imports**:

  - Standard library imports first
  - Third-party imports second
  - Local application imports last
  - Separate each group with a blank line

  ```python
  #standard library
  import os
  import sys

  #third party
  import requests
  import numpy as np

  #local package
  from .utils import helper_function
  from .models import User
  ```

- **Blank lines**:
  - Two blank lines before top-level class and function definitions
  - One blank line before method definitions inside classes
- **Indentation**: Use 4 spaces (no tabs)
- **String quotes**: Use single quotes `'` for strings, unless the string contains single quotes

## Best Practices

- **Type hints**: Use type hints for function parameters and return values
  ```python
  def process_user_data(user_id: int, data: dict[str, Any]) -> bool:
      '''Process user data and return success status.'''
  ```
- **Error handling**: Use specific exception types, avoid bare `except:` clauses
- **Function design**: Keep functions small and focused on a single responsibility
- **Variable naming**: Use descriptive names, avoid single-letter variables except for loops
- **Comments**: Write comments that explain why, not what
- **Boolean variables**: Use descriptive names with `is_`, `has_`, `can_`, `should_`, `use_` prefixes
  - Examples: `is_valid`, `has_permission`, `can_access`, `should_retry`, `use_cache`

## File Organization

- **Module structure**: Order contents as follows:
  1. Module docstring
  2. Imports
  3. Constants
  4. Classes
  5. Functions
  6. Main execution block (`if __name__ == '__main__':`)

## Examples of Good vs Bad Code

### Good:

```python
def validate_email_address(email: str) -> bool:
    '''
    Validate if the provided email address is in correct format.

    Args:
        email (str): Email address to validate

    Returns:
        bool: True if email is valid, False otherwise
    '''
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

### Bad:

```python
def checkEmail(e):
    """Check email"""
    import re
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', e))
```

</code_style>
