# Naming Conventions (Cross-Repo)

Repos
- Prefix with `tv7-` and a clear domain: `tv7-axum-engine`, `tv7-fastapi-backend`, `tv7-flutter-studio`, `tv7-astro-site`, `tv7-core`.
- Submodule mount path is `00-tv7-core/` for visibility and stability.

Branches
- Feature branches: `feat/<scope>`, bugfix: `fix/<scope>`, chores: `chore/<scope>`.
- Release branches (if used): `release/<version>`.

Tags/versions
- Use SemVer per repo (see `versioning.md`).

Docs
- Cross-repo/system docs live in `00-tv7-core/architecture|standards|meta|tooling|templates`.
- Repo-specific docs live in that repo under `docs-local/`.
