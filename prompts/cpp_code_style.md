<code_style language="cpp">

# C++ Code Style Guidelines

## General Principles
- Follow modern C++ standards (C++17 or later when possible)
- Prioritize code readability and maintainability
- Use English for all variable names, function names, comments, and documentation
- Follow RAII (Resource Acquisition Is Initialization) principles

## Naming Conventions
- **Variables and functions**: Use `snake_case`
  - Examples: `user_name`, `calculate_total_price()`, `is_valid`
- **Classes and structs**: Use `PascalCase`
  - Examples: `UserManager`, `DatabaseConnection`, `HttpClient`
- **Constants and enums**: Use `UPPER_SNAKE_CASE`
  - Examples: `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`, `API_BASE_URL`
- **Private member variables**: Suffix with underscore `_`
  - Examples: `name_`, `connection_`, `buffer_size_`
- **Namespaces**: Use `snake_case`
  - Examples: `network_utils`, `file_system`, `json_parser`
- **Template parameters**: Use `PascalCase` with `T` prefix for types
  - Examples: `TValue`, `TContainer`, `TPolicy`

## Code Formatting
- **Indentation**: Use 4 spaces (no tabs)
- **Line length**: Maximum 100 characters
- **Braces**: Use K&R style (opening brace on same line)
  ```cpp
  if (condition) {
      // code here
  }
  
  class MyClass {
  public:
      void my_method() {
          // implementation
      }
  };
  ```
- **Spacing**:
  - Space after keywords: `if (`, `for (`, `while (`
  - Space around operators: `a + b`, `x == y`, `i = 0`
  - No space before semicolons or commas
  - Space after commas: `func(a, b, c)`

## Header Files
- **Include guards**: Use `#pragma once` at the top of header files
- **Include order**:
  1. Corresponding header file (for .cpp files)
  2. Standard library headers
  3. Third-party library headers  
  4. Project headers
  - Separate each group with blank line
  ```cpp
  #pragma once
  
  #include <iostream>
  #include <vector>
  #include <string>
  
  #include <boost/algorithm/string.hpp>
  
  #include "user_manager.h"
  #include "database.h"
  ```

## Documentation Standards
- **Function documentation**: Use Doxygen-style comments
  ```cpp
  /**
   * Calculate the Euclidean distance between two points.
   * 
   * @param x1 X coordinate of first point
   * @param y1 Y coordinate of first point  
   * @param x2 X coordinate of second point
   * @param y2 Y coordinate of second point
   * @return The Euclidean distance between the two points
   * 
   * @example
   * double dist = calculate_distance(0.0, 0.0, 3.0, 4.0); // returns 5.0
   */
  double calculate_distance(double x1, double y1, double x2, double y2);
  ```
- **Class documentation**: Document purpose and key members
  ```cpp
  /**
   * Manages user authentication and session handling.
   * 
   * This class provides methods for user login, logout, and session validation.
   * It maintains user state and handles authentication tokens.
   */
  class UserManager
  {
      // class implementation
  };
  ```
- **Inline comments**: Use `//` for single-line comments, explain why not what

## Modern C++ Best Practices
- **Auto keyword**: Use `auto` for type deduction when type is obvious
  ```cpp
  auto users = get_user_list();  // Good when return type is clear
  auto count = static_cast<int>(users.size());  // Explicit when needed
  ```
- **Smart pointers**: Prefer smart pointers over raw pointers
  ```cpp
  std::unique_ptr<Database> db = std::make_unique<Database>();
  std::shared_ptr<Config> config = std::make_shared<Config>();
  ```
- **Range-based loops**: Use when iterating over containers
  ```cpp
  for (const auto& user : users) {
      process_user(user);
  }
  ```
- **Const correctness**: Use `const` whenever possible
  ```cpp
  const std::string& get_name() const { return name_; }
  void process_data(const std::vector<int>& data);
  ```

## Memory Management
- **RAII**: Use constructors/destructors for resource management
- **Avoid manual memory management**: Use containers and smart pointers
- **Exception safety**: Follow strong exception safety guarantee when possible
- **Move semantics**: Implement move constructors and assignment operators for heavy objects

## Error Handling
- **Exceptions**: Use exceptions for error handling, not error codes
- **Exception types**: Use standard exceptions or create specific exception classes
  ```cpp
  class DatabaseException : public std::runtime_error {
  public:
      explicit DatabaseException(const std::string& message)
          : std::runtime_error(message) {}
  };
  ```
- **RAII with exceptions**: Ensure proper cleanup even when exceptions occur

## File Organization
- **Header files (.h)**: Declarations, inline functions, templates
- **Source files (.cpp)**: Implementations, static variables
- **One class per file**: Generally one main class per header/source pair
- **Logical grouping**: Group related functionality in the same namespace

## Examples

### Good Code:
```cpp
#pragma once

#include <string>
#include <vector>
#include <memory>

namespace user_management {
    /**
     * Represents a user in the system.
     */
    class User {
    public:
        User(const std::string& name, int age);
        
        const std::string& get_name() const { return name_; }
        int get_age() const { return age_; }
        
        void set_age(int new_age);
        
    private:
        std::string name_;
        int age_;
    };
    
    /**
     * Manages a collection of users.
     */
    class UserManager {
    public:
        void add_user(std::unique_ptr<User> user);
        const User* find_user(const std::string& name) const;
        
    private:
        std::vector<std::unique_ptr<User>> users_;
    };
}
```

### Bad Code:
```cpp
#include<string>
#include<vector>
class user{
public:
string name;int age;
user(string n,int a):name(n),age(a){}
void setAge(int a){age=a;}
};
```

</code_style>