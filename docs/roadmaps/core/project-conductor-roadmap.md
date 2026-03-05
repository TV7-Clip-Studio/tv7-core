# Project Conductor Roadmap

Roadmap Code: CO
Batch Code: C01
Last updated: 2026-03-01

## Project Summary
Project Conductor migrates TV7 from the current custom local orchestrator to a structured multi-agent pipeline using LangGraph + Composio execution, while preserving deterministic IDs, strict state transitions, and DeepSeek quality gates.

## Success Criteria
- Every work item flows through a strict lifecycle: `seeded -> expanded -> executing -> review_failed/review_passed -> integrated -> done`.
- Ticket creation is deterministic, idempotent, and scoped (`repo`, `roadmap`, `item-prefix`) with no accidental global runs.
- Issue bodies start minimal in `seed` stage and are enriched only in `expand` stage.
- `make conductor-run` supports all-repo mode and single-repo mode.
- Migration is gated: no old orchestrator removal until two full clean batches pass with zero blocking regressions.

## Scope
- In: roadmap ingestion, issue lifecycle, agent handoff, review loop, run command, observability, rollback.
- Out: background daemonization, automatic production deploys, PR auto-merge.

## Phase 1: Program Charter And Controls
- [X] [CO-C01-01-01] Define migration charter, goals, and non-goals for Project Conductor.
    **COMPLETED** | Architect Agent | 2026-02-28 09:41
    - **NOTE**: Deliverables: charter doc with architecture decision, success metrics, and explicit exclusions.
    - **NOTE**: Acceptance: all stakeholders agree on target flow and deprecation criteria.
    - **NOTE**: Validation: review walkthrough in `tv7-core/docs/repos/core/project-conductor-runbook.md`.
    - **NOTE**: Completed with `docs/repos/core/project-conductor-charter.md` and runbook references.
- [X] [CO-C01-01-02] Define go/no-go gates for each migration phase.
    **COMPLETED** | Architect Agent | 2026-02-28 09:41
    - **NOTE**: Deliverables: checklist with phase gates, rollback trigger, owner, and sign-off.
    - **NOTE**: Acceptance: each phase has objective entry/exit criteria.
    - **NOTE**: Validation: simulate one blocked gate and one passed gate in dry-run.
    - **NOTE**: Completed with `docs/repos/core/project-conductor-phase-gates.md` including rollback triggers and simulation protocol.
- [X] [CO-C01-01-03] Define failure policy (timeouts, retries, escalation, human override).
    **COMPLETED** | Architect Agent | 2026-02-28 09:41
    - **NOTE**: Deliverables: policy table by step (`plan`, `seed`, `expand`, `execute`, `review`, `integrate`).
    - **NOTE**: Acceptance: policy is encoded in config and reflected in CLI logs.
    - **NOTE**: Validation: forced timeout and forced retry scenarios logged in reports.
    - **NOTE**: Completed with `docs/repos/core/project-conductor-failure-policy.md` and `tooling/orchestrator/conductor_policy.toml`.

## Phase 2: Data Model, IDs, And State Machine
- [X] [CO-C01-02-01] Finalize canonical work-item schema for Conductor state.
    **COMPLETED** | Architect Agent | 2026-02-28 09:45
    - **NOTE**: Fields: id, repo targets, source, stage, attempts, timestamps, linked issue/PR, review verdict, errors.
    - **NOTE**: Acceptance: schema versioned and backward-compatible loader implemented.
    - **NOTE**: Validation: state migration test from current `docs/.conductor/state.json`.
    - **NOTE**: Completed by extending `tooling/orchestrator/models.py` and `tooling/orchestrator/state_store.py` with schema v2 and migration loader.
- [X] [CO-C01-02-02] Finalize ID semantics and validation for `REPO-BATCH-EPIC-TICKET`.
    **COMPLETED** | Architect Agent | 2026-02-28 09:45
    - **NOTE**: Deliverables: strict parser, validator, and config-driven generation.
    - **NOTE**: Acceptance: parser rejects malformed IDs and reports clear errors.
    - **NOTE**: Validation: unit tests for valid/invalid ID sets.
    - **NOTE**: Completed with `tooling/orchestrator/item_id.py` and planner enforcement in `tooling/orchestrator/planner.py`.
- [X] [CO-C01-02-03] Define canonical stage enum and legal transitions.
    **COMPLETED** | Architect Agent | 2026-02-28 09:45
    - **NOTE**: Deliverables: transition matrix and enforcement hooks.
    - **NOTE**: Acceptance: illegal transitions hard-fail with actionable message.
    - **NOTE**: Validation: transition tests covering all terminal and retry states.
    - **NOTE**: Completed with canonical stages in `tooling/orchestrator/lifecycle.py` and enforcement hooks in `tooling/orchestrator/tickets.py`.
- [X] [CO-C01-02-04] Add idempotency key strategy per run.
    **COMPLETED** | Architect Agent | 2026-02-28 09:45
    - **NOTE**: Key format: `<item_id>:<repo>:<batch_id>:<stage>`.
    - **NOTE**: Acceptance: reruns do not duplicate issues or expansion updates.
    - **NOTE**: Validation: execute same command twice, compare issue/report diffs.
    - **NOTE**: Completed with `tooling/orchestrator/idempotency.py`, state registry persistence, and ticket sync idempotency checks.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (11 tests passed).

## Phase 3: Seed Issue Workflow (Plain Issues)
- [X] [CO-C01-03-01] Implement `seed` stage to create minimal issue bodies only.
    **COMPLETED** | Architect Agent | 2026-02-28 09:54
    - **NOTE**: Body includes: item ID, source, batch ID, short task list, repo default validation commands.
    - **NOTE**: Acceptance: no agent-generated acceptance criteria in seed stage.
    - **NOTE**: Validation: issue body snapshot tests for all repos.
    - **NOTE**: Completed by refactoring seed body builder in `tooling/orchestrator/tickets.py` to emit minimal seed-only sections and repo default checks.
- [X] [CO-C01-03-02] Add repo tags/labels and useful metadata on issue creation.
    **COMPLETED** | Architect Agent | 2026-02-28 09:54
    - **NOTE**: Labels: `conductor`, `type:task`, `source:roadmap`, `stage:seed`, `repo:<name>`, `batch:<code>`.
    - **NOTE**: Acceptance: labels are present on newly created issues and update cleanly.
    - **NOTE**: Validation: `gh issue view` assertions in CI-style script.
    - **NOTE**: Completed with base/dynamic labels in `tooling/orchestrator/tickets.py` and assertion helper `tooling/orchestrator/verify_seed_labels.py`.
- [X] [CO-C01-03-03] Add config file for per-repo defaults (checks, labels, owner hints).
    **COMPLETED** | Architect Agent | 2026-02-28 09:54
    - **NOTE**: Deliverables: TOML/YAML config under `tooling/orchestrator/` for repo defaults.
    - **NOTE**: Acceptance: changing config does not require code edits.
    - **NOTE**: Validation: two repos with different lint/test command templates.
    - **NOTE**: Completed with `tooling/orchestrator/repo_defaults.toml` + `tooling/orchestrator/repo_defaults.py` consumed by seed body/labels.
- [X] [CO-C01-03-04] Keep `seed` safe under scoped filters.
    **COMPLETED** | Architect Agent | 2026-02-28 09:54
    - **NOTE**: Filters: `--repo`, `--roadmap`, `--item-prefix` compose safely.
    - **NOTE**: Acceptance: no off-scope issue creation in apply mode.
    - **NOTE**: Validation: dry-run and apply logs for single-repo and mixed-prefix cases.
    - **NOTE**: Validation tests: `tooling/tests/orchestrator/test_seed_scoped_filters.py` and `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (17 tests passed).

## Phase 4: Expand Workflow (Planner Enrichment)
- [X] [CO-C01-04-01] Implement `expand` stage to enrich existing issues ticket-by-ticket.
    **COMPLETED** | Architect Agent | 2026-02-28 10:05
    - **NOTE**: Expansion adds structured sections: context, acceptance criteria, validation, risks, out-of-scope.
    - **NOTE**: Acceptance: expansion is append/update deterministic and idempotent.
    - **NOTE**: Validation: repeated expand run produces no duplicate sections.
    - **NOTE**: Completed with `expand_repo_issues` plus deterministic upsert marker handling in `tooling/orchestrator/tickets.py`.
- [X] [CO-C01-04-02] Implement strict structured output for expansion (JSON schema).
    **COMPLETED** | Architect Agent | 2026-02-28 10:05
    - **NOTE**: No free-form conversational output; invalid payloads fail with fallback policy.
    - **NOTE**: Acceptance: schema validation required before issue update.
    - **NOTE**: Validation: schema-negative tests and fallback behavior tests.
    - **NOTE**: Completed with `EXPANSION_SCHEMA` + payload validation/fallback in `tooling/orchestrator/tickets.py` and tests in `tooling/tests/orchestrator/test_expand_payload.py`.
- [X] [CO-C01-04-03] Add expansion mode controls (`--limit`, `--resume-from`, `--dry-run-diff`).
    **COMPLETED** | Architect Agent | 2026-02-28 10:05
    - **NOTE**: Supports one-ticket iterative enrichment and resume after interruption.
    - **NOTE**: Acceptance: operator can expand exactly one item without side effects.
    - **NOTE**: Validation: dry-run diff artifact in `docs/.conductor/reports/`.
    - **NOTE**: Completed with CLI + Makefile support and tests in `tooling/tests/orchestrator/test_expand_controls.py`.
- [X] [CO-C01-04-04] Update issue labels after expansion.
    **COMPLETED** | Architect Agent | 2026-02-28 10:05
    - **NOTE**: Transition label from `stage:seed` to `stage:expanded`.
    - **NOTE**: Acceptance: stage labels always match orchestrator state.
    - **NOTE**: Validation: label consistency checker command.
    - **NOTE**: Completed with stage label sync/check helpers in `tooling/orchestrator/tickets.py`, `expand-label-check` CLI command, and `tooling/tests/orchestrator/test_expand_label_check.py`.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (22 tests passed).
- [X] [CO-C01-04-05] Enable agent-backed expansion generation for `expand` stage.
    **COMPLETED** | Architect Agent | 2026-03-02 00:43
    - **NOTE**: Added `expand` provider routing (`auto|codex|gemini|none`) in `tooling/orchestrator/tickets.py` with Codex schema-driven generation, Gemini/local CLI queue artifacts, and deterministic fallback behavior.
    - **NOTE**: Exposed controls in CLI (`--expand-agent`, `--expand-model`, `--expand-reasoning`, `--expand-personality`) and Makefile (`CONDUCTOR_EXPAND_*`).
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (38 tests passed).
- [X] [CO-C01-04-06] Automate Gemini CLI execution for assess/expand provider paths.
    **COMPLETED** | Architect Agent | 2026-03-02 01:13
    - **NOTE**: Added direct non-interactive Gemini CLI invocation for both ticket assessment and expand payload generation (`tooling/orchestrator/tickets.py`), with queue artifact fallback only when Gemini execution fails.
    - **NOTE**: Added resilient JSON extraction for Gemini JSON envelope responses (plain JSON, fenced JSON, and embedded object text).
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (41 tests passed).
- [X] [CO-C01-04-07] Remove mutable stage/assessment metadata from issue bodies and keep lifecycle truth in labels/state.
    **COMPLETED** | Architect Agent | 2026-03-02 10:56
    - **NOTE**: Seed issue body now omits mutable `Stage`/`Assessment` fields; lifecycle source of truth is labels + orchestrator state.
    - **NOTE**: Expand stage now strips legacy `- Stage:` / `- Assessment:` lines from existing issue bodies before expansion upsert.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (43 tests passed).
- [X] [CO-C01-04-08] Add expansion quality regression guard to preserve strong issue context.
    **COMPLETED** | Architect Agent | 2026-03-03 11:14
    - **NOTE**: Expand now parses existing expansion block and skips replacement when incoming payload is low-quality/regressive; action emitted as `skipped_low_quality_expand`.
    - **NOTE**: Added parsing/quality tests and provider regression test in `tooling/tests/orchestrator/test_expand_payload.py` + `test_expand_provider.py`.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (49 tests passed).
- [X] [CO-C01-04-09] Make expand stage non-regressive for items already beyond expanded.
    **COMPLETED** | Architect Agent | 2026-03-04 10:21
    - **NOTE**: Expand now preserves lifecycle stage for items already in `executing`/review stages and appends `stage_preserved=<stage>` note instead of forcing illegal rollback to `expanded`.
    - **NOTE**: Added apply-mode regression test for executing-stage expansion in `tooling/tests/orchestrator/test_expand_controls.py`.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (51 tests passed).

## Phase 5: LangGraph Planning Pipeline Integration
- [X] [CO-C01-05-01] Implement Idea ingestion node (IDEA.md -> structured roadmap items).
    **COMPLETED** | Architect Agent | 2026-02-28 10:19
    - **NOTE**: Uses strict schema output only; no prose in graph state.
    - **NOTE**: Acceptance: all generated items include repo, batch, epic hints, and title.
    - **NOTE**: Validation: deterministic snapshot tests for fixed IDEA inputs.
    - **NOTE**: Completed with deterministic IDEA parser in `tooling/orchestrator/planning_pipeline.py` and tests in `tooling/tests/orchestrator/test_planning_pipeline.py`.
- [X] [CO-C01-05-02] Implement queue emission node for initial issue intents.
    **COMPLETED** | Architect Agent | 2026-02-28 10:19
    - **NOTE**: Queue artifacts are normalized and traceable to item IDs.
    - **NOTE**: Acceptance: one queue record per target repo/item pair.
    - **NOTE**: Validation: count parity checks with orchestrator state.
    - **NOTE**: Completed with normalized planning queue persistence in `tooling/orchestrator/state_store.py` and graph-plan CLI orchestration in `tooling/orchestrator/cli.py`.
- [X] [CO-C01-05-03] Implement expansion node handoff contract to orchestrator expand stage.
    **COMPLETED** | Architect Agent | 2026-02-28 10:19
    - **NOTE**: Graph step should trigger expand deterministically and capture status/result.
    - **NOTE**: Acceptance: graph and orchestrator state stay in sync on retries.
    - **NOTE**: Validation: interruption/resume integration tests.
    - **NOTE**: Completed with handoff wiring to `expand_repo_issues` via `graph-plan`, including `--limit` and `--resume-from` pass-through and queue status updates.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (25 tests passed).

## Phase 6: Execution Engine Integration (Composio)
- [X] [CO-C01-06-01] Implement handoff bridge (`item -> ao spawn <repo> <item_id>`).
    **COMPLETED** | Architect Agent | 2026-02-28 10:45
    - **NOTE**: Include metadata payload: issue URL, acceptance criteria, validation commands.
    - **NOTE**: Acceptance: spawned run references exact item and branch context.
    - **NOTE**: Validation: smoke test for one repo and one item.
    - **NOTE**: Completed with execute bridge in `tooling/orchestrator/execution_bridge.py` and CLI command `conductor.py execute`.
- [X] [CO-C01-06-02] Define sandbox policy for worktree/container isolation.
    **COMPLETED** | Architect Agent | 2026-02-28 10:45
    - **NOTE**: Determine when sandbox required (`code`) vs optional (`docs/config`).
    - **NOTE**: Acceptance: policy in config and logs indicate chosen mode.
    - **NOTE**: Validation: one docs task and one code task in separate modes.
    - **NOTE**: Completed with policy config `tooling/orchestrator/execution_policy.toml`, loader `execution_policy.py`, and sandbox metadata in execute logs/state.
- [X] [CO-C01-06-03] Capture execution artifacts into orchestrator state.
    **COMPLETED** | Architect Agent | 2026-02-28 10:45
    - **NOTE**: Persist branch, commit, PR URL, execution log path, exit status.
    - **NOTE**: Acceptance: operator can inspect every run from state/report files.
    - **NOTE**: Validation: artifact integrity check command.
    - **NOTE**: Completed with artifact persistence in `state.agent_runs` (`run_type=execute_handoff`) including branch/commit/PR/log/exit status and linked PR updates on work items.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (29 tests passed).
- [X] [CO-C01-06-04] Align execute handoff issue argument with tracker requirements.
    **COMPLETED** | Architect Agent | 2026-03-03 11:06
    - **NOTE**: Execute bridge now resolves issue reference from linked issue metadata (`issues[repo].number` or `/issues/<n>` URL) and passes that to `ao spawn`; falls back to `item_id` only when no issue reference can be derived.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (44 tests passed).
- [X] [CO-C01-06-05] Add post-spawn session health check and reporting for execute handoff.
    **COMPLETED** | Architect Agent | 2026-03-03 11:14
    - **NOTE**: Execute now verifies spawned AO session health via `ao status --json`; immediate exited/killed sessions are reported as `spawn_failed` instead of false-positive `spawned`.
    - **NOTE**: Execute run artifacts now include `session_id` and `spawn_health` for visibility in state/events/actions.
    - **NOTE**: Added execute handoff tests for healthy/early-exit sessions in `tooling/tests/orchestrator/test_execute_handoff.py`.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (49 tests passed).
- [X] [CO-C01-06-06] Allow execute retry eligibility for stuck `executing` items with explicit force.
    **COMPLETED** | Architect Agent | 2026-03-04 10:21
    - **NOTE**: `execute --force` now includes items already in `executing` stage so operators can recover from failed/killed AO sessions without manual state edits.
    - **NOTE**: Added force-eligibility test in `tooling/tests/orchestrator/test_execute_handoff.py`.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (51 tests passed).
- [X] [CO-C01-06-07] Auto-unblock Codex workspace trust prompts during execute handoff spawn checks.
    **COMPLETED** | Architect Agent | 2026-03-04 12:36
    - **NOTE**: Execute bridge now inspects AO session tmux output when spawn health is not ready; if Codex workspace trust prompt is detected, it auto-sends one approval via `ao send --no-wait <session> 1` and re-checks health.
    - **NOTE**: Spawn health now treats persistent `spawning` as unresolved (not success) and reports `spawn_bootstrap` diagnostics in run artifacts/events/actions.
    - **NOTE**: Added execute handoff test coverage for trust-prompt auto-unblock in `tooling/tests/orchestrator/test_execute_handoff.py`.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (52 tests passed).
- [X] [CO-C01-06-08] Add fallback trust bootstrap when session stays spawning but prompt text is not detectable.
    **COMPLETED** | Architect Agent | 2026-03-04 12:44
    - **NOTE**: Execute bridge now sends one guarded fallback approval (`ao send --no-wait <session> 1`) when spawn health remains `spawning/*` and prompt detection is unavailable/variant, then re-checks session health.
    - **NOTE**: Added regression coverage for fallback path in `tooling/tests/orchestrator/test_execute_handoff.py` (`bootstrap=blind_approve_sent`).
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (53 tests passed).
- [X] [CO-C01-06-09] Add tmux key-injection bootstrap path and longer spawn readiness window.
    **COMPLETED** | Architect Agent | 2026-03-04 12:54
    - **NOTE**: Execute bridge now attempts direct tmux key injection (`1` + `Enter`) for Codex trust unblocking when session metadata exposes `tmuxName`; AO send remains fallback.
    - **NOTE**: Spawn health polling defaults increased to reduce false negatives on slow startup (`TV7_EXEC_SPAWN_HEALTH_POLLS=12`, `TV7_EXEC_SPAWN_HEALTH_POLL_SEC=1.0`).
    - **NOTE**: Added/updated tests for `bootstrap=codex_workspace_trust_approved_tmux` and `bootstrap=blind_tmux_keys_sent` in `tooling/tests/orchestrator/test_execute_handoff.py`.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (53 tests passed).

## Phase 7: DeepSeek Quality Loop
- [X] [CO-C01-07-01] Integrate DeepSeek review gate in execution lifecycle.
    **COMPLETED** | Architect Agent | 2026-03-01 20:10
    - **NOTE**: Do not mark task done until final verdict is APPROVED.
    - **NOTE**: Acceptance: non-approved verdict returns item to execution stage.
    - **NOTE**: Validation: simulated failing review then successful fix cycle.
    - **NOTE**: Completed with review gate implementation in `tooling/orchestrator/review_gate.py` and `conductor.py review` CLI command.
- [X] [CO-C01-07-02] Normalize review feedback payload for deterministic retries.
    **COMPLETED** | Architect Agent | 2026-03-01 20:10
    - **NOTE**: Keep compact actionable comments and stable mapping to files/lines.
    - **NOTE**: Acceptance: retry prompt contains only required failure context.
    - **NOTE**: Validation: compare payload size and retry success rate.
    - **NOTE**: Completed with deterministic `review_feedback.retry_payload` persisted on work items for retry prompts.
- [X] [CO-C01-07-03] Add max-loop safeguards and explicit escalation state.
    **COMPLETED** | Architect Agent | 2026-03-01 20:10
    - **NOTE**: Loop thresholds configurable per repo or task class.
    - **NOTE**: Acceptance: exceeded loops produce `needs-human` state, not silent fail.
    - **NOTE**: Validation: forced loop overflow scenario.
    - **NOTE**: Completed with configurable loop policy in `tooling/orchestrator/review_policy.toml` + `review_policy.py` and escalation transition to `needs_human` in review gate.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (32 tests passed).
- [X] [CO-C01-07-04] Keep PR author metadata immutable during DeepSeek review and emit comment-only verdict + confidence.
    **COMPLETED** | Architect Agent | 2026-03-04 18:55
    - **NOTE**: Removed PR title/body mutation path from reusable DeepSeek workflow and removed prompt instructions requesting `PR_TITLE`/`PR_SUMMARY`.
    - **NOTE**: DeepSeek review body now includes explicit `Confidence: NN%` plus verdict line, while preserving author-written PR metadata.
    - **NOTE**: Updated workflow: `.github/workflows/deepseek-review.yml`.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (53 tests passed).
- [X] [CO-C01-07-05] Enforce strict, evidence-scoped DeepSeek review comment schema.
    **COMPLETED** | Architect Agent | 2026-03-04 19:36
    - **NOTE**: Added deterministic review comment normalizer `tooling/deepseek_review_comment.py` and wired reusable workflow to use it before posting GitHub review.
    - **NOTE**: DeepSeek prompt now explicitly forbids speculative non-diff claims and requires changed-file evidence with max 5 findings.
    - **NOTE**: Posted review format is now strict/comment-only: `DeepSeek review`, confidence, final verdict, top findings (changed-file evidence only); parser fallback posts COMMENT with `unknown` confidence when verdict is missing.
    - **NOTE**: Added unit tests in `tooling/tests/orchestrator/test_deepseek_review_comment.py`.
    - **NOTE**: Validation commands run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (56 tests passed); `python3 tooling/deepseek_review_comment.py --content-file ... --changed-files-file ...` (manual smoke).
- [X] [CO-C01-07-06] Remove hard cap/truncation in DeepSeek comment normalizer and enforce explicit code references per finding.
    **COMPLETED** | Architect Agent | 2026-03-04 22:17
    - **NOTE**: Updated `tooling/deepseek_review_comment.py` defaults to no fixed max findings and no body truncation (`0` means unlimited); retained optional CLI overrides for repos that need limits.
    - **NOTE**: Normalized review body now emits explicit `Code refs: path[:line]` for each finding and filters out lines without changed-file code references.
    - **NOTE**: Updated DeepSeek prompt/workflow to remove the top-5 cap instruction and stop passing `--max-findings 5 --max-body-chars 4500`.
    - **NOTE**: Updated docs in `docs/ai-code-review.md` and added regression tests in `tooling/tests/orchestrator/test_deepseek_review_comment.py`.
    - **NOTE**: Validation command run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (58 tests passed).

## Phase 8: Integrator And Validation
- [ ] [CO-C01-08-01] Implement final integrator node for post-review merge validation.
    **BACKLOG** | Architect Agent | 2026-02-26
    - **NOTE**: Runs final repo tests before marking done (`pytest`, `flutter test`, etc.).
    - **NOTE**: Acceptance: failed integration tests block completion and record failure cause.
    - **NOTE**: Validation: one intentional failing test scenario.
- [ ] [CO-C01-08-02] Add per-repo validation matrix and command resolver.
    **BACKLOG** | Architect Agent | 2026-02-26
    - **NOTE**: Resolver pulls from orchestrator config defaults and optional ticket overrides.
    - **NOTE**: Acceptance: validation command list is explicit in issue and logs.
    - **NOTE**: Validation: matrix coverage for all five repos.

## Phase 9: Unified Run Command
- [ ] [CO-C01-09-01] Add `conductor-run` command to execute full flow.
    **BACKLOG** | Architect Agent | 2026-02-26
    - **NOTE**: Sequence: `plan -> seed -> expand -> execute/review -> integrate`.
    - **NOTE**: Acceptance: one command can run all stages with structured progress output.
    - **NOTE**: Validation: full dry-run and full apply runs produce complete reports.
- [ ] [CO-C01-09-02] Add optional repo scoping to `conductor-run`.
    **BACKLOG** | Architect Agent | 2026-02-26
    - **NOTE**: Supports `--repo` and existing filter combinations.
    - **NOTE**: Acceptance: scoped run never touches off-scope repos/items.
    - **NOTE**: Validation: scoped run report with zero off-scope actions.
- [ ] [CO-C01-09-03] Add Makefile targets for full and scoped run.
    **BACKLOG** | Architect Agent | 2026-02-26
    - **NOTE**: `make conductor-run` and `make conductor-run CONDUCTOR_TICKET_REPO=tv7-...`.
    - **NOTE**: Acceptance: commands documented and reproducible from clean workspace.
    - **NOTE**: Validation: command examples in runbook tested verbatim.

## Phase 10: Observability, Rollout, And Decommission
- [ ] [CO-C01-10-01] Add metrics and reporting for each stage.
    **BACKLOG** | Architect Agent | 2026-02-26
    - **NOTE**: Metrics: throughput, failure rates, retries, approval latency, timeout rates.
    - **NOTE**: Acceptance: metrics emitted per run and summarized in markdown report.
    - **NOTE**: Validation: compare metrics across two consecutive batches.
- [ ] [CO-C01-10-02] Run controlled pilot batches (single repo then full workspace).
    **BACKLOG** | Architect Agent | 2026-02-26
    - **CROSS-AGENT-NOTES**: Pilot order: one repo first, then all repos.
    - **NOTE**: Acceptance: two clean full batches with no critical regressions.
    - **NOTE**: Validation: sign-off checklist completed and archived.
- [ ] [CO-C01-10-03] Decommission legacy local orchestrator modules after gate pass.
    **BACKLOG** | Architect Agent | 2026-02-26
    - **NOTE**: Remove old scripts only after migration gates are green.
    - **NOTE**: Acceptance: no production workflow dependency on removed modules.
    - **NOTE**: Validation: clean-room run from docs confirms new stack only.
- [X] [CO-C01-10-04] Add operator-facing spawned-agent status board with actionable next-step hints.
    **COMPLETED** | Architect Agent | 2026-03-04 18:55
    - **NOTE**: Added `ops-status` CLI command (`tooling/orchestrator/cli.py`) to aggregate AO sessions and emit actionable hints (startup pending, session stopped, CI/review needed, merge-ready).
    - **NOTE**: Added Make targets `conductor-ops-status` and `orchestrator-ops-status`.
    - **NOTE**: Documented operator command in runbook and tooling README.
    - **NOTE**: Validation commands run: `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` (53 tests passed); `python3 tooling/conductor.py ops-status --json`.
