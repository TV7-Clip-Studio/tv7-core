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
- `OPEN_PR=0` - disable PR creation for a run.
- `PUSH_BRANCH=0` - disable push for a run.
- `RUN_CHECKS_IN_ALL_REPOS=0` - check only changed repos.

## Config Source
- `tooling/repos-checks.conf` is the source of truth for repo check/base mappings.

