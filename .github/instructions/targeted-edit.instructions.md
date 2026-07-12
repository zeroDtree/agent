---
description: "Use when: modifying existing code files. Enforces targeted inline edits via replace_string_in_file, forbids full file rewrites, and requires exact whitespace/indentation matching with sufficient context lines."
applyTo: "**"
---

# Targeted Edit Rules

## 1. Core Principle: No Full File Rewrites

- **Prioritize Local Tools:** Unless creating a brand-new file, you **MUST** prioritize using `replace_string_in_file` (or equivalent local edit tools) when modifying existing code.
- **Do Not Abuse Creation Tools:** Never use `create_file` or output the entire file's source code to overwrite an existing file.

## 2. Exact Matching Requirements

- **Strict Alignment:** When performing a local replacement, you must exactly match the whitespace, indentation (Tabs/Spaces), and line endings of the target area.
- **Sufficient Context:** The replacement block must include **at least 2-3 lines of unchanged code before and after** the target modification to ensure uniqueness and prevent matching failures.

## 3. Code Modification Protocol

When a modification request is received, follow these steps strictly:

1. **Locate:** Pinpoint the exact code block to modify using the file name, class/function/method name, or line numbers.
2. **Extract:** Isolate only the specific code snippet that needs changes.
3. **Replace:** Apply the changes with the **minimal diff possible**, leaving 100% of the rest of the file untouched.

## 4. Fallback Strategy & Exception Handling

- If `replace_string_in_file` fails due to indentation mismatch or ambiguous context, **DO NOT fallback to a full file rewrite.**
- **Correct Action:** Ask the user for clarification first. Respond with: *"I could not apply a targeted edit due to ambiguous context. Please provide more surrounding code or explicit line numbers for this section."*

## Golden Rule

> ⚠️ **IMPORTANT:** Use `replace_string_in_file` for a targeted inline edit. Provide sufficient context lines and ensure exact matching. **DO NOT rewrite or output the entire file.**
