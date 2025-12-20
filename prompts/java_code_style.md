<code_style language="java">

# Java Code Style Guidelines

## General Principles
- Follow Oracle's Java Code Conventions and Google Java Style Guide
- Use English for all variable names, method names, comments, and documentation
- Prioritize code readability and maintainability
- Follow object-oriented programming principles

## Naming Conventions
- **Classes and Interfaces**: Use `PascalCase`
  - Examples: `UserManager`, `DatabaseConnection`, `PaymentProcessor`
  - Interfaces can optionally start with `I`: `IUserService`, `IRepository`
- **Methods and Variables**: Use `camelCase`
  - Examples: `getUserName()`, `calculateTotalPrice()`, `isValid`, `userAge`
- **Constants**: Use `UPPER_SNAKE_CASE`
  - Examples: `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`, `API_BASE_URL`
- **Packages**: Use lowercase with dots
  - Examples: `com.company.project.utils`, `org.example.service`
- **Generic Type Parameters**: Use single uppercase letters
  - Examples: `T`, `E`, `K`, `V`, `? extends T`, `? super T`

## Code Formatting
- **Indentation**: Use 4 spaces (no tabs)
- **Line length**: Maximum 100 characters
- **Braces**: Use K&R style (opening brace on same line)
  ```java
  if (condition) {
      // code here
  }
  
  public class MyClass {
      public void myMethod() {
          // implementation
      }
  }
  ```
- **Spacing**:
  - Space after keywords: `if (`, `for (`, `while (`, `catch (`
  - Space around operators: `a + b`, `x == y`, `i = 0`
  - Space after commas: `method(a, b, c)`
  - No space before semicolons: `for (int i = 0; i < 10; i++)`

## Import Organization
- **Import order**:
  1. Static imports
  2. `java.*` packages
  3. `javax.*` packages
  4. Third-party libraries (alphabetical)
  5. Your organization's packages
  - Separate each group with blank line
  ```java
  import static org.junit.Assert.*;
  
  import java.util.List;
  import java.util.ArrayList;
  
  import javax.servlet.http.HttpServletRequest;
  
  import com.google.common.collect.Lists;
  import org.springframework.stereotype.Service;
  
  import com.company.project.model.User;
  import com.company.project.service.UserService;
  ```
- **Avoid wildcard imports**: Use specific imports instead of `import java.util.*;`

## Documentation Standards
- **JavaDoc**: Use for all public classes, interfaces, and methods
  ```java
  /**
   * Calculates the distance between two geographical points.
   * 
   * @param lat1 Latitude of the first point
   * @param lon1 Longitude of the first point
   * @param lat2 Latitude of the second point
   * @param lon2 Longitude of the second point
   * @return The distance in kilometers
   * @throws IllegalArgumentException if any coordinate is invalid
   * 
   * @since 1.0
   * @author John Doe
   */
  public double calculateDistance(double lat1, double lon1, double lat2, double lon2) {
      // implementation
  }
  ```
- **Class JavaDoc**: Include purpose, usage examples, and important notes
  ```java
  /**
   * Manages user authentication and session handling.
   * 
   * <p>This class provides methods for user login, logout, and session validation.
   * It maintains user state and handles authentication tokens securely.
   * 
   * <p>Example usage:
   * <pre>
   * UserManager manager = new UserManager();
   * boolean success = manager.authenticateUser("username", "password");
   * </pre>
   * 
   * @since 1.0
   * @see User
   * @see Session
   */
  public class UserManager {
      // class implementation
  }
  ```
- **Inline comments**: Use `//` for single-line comments, explain why not what

## Modern Java Best Practices
- **Use modern Java features** (Java 8+):
  ```java
  // Streams and Lambda expressions
  List<String> activeUsers = users.stream()
      .filter(User::isActive)
      .map(User::getName)
      .collect(Collectors.toList());
  
  // Optional instead of null checks
  Optional<User> user = userRepository.findById(userId);
  user.ifPresent(u -> sendWelcomeEmail(u.getEmail()));
  
  // Try-with-resources
  try (BufferedReader reader = Files.newBufferedReader(path)) {
      return reader.lines().collect(Collectors.toList());
  }
  ```
- **Diamond operator**: Use `<>` for generic type inference
  ```java
  List<String> names = new ArrayList<>();  // Good
  Map<String, Integer> counts = new HashMap<>();  // Good
  ```
- **String operations**: Use `StringBuilder` for multiple concatenations
  ```java
  StringBuilder sb = new StringBuilder();
  for (String item : items) {
      sb.append(item).append(", ");
  }
  ```

## Object-Oriented Best Practices
- **Encapsulation**: Use private fields with public getters/setters
  ```java
  public class User {
      private String name;
      private int age;
      
      public String getName() { return name; }
      public void setName(String name) { this.name = name; }
  }
  ```
- **Immutable objects**: Make objects immutable when possible
  ```java
  public final class Point {
      private final int x;
      private final int y;
      
      public Point(int x, int y) {
          this.x = x;
          this.y = y;
      }
      
      public int getX() { return x; }
      public int getY() { return y; }
  }
  ```
- **Builder pattern**: For objects with many parameters
  ```java
  public class User {
      private User(Builder builder) {
          this.name = builder.name;
          this.email = builder.email;
      }
      
      public static class Builder {
          private String name;
          private String email;
          
          public Builder setName(String name) {
              this.name = name;
              return this;
          }
          
          public User build() {
              return new User(this);
          }
      }
  }
  ```

## Exception Handling
- **Specific exceptions**: Use specific exception types
  ```java
  public void processFile(String filename) throws FileNotFoundException, IOException {
      if (filename == null) {
          throw new IllegalArgumentException("Filename cannot be null");
      }
      // file processing
  }
  ```
- **Try-catch placement**: Catch exceptions at the appropriate level
- **Resource management**: Always use try-with-resources for closeable resources

## Collections and Generics
- **Use interfaces**: Declare collections using interface types
  ```java
  List<String> names = new ArrayList<>();  // Good
  Set<Integer> numbers = new HashSet<>();  // Good
  ```
- **Generic wildcards**: Use appropriately
  ```java
  List<? extends Number> numbers;  // Producer
  List<? super Integer> integers;  // Consumer
  ```

## Constants and Enums
- **Constants**: Group related constants in classes or interfaces
  ```java
  public final class Constants {
      public static final int MAX_USERS = 1000;
      public static final String DEFAULT_ENCODING = "UTF-8";
      
      private Constants() {} // Prevent instantiation
  }
  ```
- **Enums**: Use for fixed sets of constants
  ```java
  public enum UserRole {
      ADMIN("Administrator"),
      USER("Regular User"),
      GUEST("Guest User");
      
      private final String displayName;
      
      UserRole(String displayName) {
          this.displayName = displayName;
      }
      
      public String getDisplayName() {
          return displayName;
      }
  }
  ```

## File Organization
- **One public class per file**: File name should match the public class name
- **Package structure**: Organize packages by feature or layer
  ```
  com.company.project.
  ├── controller/
  ├── service/
  ├── repository/
  ├── model/
  └── util/
  ```

## Examples

### Good Code:
```java
package com.company.project.service;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;

import com.company.project.model.User;
import com.company.project.repository.UserRepository;

/**
 * Service class for managing user operations.
 * 
 * <p>Provides business logic for user management including
 * creation, updates, and retrieval operations.
 */
@Service
public class UserService {
    
    private final UserRepository userRepository;
    
    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }
    
    /**
     * Retrieves all active users from the system.
     * 
     * @return List of active users
     */
    public List<User> getActiveUsers() {
        return userRepository.findAll().stream()
            .filter(User::isActive)
            .collect(Collectors.toList());
    }
    
    /**
     * Finds a user by their unique identifier.
     * 
     * @param userId The unique identifier of the user
     * @return Optional containing the user if found
     * @throws IllegalArgumentException if userId is null or negative
     */
    public Optional<User> findUserById(Long userId) {
        if (userId == null || userId < 0) {
            throw new IllegalArgumentException("User ID must be positive");
        }
        return userRepository.findById(userId);
    }
}
```

### Bad Code:
```java
import java.util.*;
public class userservice{
String n;
public userservice(String name){n=name;}
public list getusers(){
return new arraylist();
}
}
```

</code_style>
