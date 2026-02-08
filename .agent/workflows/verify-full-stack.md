---
description: Runs all tests and checks across the entire TV7 stack.
---

# 2. Verify Full Stack Workflow

// turbo-all

1.  **Verify Backend**:
    - Navigate to `tv7-fastapi-backend`.
    - Run `make check`.
2.  **Verify Frontend**:
    - Navigate to `tv7-flutter-studio/forgotten_client`.
    - Run `flutter analyze`.
    - Run `flutter test`.
3.  **Cross-Check consistency**:
    - Verify that both projects are using the same API version.
