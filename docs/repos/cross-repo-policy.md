# Cross-Repo Change Policy

Use this policy when one feature touches more than one repository.

## Required Rules
- Link related PRs in every PR description.
- Keep interface/contract changes explicit (OpenAPI, docs, schema changes).
- Land contract producer changes before consumer changes when compatibility is not backward-safe.
- If backward-safe, producer/consumer PRs may merge in any order but must reference each other.

## Recommended Order
1. Update contract artifacts in `tv7-core/docs/contracts/...`.
2. Update producer repo implementation.
3. Update consumer repos.
4. Update shared docs/roadmaps in `tv7-core`.

## Compatibility Notes
- For breaking changes, include migration notes in PR descriptions.
- For non-breaking changes, identify fallback behavior and rollout assumptions.
- Use one batch branch/PR per repo; do not mix unrelated work.

## Reviewer Expectations
- Confirm linked PR list is complete.
- Confirm contract artifact updates are present when API changes exist.
- Confirm each repo passes its configured check command.

