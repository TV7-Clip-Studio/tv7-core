---
description: Automatically exports Backend OpenAPI schema and updates the Flutter client.
---

# 1. Sync Backend to Flutter Workflow

// turbo-all

1.  Navigate to `tv7-fastapi-backend`.
2.  Export the latest `openapi.json`:
    ```bash
    # Assuming there's a script or make command
    make export-schema
    ```
3.  Navigate to `tv7-flutter-studio/forgotten_client`.
4.  Run the OpenAPI generator to update `forgotten_client_api`:
    ```bash
    # Placeholder for the actual generation command
    dart run build_runner build --delete-conflicting-outputs
    ```
5.  Check for build errors in `lib/api/generated`.
6.  If language version errors occur, update the SDK constraint in `pubspec.yaml` to match the generated code.
