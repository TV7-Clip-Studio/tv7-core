# Batch PR Runbook

## Standard Run
```bash
cd tv7-core
make batch-pr
```

## Dry Run
```bash
cd tv7-core
make batch-pr-dry-run
```

## Status Dashboard
```bash
cd tv7-core
make batch-pr-report
```

## Failure Handling
- Check summary output from `batch-pr.sh` for failing repo and command.
- Fix that repo in place.
- Re-run `make batch-pr` (it skips repos without new changes).
- If PR status shows `EXISTS`, `batch-pr.sh` found an open PR for the current branch and will not create another one.
- If a previous PR on the same branch was `MERGED` or `CLOSED`, `batch-pr.sh` now creates a fresh PR for new commits on that branch.

## DeepSeek Follow-up (Collect)
```bash
cd tv7-core
make deepseek-followup
```

Prerequisite:
- Python 3.11+

Outputs:
- `docs/.tmp/deepseek-followup.json` (machine-readable queue)
- `docs/.tmp/deepseek-followup.md` (operator summary)

Useful knobs:
- `BATCH_ID=...` to focus on one batch branch suffix.
- `ONLY_ACTIONABLE=1` to keep only findings requiring action.
- `FAIL_ON_ACTIONABLE=1` to return non-zero if any actionable findings remain.
- `INCLUDE_RECOMMENDATIONS=1` (default) treats recommendation-style feedback as actionable; set `0` for strict mode (only rejected/request-changes style findings).
- Default behavior: if current branch matches `codex/batch-tv7-core-<suffix>`, Make auto-sets `BATCH_ID=<suffix>`.

## DeepSeek Follow-up (Prepare Fix Queue)
```bash
cd tv7-core
make deepseek-fix
```

This command:
- Runs `tooling/deepseek_followup.py` twice:
  - Full snapshot: `docs/.tmp/deepseek-followup.json`
  - Actionable-only snapshot: `docs/.tmp/deepseek-followup-actionable.json`
- Builds per-repo prompt bundles in `docs/.tmp/deepseek-fix-prompts`:
  - `<repo>-pr-<number>.md` (agent prompt)
  - `<repo>-pr-<number>.comments.json` (full comment payload for that PR)
- Writes queue summary to `docs/.tmp/deepseek-fix-plan.md`.

Execution model:
- Use each repo agent to process the prompt generated for that repo.
- This keeps fixes scoped to repo-local context and tooling.

## Environment Knobs
- `COMMIT_MESSAGE` - override commit message.
- `BATCH_ID` - pin run id used in branch names.
- `TASK_ID` + `CHANGE_TITLE` - set canonical subject (`[TASK_ID] CHANGE_TITLE`) for commit/PR title when provided together.
- `PR_TITLE` - override PR title explicitly.
- `PR_BODY` - provide PR description inline.
- `PR_BODY_FILE` - provide PR description from file path.
- `OPEN_PR=0` - disable PR creation for a run.
- `PUSH_BRANCH=0` - disable push for a run.
- `RUN_CHECKS_IN_ALL_REPOS=0` - check only changed repos.
- `BRANCH_PREFIX` - override default branch prefix (`codex/batch`).
- `LIMIT` - number of PRs inspected per repo for DeepSeek follow-up commands.

## Metadata Example
```bash
cd tv7-core
TASK_ID=TV7-128 \
CHANGE_TITLE="Harden batch PR metadata flow" \
PR_BODY_FILE=docs/pr-template.md \
make batch-pr
```

## Config Source
- `tooling/repos-checks.conf` is the source of truth for repo check/base mappings.
