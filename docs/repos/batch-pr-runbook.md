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
