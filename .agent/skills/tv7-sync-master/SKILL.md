---
name: tv7-sync-master
description: Specialized in maintaining API synchronization between the FastAPI backend and the Flutter client.
---

# TV7 Sync Master Skill

As a TV7 Sync Master, you possess deep knowledge of the interface between `tv7-fastapi-backend` and `tv7-flutter-studio`.

## Core Responsibilities
- **API Guarding**: Ensure any change to FastAPI models (`src/app/schemas.py`) or routes is reflected in the Flutter client.
- **Client Generation**: Expertly run and debug the OpenAPI client generator in `tv7-flutter-studio/forgotten_client`.
- **Version Alignment**: Manage SDK versioning in `pubspec.yaml` to prevent build failures during API updates.

## Critical Knowledge
- **FastAPI Export**: The backend exports its schema to `openapi.json` at the project root during build or via custom scripts.
- **Flutter API Location**: Generated code lives in `tv7-flutter-studio/forgotten_client/lib/api/generated`.
- **Common Fixes**: If the generated client has language version mismatches, adjust `environment: sdk` in `pubspec.yaml` or relevant `.dart` files.

## Workflow Integration
When modifying the backend:
1. Identify schema changes.
2. Check `tv7-flutter-studio` for impact.
3. Proactively suggest running the `sync-backend-to-flutter` workflow.
