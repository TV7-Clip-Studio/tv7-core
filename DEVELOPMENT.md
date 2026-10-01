# TV7 daily development

The product is a downloadable Studio. Engine performs heavy video work locally. Backend handles licensing, private approved assets, scheduling, and publishing. Start with the [architecture boundary](docs/architecture/downloadable-studio.md) and the [cohort roles](COHORT.md).

## Small daily loop

1. Pick one creator-visible slice and name its owner. Check the affected repo's `AGENTS.md`, current code, and relevant API contract.
2. Start the integrated browser test stack with `cd tv7-core && make dev-browser-up`. Confirm listeners with `make dev-browser-status`; open Studio at `http://127.0.0.1:8080/`.
3. Implement in the owning repo. Update Core OpenAPI/architecture only when the contract changes. Use a separate agent for an independent review or a disjoint component.
4. Run the owning repo's checks. Exercise the changed flow through the Studio UI and inspect real Backend/Engine responses or media output. `make precommit-context` validates Core changes.
5. Review `git diff --check` and `git status` in each changed repo. Commit and push deliberately, per repo, after reviewing the diff. Use `make status` for a workspace summary.
6. Stop the integrated stack with `make dev-browser-stop` when done.

`make help` lists the normal entry points. Conductor, Cockpit, `sync`, and bulk PR commands live in `Makefile.legacy` for opt-in historical/advanced workflows: `make -f Makefile.legacy <target>`. They are not prerequisites for ordinary development. In particular, legacy `review`, `batch-pr`, and `batch-pr-open` can mutate GitHub and are not part of this daily loop.

## Checks by component

| Component | Local check |
| --- | --- |
| Studio | `cd ../tv7-studio && make check`; package with `npm run desktop:build` when desktop behavior changes. |
| Engine | `cd ../tv7-engine && cargo test && cargo clippy --all-targets -- -D warnings`. |
| Backend | `cd ../tv7-backend && make check`. |
| Core | `make precommit-context`. |

For UI critique, use the optional Agy role in `COHORT.md`. For independent code review, use optional DeepSeek only after local checks. Neither provider should use MindDrift credentials or Claude.
