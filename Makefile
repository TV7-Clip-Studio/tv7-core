# Cross-repo convenience targets; run from repo root.

REPO_ROOT ?= ..
REPO_ROOT := $(abspath $(REPO_ROOT))
OWNER ?= TV7-Clip-Studio
REPOS ?= tv7-core tv7-conductor tv7-axum-engine tv7-fastapi-backend tv7-flutter-studio tv7-astro-site
TOOLING_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/tooling
CONDUCTOR_REPO ?= $(REPO_ROOT)/tv7-conductor
CONDUCTOR_TOOLING_DIR ?= $(CONDUCTOR_REPO)/tooling
CONDUCTOR_PYTHON ?= $(if $(wildcard $(CONDUCTOR_REPO)/.venv/bin/python),$(CONDUCTOR_REPO)/.venv/bin/python,$(if $(wildcard /opt/homebrew/bin/python3),/opt/homebrew/bin/python3,python3))
SYNC_BASE ?= origin/main
SKIP_DEPS ?= 0
SKIP_IDE ?= 0
PYTHON ?= python3
TMP_DIR ?= $(CURDIR)/docs/.tmp
DEV_STATE_DIR ?= $(TMP_DIR)/dev-stack
BACKEND_PORT ?= 8000
ENGINE_PORT ?= 7070
SITE_PORT ?= 4321
REVIEWS_DIR ?= $(CURDIR)/docs/code-reviews
CURRENT_BRANCH := $(shell git -C "$(CURDIR)" rev-parse --abbrev-ref HEAD 2>/dev/null)
AUTO_BATCH_ID := $(shell printf '%s' "$(CURRENT_BRANCH)" | sed -nE 's/^codex\/batch-tv7-core-//p')
BATCH_ID ?= $(AUTO_BATCH_ID)
AGENT_PROFILE ?= local_auto_medium
ORCH_PLAN_ROADMAP ?=
ORCH_TICKET_REPO ?=
ORCH_TICKET_ROADMAP ?=
ORCH_TICKET_ITEM_PREFIX ?=
CONDUCTOR_PLAN_ROADMAP ?= $(ORCH_PLAN_ROADMAP)
CONDUCTOR_ROADMAP_FILE ?= $(CONDUCTOR_PLAN_ROADMAP)
CONDUCTOR_TICKET_REPO ?= $(ORCH_TICKET_REPO)
CONDUCTOR_TICKET_ROADMAP ?= $(ORCH_TICKET_ROADMAP)
CONDUCTOR_TICKET_ITEM_PREFIX ?= $(ORCH_TICKET_ITEM_PREFIX)
CONDUCTOR_AGENT_PROFILE ?= $(AGENT_PROFILE)
CONDUCTOR_BATCH_ID ?= $(BATCH_ID)
CONDUCTOR_DRY_RUN ?= 0
CONDUCTOR_ASSESS ?= 0
CONDUCTOR_RUN_FLAGS ?=
CONDUCTOR_EXPAND_LIMIT ?= 0
CONDUCTOR_EXPAND_RESUME_FROM ?=
CONDUCTOR_EXPAND_DRY_RUN_DIFF ?= 0
CONDUCTOR_EXPAND_STRICT ?= 0
CONDUCTOR_EXPAND_AGENT ?= auto
CONDUCTOR_EXPAND_MODEL ?=
CONDUCTOR_EXPAND_REASONING ?=
CONDUCTOR_EXPAND_PERSONALITY ?=
CONDUCTOR_EXECUTE_LIMIT ?= 0
CONDUCTOR_EXECUTE_RESUME_FROM ?=
CONDUCTOR_EXECUTE_FORCE ?= 0
CONDUCTOR_AO_COMMAND ?= ao
CONDUCTOR_EXECUTE_POLICY ?= $(CONDUCTOR_TOOLING_DIR)/orchestrator/execution_policy.toml
CONDUCTOR_REVIEW_LIMIT ?= 0
CONDUCTOR_REVIEW_RESUME_FROM ?=
CONDUCTOR_REVIEW_MAX_LOOPS ?= 0
CONDUCTOR_REVIEW_POLICY ?= $(CONDUCTOR_TOOLING_DIR)/orchestrator/review_policy.toml
CONDUCTOR_REVIEW_HARD_ONLY ?= 0
CONDUCTOR_REVIEW_INCLUDE_RECOMMENDATIONS ?= 0
CONDUCTOR_IDEA_FILE ?= $(CURDIR)/IDEA.md
CONDUCTOR_GRAPH_DEFAULT_REPO ?= tv7-core
CONDUCTOR_GRAPH_ROADMAP_CODE ?=
CONDUCTOR_GRAPH_BATCH_CODE ?= C01
CONDUCTOR_GRAPH_DEFAULT_EPIC ?= 01
CONDUCTOR_GRAPH_HANDOFF ?= 1

.PHONY: status pull-all bootstrap sync update set-secret update-secrets install-guardrails dev dev-up dev-backend dev-engine dev-site dev-studio dev-status dev-stop dev-logs reviews reviews-json batch-pr batch-pr-dry-run batch-pr-report batch-pr-open repo-status deepseek-followup deepseek-fix conductor-init conductor-plan conductor-graph-plan conductor-graph-plan-apply conductor-profiles conductor-tickets conductor-tickets-apply conductor-tickets-gemini conductor-tickets-gemini-apply conductor-tickets-codex conductor-tickets-codex-apply conductor-expand conductor-expand-apply conductor-expand-label-check conductor-expand-label-check-apply conductor-execute conductor-execute-apply conductor-review conductor-review-apply conductor-tickets-reset conductor-tickets-reset-apply conductor-tickets-reset-scan conductor-tickets-reset-scan-apply conductor-run conductor-run-once conductor-status conductor-ops-status conductor-events conductor-shim-check orchestrator-init orchestrator-plan orchestrator-profiles orchestrator-tickets orchestrator-tickets-apply orchestrator-tickets-gemini orchestrator-tickets-gemini-apply orchestrator-tickets-codex orchestrator-tickets-codex-apply orchestrator-tickets-reset orchestrator-tickets-reset-apply orchestrator-tickets-reset-scan orchestrator-tickets-reset-scan-apply orchestrator-run-once orchestrator-status orchestrator-ops-status orchestrator-events

status:
	@bash "$(TOOLING_DIR)/status.sh"

pull-all:
	@bash "$(TOOLING_DIR)/pull-all.sh"

bootstrap:
	@REPO_ROOT="$(REPO_ROOT)" bash "$(TOOLING_DIR)/bootstrap-repos.sh"
	@REPO_ROOT="$(REPO_ROOT)" bash "$(TOOLING_DIR)/setup-secrets.sh" --defaults
	@REPO_ROOT="$(REPO_ROOT)" SKIP_DEPS="$(SKIP_DEPS)" bash "$(TOOLING_DIR)/install-deps.sh"
	@if [ "$(SKIP_IDE)" != "1" ]; then REPO_ROOT="$(REPO_ROOT)" bash "$(TOOLING_DIR)/setup-ide.sh"; fi
	@echo "Bootstrap complete. To skip deps, set SKIP_DEPS=1. To skip IDE setup, set SKIP_IDE=1."

sync update:
	@REPO_ROOT="$(REPO_ROOT)" QUIET=1 bash "$(TOOLING_DIR)/bootstrap-repos.sh"
	@for repo in $(REPOS); do \
		path="$(REPO_ROOT)/$$repo"; \
		status="[✓]"; note=""; \
		if [ ! -d "$$path/.git" ]; then \
			status="[X]"; note="missing at $$path"; \
			echo "$$status $$repo - $$note"; \
			continue; \
		fi; \
		branch="$$(git -C "$$path" rev-parse --abbrev-ref HEAD)"; \
		git -C "$$path" fetch --quiet --prune >/dev/null 2>&1 || true; \
		upstream="$$(git -C "$$path" rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>/dev/null || true)"; \
		if [ -z "$$upstream" ] && git -C "$$path" ls-remote --exit-code --heads origin "$$branch" >/dev/null 2>&1; then \
			git -C "$$path" branch --set-upstream-to="origin/$$branch" "$$branch" >/dev/null 2>&1 && upstream="origin/$$branch"; \
		else \
			:; \
		fi; \
		if [ -z "$$upstream" ]; then \
			if git -C "$$path" rev-parse --verify --quiet "$(SYNC_BASE)^{commit}" >/dev/null 2>&1; then \
				rebase_output="$$(git -C "$$path" rebase --autostash "$(SYNC_BASE)" 2>&1)"; \
				rc=$$?; \
				if [ $$rc -eq 0 ]; then \
					note="local branch (rebased onto $(SYNC_BASE))"; \
				else \
					status="[X]"; \
					conflicts="$$(git -C "$$path" diff --name-only --diff-filter=U | tr '\n' ' ' | sed 's/[[:space:]]$$//')"; \
					if [ -z "$$conflicts" ]; then \
						conflicts="see git status"; \
					else \
						conflicts="conflicts: $$conflicts"; \
					fi; \
					note="rebase failed onto $(SYNC_BASE); $$conflicts"; \
				fi; \
			else \
				changes="$$(git -C "$$path" status --porcelain | wc -l | tr -d ' ')"; \
				if [ "$$changes" = "0" ]; then \
					note="local branch (no upstream, clean)"; \
				else \
					note="local branch (no upstream, $$changes pending)"; \
				fi; \
			fi; \
		else \
			pull_output="$$(git -C "$$path" pull --rebase --autostash 2>&1)"; \
			rc=$$?; \
			if [ $$rc -eq 0 ]; then \
				note=""; \
			else \
				status="[X]"; \
				conflicts="$$(git -C "$$path" diff --name-only --diff-filter=U | tr '\n' ' ' | sed 's/[[:space:]]$$//')"; \
				if [ -z "$$conflicts" ]; then \
					conflicts="see git status"; \
				else \
					conflicts="conflicts: $$conflicts"; \
				fi; \
				note="rebase failed onto $$upstream; $$conflicts"; \
			fi; \
		fi; \
		pr_note="$$(OWNER="$(OWNER)" bash "$(TOOLING_DIR)/pr-info.sh" "$$repo" "$$branch" 2>/dev/null || true)"; \
		if [ -n "$$note" ] && [ -n "$$pr_note" ]; then \
			echo "$$status $$repo ($$branch) - $$note - $$pr_note"; \
		elif [ -n "$$note" ]; then \
			echo "$$status $$repo ($$branch) - $$note"; \
		elif [ -n "$$pr_note" ]; then \
			echo "$$status $$repo ($$branch) - $$pr_note"; \
		else \
			echo "$$status $$repo ($$branch)"; \
		fi; \
	done

set-secret:
	@SECRET_NAME=$(SECRET_NAME) SECRET_VALUE=$(SECRET_VALUE) REPOS="$(REPOS)" ALL=$(ALL) ORG=$(ORG) bash "$(CURDIR)/tooling/set-secret.sh"

install-guardrails:
	@hook="$(TOOLING_DIR)/git-hooks/pre-push"; \
	for repo in $(REPOS); do \
		path="$(REPO_ROOT)/$$repo"; \
		if [ ! -d "$$path/.git" ]; then \
			echo "[skip] $$repo missing at $$path"; \
			continue; \
		fi; \
		mkdir -p "$$path/.git/hooks"; \
		cp "$$hook" "$$path/.git/hooks/pre-push"; \
		chmod +x "$$path/.git/hooks/pre-push"; \
		echo "[ok] installed no-push guardrail in $$repo"; \
	done

dev dev-up:
	@REPO_ROOT="$(REPO_ROOT)" DEV_STATE_DIR="$(DEV_STATE_DIR)" BACKEND_PORT="$(BACKEND_PORT)" ENGINE_PORT="$(ENGINE_PORT)" SITE_PORT="$(SITE_PORT)" bash "$(TOOLING_DIR)/dev-stack.sh" up

dev-backend:
	@REPO_ROOT="$(REPO_ROOT)" DEV_STATE_DIR="$(DEV_STATE_DIR)" BACKEND_PORT="$(BACKEND_PORT)" ENGINE_PORT="$(ENGINE_PORT)" SITE_PORT="$(SITE_PORT)" bash "$(TOOLING_DIR)/dev-stack.sh" backend

dev-engine:
	@REPO_ROOT="$(REPO_ROOT)" DEV_STATE_DIR="$(DEV_STATE_DIR)" BACKEND_PORT="$(BACKEND_PORT)" ENGINE_PORT="$(ENGINE_PORT)" SITE_PORT="$(SITE_PORT)" bash "$(TOOLING_DIR)/dev-stack.sh" engine

dev-site:
	@REPO_ROOT="$(REPO_ROOT)" DEV_STATE_DIR="$(DEV_STATE_DIR)" BACKEND_PORT="$(BACKEND_PORT)" ENGINE_PORT="$(ENGINE_PORT)" SITE_PORT="$(SITE_PORT)" bash "$(TOOLING_DIR)/dev-stack.sh" site

dev-studio:
	@REPO_ROOT="$(REPO_ROOT)" DEV_STATE_DIR="$(DEV_STATE_DIR)" BACKEND_PORT="$(BACKEND_PORT)" ENGINE_PORT="$(ENGINE_PORT)" SITE_PORT="$(SITE_PORT)" bash "$(TOOLING_DIR)/dev-stack.sh" studio

dev-status:
	@REPO_ROOT="$(REPO_ROOT)" DEV_STATE_DIR="$(DEV_STATE_DIR)" BACKEND_PORT="$(BACKEND_PORT)" ENGINE_PORT="$(ENGINE_PORT)" SITE_PORT="$(SITE_PORT)" bash "$(TOOLING_DIR)/dev-stack.sh" status

dev-stop:
	@REPO_ROOT="$(REPO_ROOT)" DEV_STATE_DIR="$(DEV_STATE_DIR)" BACKEND_PORT="$(BACKEND_PORT)" ENGINE_PORT="$(ENGINE_PORT)" SITE_PORT="$(SITE_PORT)" bash "$(TOOLING_DIR)/dev-stack.sh" stop

dev-logs:
	@REPO_ROOT="$(REPO_ROOT)" DEV_STATE_DIR="$(DEV_STATE_DIR)" BACKEND_PORT="$(BACKEND_PORT)" ENGINE_PORT="$(ENGINE_PORT)" SITE_PORT="$(SITE_PORT)" bash "$(TOOLING_DIR)/dev-stack.sh" logs

reviews reviews-json:
	@if [ ! -f "$(TOOLING_DIR)/repos-checks.conf" ]; then \
		echo "Error: $(TOOLING_DIR)/repos-checks.conf not found." >&2; \
		exit 1; \
	fi
	@mkdir -p "$(REVIEWS_DIR)"
	@if [ ! -w "$(REVIEWS_DIR)" ]; then \
		echo "Error: Output directory $(REVIEWS_DIR) is not writable." >&2; \
		exit 1; \
	fi
	@REPOS="$(REPOS)" OUT_DIR="$(REVIEWS_DIR)" CONFIG_FILE="$(TOOLING_DIR)/repos-checks.conf" "$(PYTHON)" "$(TOOLING_DIR)/reviews.py"

batch-pr:
	@REPO_ROOT="$(REPO_ROOT)" OPEN_PR=1 PUSH_BRANCH=1 RUN_CHECKS_IN_ALL_REPOS=1 bash "$(TOOLING_DIR)/batch-pr.sh"

batch-pr-dry-run:
	@REPO_ROOT="$(REPO_ROOT)" DRY_RUN=1 OPEN_PR=1 PUSH_BRANCH=1 RUN_CHECKS_IN_ALL_REPOS=1 bash "$(TOOLING_DIR)/batch-pr.sh"

batch-pr-open:
	@REPO_ROOT="$(REPO_ROOT)" OPEN_PR=1 PUSH_BRANCH=1 RUN_CHECKS_IN_ALL_REPOS=1 bash "$(TOOLING_DIR)/batch-pr.sh"

batch-pr-report repo-status:
	@REPO_ROOT="$(REPO_ROOT)" bash "$(TOOLING_DIR)/repo-status.sh"

deepseek-followup:
	@mkdir -p "$(TMP_DIR)"
	@REPO_ROOT="$(REPO_ROOT)" \
	BATCH_ID="$(BATCH_ID)" \
	OUT_JSON="$(TMP_DIR)/deepseek-followup.json" \
	OUT_MD="$(TMP_DIR)/deepseek-followup.md" \
	"$(PYTHON)" "$(TOOLING_DIR)/deepseek_followup.py"

deepseek-fix:
	@mkdir -p "$(TMP_DIR)"
	@REPO_ROOT="$(REPO_ROOT)" \
	BATCH_ID="$(BATCH_ID)" \
	FOLLOWUP_JSON="$(TMP_DIR)/deepseek-followup.json" \
	FOLLOWUP_MD="$(TMP_DIR)/deepseek-followup.md" \
	ACTIONABLE_JSON="$(TMP_DIR)/deepseek-followup-actionable.json" \
	ACTIONABLE_MD="$(TMP_DIR)/deepseek-followup-actionable.md" \
	PROMPT_DIR="$(TMP_DIR)/deepseek-fix-prompts" \
	PLAN_MD="$(TMP_DIR)/deepseek-fix-plan.md" \
	"$(PYTHON)" "$(TOOLING_DIR)/deepseek_fix.py"

conductor-init:
	@"$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" init

conductor-plan:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" plan; \
	if [ -n "$(CONDUCTOR_PLAN_ROADMAP)" ]; then \
		set -- "$$@" --single-roadmap --roadmap "$(CONDUCTOR_PLAN_ROADMAP)"; \
	fi; \
	"$$@"

conductor-graph-plan:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" graph-plan --idea-file "$(CONDUCTOR_IDEA_FILE)" --default-repo "$(CONDUCTOR_GRAPH_DEFAULT_REPO)" --batch-code "$(CONDUCTOR_GRAPH_BATCH_CODE)" --default-epic "$(CONDUCTOR_GRAPH_DEFAULT_EPIC)" --batch-id "$(CONDUCTOR_BATCH_ID)" --limit "$(CONDUCTOR_EXPAND_LIMIT)"; \
	if [ -n "$(CONDUCTOR_GRAPH_ROADMAP_CODE)" ]; then set -- "$$@" --roadmap-code "$(CONDUCTOR_GRAPH_ROADMAP_CODE)"; fi; \
	if [ "$(CONDUCTOR_GRAPH_HANDOFF)" = "0" ]; then set -- "$$@" --no-handoff-expand; fi; \
	if [ -n "$(CONDUCTOR_EXPAND_RESUME_FROM)" ]; then set -- "$$@" --resume-from "$(CONDUCTOR_EXPAND_RESUME_FROM)"; fi; \
	if [ "$(CONDUCTOR_EXPAND_DRY_RUN_DIFF)" = "1" ]; then set -- "$$@" --dry-run-diff; fi; \
	if [ "$(CONDUCTOR_EXPAND_STRICT)" = "1" ]; then set -- "$$@" --strict-expand; fi; \
	"$$@"

conductor-graph-plan-apply:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" graph-plan --apply --idea-file "$(CONDUCTOR_IDEA_FILE)" --default-repo "$(CONDUCTOR_GRAPH_DEFAULT_REPO)" --batch-code "$(CONDUCTOR_GRAPH_BATCH_CODE)" --default-epic "$(CONDUCTOR_GRAPH_DEFAULT_EPIC)" --batch-id "$(CONDUCTOR_BATCH_ID)" --limit "$(CONDUCTOR_EXPAND_LIMIT)"; \
	if [ -n "$(CONDUCTOR_GRAPH_ROADMAP_CODE)" ]; then set -- "$$@" --roadmap-code "$(CONDUCTOR_GRAPH_ROADMAP_CODE)"; fi; \
	if [ "$(CONDUCTOR_GRAPH_HANDOFF)" = "0" ]; then set -- "$$@" --no-handoff-expand; fi; \
	if [ -n "$(CONDUCTOR_EXPAND_RESUME_FROM)" ]; then set -- "$$@" --resume-from "$(CONDUCTOR_EXPAND_RESUME_FROM)"; fi; \
	if [ "$(CONDUCTOR_EXPAND_STRICT)" = "1" ]; then set -- "$$@" --strict-expand; fi; \
	"$$@"

conductor-profiles:
	@"$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" tickets --list-agent-profiles

conductor-tickets:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" tickets --agent-profile "$(CONDUCTOR_AGENT_PROFILE)" --batch-id "$(CONDUCTOR_BATCH_ID)"; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ROADMAP)" ]; then set -- "$$@" --roadmap "$(CONDUCTOR_TICKET_ROADMAP)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	"$$@"

conductor-tickets-apply:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" tickets --apply --agent-profile "$(CONDUCTOR_AGENT_PROFILE)" --batch-id "$(CONDUCTOR_BATCH_ID)"; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ROADMAP)" ]; then set -- "$$@" --roadmap "$(CONDUCTOR_TICKET_ROADMAP)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	"$$@"

conductor-tickets-gemini:
	@$(MAKE) conductor-tickets CONDUCTOR_AGENT_PROFILE=gemini_pro_medium CONDUCTOR_TICKET_REPO="$(CONDUCTOR_TICKET_REPO)" CONDUCTOR_TICKET_ROADMAP="$(CONDUCTOR_TICKET_ROADMAP)" CONDUCTOR_TICKET_ITEM_PREFIX="$(CONDUCTOR_TICKET_ITEM_PREFIX)" CONDUCTOR_BATCH_ID="$(CONDUCTOR_BATCH_ID)"

conductor-tickets-gemini-apply:
	@$(MAKE) conductor-tickets-apply CONDUCTOR_AGENT_PROFILE=gemini_pro_medium CONDUCTOR_TICKET_REPO="$(CONDUCTOR_TICKET_REPO)" CONDUCTOR_TICKET_ROADMAP="$(CONDUCTOR_TICKET_ROADMAP)" CONDUCTOR_TICKET_ITEM_PREFIX="$(CONDUCTOR_TICKET_ITEM_PREFIX)" CONDUCTOR_BATCH_ID="$(CONDUCTOR_BATCH_ID)"

conductor-tickets-codex:
	@$(MAKE) conductor-tickets CONDUCTOR_AGENT_PROFILE=codex_fast_low CONDUCTOR_TICKET_REPO="$(CONDUCTOR_TICKET_REPO)" CONDUCTOR_TICKET_ROADMAP="$(CONDUCTOR_TICKET_ROADMAP)" CONDUCTOR_TICKET_ITEM_PREFIX="$(CONDUCTOR_TICKET_ITEM_PREFIX)" CONDUCTOR_BATCH_ID="$(CONDUCTOR_BATCH_ID)"

conductor-tickets-codex-apply:
	@$(MAKE) conductor-tickets-apply CONDUCTOR_AGENT_PROFILE=codex_fast_low CONDUCTOR_TICKET_REPO="$(CONDUCTOR_TICKET_REPO)" CONDUCTOR_TICKET_ROADMAP="$(CONDUCTOR_TICKET_ROADMAP)" CONDUCTOR_TICKET_ITEM_PREFIX="$(CONDUCTOR_TICKET_ITEM_PREFIX)" CONDUCTOR_BATCH_ID="$(CONDUCTOR_BATCH_ID)"

conductor-expand:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" expand --batch-id "$(CONDUCTOR_BATCH_ID)" --limit "$(CONDUCTOR_EXPAND_LIMIT)"; \
	set -- "$$@" --expand-agent "$(CONDUCTOR_EXPAND_AGENT)"; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ROADMAP)" ]; then set -- "$$@" --roadmap "$(CONDUCTOR_TICKET_ROADMAP)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	if [ -n "$(CONDUCTOR_EXPAND_RESUME_FROM)" ]; then set -- "$$@" --resume-from "$(CONDUCTOR_EXPAND_RESUME_FROM)"; fi; \
	if [ -n "$(CONDUCTOR_EXPAND_MODEL)" ]; then set -- "$$@" --expand-model "$(CONDUCTOR_EXPAND_MODEL)"; fi; \
	if [ -n "$(CONDUCTOR_EXPAND_REASONING)" ]; then set -- "$$@" --expand-reasoning "$(CONDUCTOR_EXPAND_REASONING)"; fi; \
	if [ -n "$(CONDUCTOR_EXPAND_PERSONALITY)" ]; then set -- "$$@" --expand-personality "$(CONDUCTOR_EXPAND_PERSONALITY)"; fi; \
	if [ "$(CONDUCTOR_EXPAND_DRY_RUN_DIFF)" = "1" ]; then set -- "$$@" --dry-run-diff; fi; \
	if [ "$(CONDUCTOR_EXPAND_STRICT)" = "1" ]; then set -- "$$@" --strict-expand; fi; \
	"$$@"

conductor-expand-apply:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" expand --apply --batch-id "$(CONDUCTOR_BATCH_ID)" --limit "$(CONDUCTOR_EXPAND_LIMIT)"; \
	set -- "$$@" --expand-agent "$(CONDUCTOR_EXPAND_AGENT)"; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ROADMAP)" ]; then set -- "$$@" --roadmap "$(CONDUCTOR_TICKET_ROADMAP)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	if [ -n "$(CONDUCTOR_EXPAND_RESUME_FROM)" ]; then set -- "$$@" --resume-from "$(CONDUCTOR_EXPAND_RESUME_FROM)"; fi; \
	if [ -n "$(CONDUCTOR_EXPAND_MODEL)" ]; then set -- "$$@" --expand-model "$(CONDUCTOR_EXPAND_MODEL)"; fi; \
	if [ -n "$(CONDUCTOR_EXPAND_REASONING)" ]; then set -- "$$@" --expand-reasoning "$(CONDUCTOR_EXPAND_REASONING)"; fi; \
	if [ -n "$(CONDUCTOR_EXPAND_PERSONALITY)" ]; then set -- "$$@" --expand-personality "$(CONDUCTOR_EXPAND_PERSONALITY)"; fi; \
	if [ "$(CONDUCTOR_EXPAND_STRICT)" = "1" ]; then set -- "$$@" --strict-expand; fi; \
	"$$@"

conductor-expand-label-check:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" expand-label-check; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	"$$@"

conductor-expand-label-check-apply:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" expand-label-check --apply; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	"$$@"

conductor-execute:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" execute --ao-command "$(CONDUCTOR_AO_COMMAND)" --batch-id "$(CONDUCTOR_BATCH_ID)" --limit "$(CONDUCTOR_EXECUTE_LIMIT)"; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ROADMAP)" ]; then set -- "$$@" --roadmap "$(CONDUCTOR_TICKET_ROADMAP)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	if [ -n "$(CONDUCTOR_EXECUTE_RESUME_FROM)" ]; then set -- "$$@" --resume-from "$(CONDUCTOR_EXECUTE_RESUME_FROM)"; fi; \
	if [ "$(CONDUCTOR_EXECUTE_FORCE)" = "1" ]; then set -- "$$@" --force; fi; \
	if [ -n "$(CONDUCTOR_EXECUTE_POLICY)" ]; then set -- "$$@" --policy-path "$(CONDUCTOR_EXECUTE_POLICY)"; fi; \
	"$$@"

conductor-execute-apply:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" execute --apply --ao-command "$(CONDUCTOR_AO_COMMAND)" --batch-id "$(CONDUCTOR_BATCH_ID)" --limit "$(CONDUCTOR_EXECUTE_LIMIT)"; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ROADMAP)" ]; then set -- "$$@" --roadmap "$(CONDUCTOR_TICKET_ROADMAP)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	if [ -n "$(CONDUCTOR_EXECUTE_RESUME_FROM)" ]; then set -- "$$@" --resume-from "$(CONDUCTOR_EXECUTE_RESUME_FROM)"; fi; \
	if [ "$(CONDUCTOR_EXECUTE_FORCE)" = "1" ]; then set -- "$$@" --force; fi; \
	if [ -n "$(CONDUCTOR_EXECUTE_POLICY)" ]; then set -- "$$@" --policy-path "$(CONDUCTOR_EXECUTE_POLICY)"; fi; \
	"$$@"

conductor-review:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" review --limit "$(CONDUCTOR_REVIEW_LIMIT)" --max-loops "$(CONDUCTOR_REVIEW_MAX_LOOPS)"; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ROADMAP)" ]; then set -- "$$@" --roadmap "$(CONDUCTOR_TICKET_ROADMAP)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	if [ -n "$(CONDUCTOR_REVIEW_RESUME_FROM)" ]; then set -- "$$@" --resume-from "$(CONDUCTOR_REVIEW_RESUME_FROM)"; fi; \
	if [ -n "$(CONDUCTOR_REVIEW_POLICY)" ]; then set -- "$$@" --review-policy-path "$(CONDUCTOR_REVIEW_POLICY)"; fi; \
	if [ -n "$(CONDUCTOR_EXECUTE_POLICY)" ]; then set -- "$$@" --execution-policy-path "$(CONDUCTOR_EXECUTE_POLICY)"; fi; \
	if [ "$(CONDUCTOR_REVIEW_INCLUDE_RECOMMENDATIONS)" = "1" ]; then set -- "$$@" --include-recommendations; fi; \
	if [ "$(CONDUCTOR_REVIEW_HARD_ONLY)" = "1" ]; then set -- "$$@" --hard-only; fi; \
	"$$@"

conductor-review-apply:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" review --apply --limit "$(CONDUCTOR_REVIEW_LIMIT)" --max-loops "$(CONDUCTOR_REVIEW_MAX_LOOPS)"; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ROADMAP)" ]; then set -- "$$@" --roadmap "$(CONDUCTOR_TICKET_ROADMAP)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	if [ -n "$(CONDUCTOR_REVIEW_RESUME_FROM)" ]; then set -- "$$@" --resume-from "$(CONDUCTOR_REVIEW_RESUME_FROM)"; fi; \
	if [ -n "$(CONDUCTOR_REVIEW_POLICY)" ]; then set -- "$$@" --review-policy-path "$(CONDUCTOR_REVIEW_POLICY)"; fi; \
	if [ -n "$(CONDUCTOR_EXECUTE_POLICY)" ]; then set -- "$$@" --execution-policy-path "$(CONDUCTOR_EXECUTE_POLICY)"; fi; \
	if [ "$(CONDUCTOR_REVIEW_INCLUDE_RECOMMENDATIONS)" = "1" ]; then set -- "$$@" --include-recommendations; fi; \
	if [ "$(CONDUCTOR_REVIEW_HARD_ONLY)" = "1" ]; then set -- "$$@" --hard-only; fi; \
	"$$@"

conductor-tickets-reset:
	@"$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" tickets-reset --batch-id "$(CONDUCTOR_BATCH_ID)"

conductor-tickets-reset-apply:
	@"$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" tickets-reset --apply --batch-id "$(CONDUCTOR_BATCH_ID)"

conductor-tickets-reset-scan:
	@"$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" tickets-reset --scan-open --scope all-linked

conductor-tickets-reset-scan-apply:
	@"$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" tickets-reset --apply --scan-open --scope all-linked

conductor-run-once:
	@"$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" run-once

conductor-status:
	@"$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" status

conductor-ops-status:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" ops-status --ao-command "$(CONDUCTOR_AO_COMMAND)"; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	"$$@"

conductor-events:
	@"$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor.py" events

conductor-shim-check:
	@"$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/check-conductor-shims.py"

conductor-run:
	@set -- "$(CONDUCTOR_PYTHON)" "$(CURDIR)/tooling/conductor_run.py"; \
	if [ -n "$(CONDUCTOR_ROADMAP_FILE)" ]; then set -- "$$@" --roadmap-file "$(CONDUCTOR_ROADMAP_FILE)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_REPO)" ]; then set -- "$$@" --repo "$(CONDUCTOR_TICKET_REPO)"; fi; \
	if [ -n "$(CONDUCTOR_TICKET_ITEM_PREFIX)" ]; then set -- "$$@" --item-prefix "$(CONDUCTOR_TICKET_ITEM_PREFIX)"; fi; \
	if [ -n "$(CONDUCTOR_AGENT_PROFILE)" ]; then set -- "$$@" --agent-profile "$(CONDUCTOR_AGENT_PROFILE)"; fi; \
	if [ -n "$(CONDUCTOR_BATCH_ID)" ]; then set -- "$$@" --batch-id "$(CONDUCTOR_BATCH_ID)"; fi; \
	if [ "$(CONDUCTOR_DRY_RUN)" = "1" ]; then set -- "$$@" --dry-run; fi; \
	if [ "$(CONDUCTOR_ASSESS)" = "1" ]; then set -- "$$@" --assess; fi; \
	if [ -n "$(CONDUCTOR_RUN_FLAGS)" ]; then set -- "$$@" $(CONDUCTOR_RUN_FLAGS); fi; \
	"$$@"

orchestrator-init:
	@echo "[deprecated] orchestrator-init -> conductor-init (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-init

orchestrator-plan:
	@echo "[deprecated] orchestrator-plan -> conductor-plan (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-plan CONDUCTOR_PLAN_ROADMAP="$(ORCH_PLAN_ROADMAP)"

orchestrator-profiles:
	@echo "[deprecated] orchestrator-profiles -> conductor-profiles (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-profiles

orchestrator-tickets:
	@echo "[deprecated] orchestrator-tickets -> conductor-tickets (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-tickets CONDUCTOR_AGENT_PROFILE="$(AGENT_PROFILE)" CONDUCTOR_BATCH_ID="$(BATCH_ID)" CONDUCTOR_TICKET_REPO="$(ORCH_TICKET_REPO)" CONDUCTOR_TICKET_ROADMAP="$(ORCH_TICKET_ROADMAP)" CONDUCTOR_TICKET_ITEM_PREFIX="$(ORCH_TICKET_ITEM_PREFIX)"

orchestrator-tickets-apply:
	@echo "[deprecated] orchestrator-tickets-apply -> conductor-tickets-apply (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-tickets-apply CONDUCTOR_AGENT_PROFILE="$(AGENT_PROFILE)" CONDUCTOR_BATCH_ID="$(BATCH_ID)" CONDUCTOR_TICKET_REPO="$(ORCH_TICKET_REPO)" CONDUCTOR_TICKET_ROADMAP="$(ORCH_TICKET_ROADMAP)" CONDUCTOR_TICKET_ITEM_PREFIX="$(ORCH_TICKET_ITEM_PREFIX)"

orchestrator-tickets-gemini:
	@echo "[deprecated] orchestrator-tickets-gemini -> conductor-tickets-gemini (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-tickets-gemini CONDUCTOR_BATCH_ID="$(BATCH_ID)" CONDUCTOR_TICKET_REPO="$(ORCH_TICKET_REPO)" CONDUCTOR_TICKET_ROADMAP="$(ORCH_TICKET_ROADMAP)" CONDUCTOR_TICKET_ITEM_PREFIX="$(ORCH_TICKET_ITEM_PREFIX)"

orchestrator-tickets-gemini-apply:
	@echo "[deprecated] orchestrator-tickets-gemini-apply -> conductor-tickets-gemini-apply (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-tickets-gemini-apply CONDUCTOR_BATCH_ID="$(BATCH_ID)" CONDUCTOR_TICKET_REPO="$(ORCH_TICKET_REPO)" CONDUCTOR_TICKET_ROADMAP="$(ORCH_TICKET_ROADMAP)" CONDUCTOR_TICKET_ITEM_PREFIX="$(ORCH_TICKET_ITEM_PREFIX)"

orchestrator-tickets-codex:
	@echo "[deprecated] orchestrator-tickets-codex -> conductor-tickets-codex (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-tickets-codex CONDUCTOR_BATCH_ID="$(BATCH_ID)" CONDUCTOR_TICKET_REPO="$(ORCH_TICKET_REPO)" CONDUCTOR_TICKET_ROADMAP="$(ORCH_TICKET_ROADMAP)" CONDUCTOR_TICKET_ITEM_PREFIX="$(ORCH_TICKET_ITEM_PREFIX)"

orchestrator-tickets-codex-apply:
	@echo "[deprecated] orchestrator-tickets-codex-apply -> conductor-tickets-codex-apply (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-tickets-codex-apply CONDUCTOR_BATCH_ID="$(BATCH_ID)" CONDUCTOR_TICKET_REPO="$(ORCH_TICKET_REPO)" CONDUCTOR_TICKET_ROADMAP="$(ORCH_TICKET_ROADMAP)" CONDUCTOR_TICKET_ITEM_PREFIX="$(ORCH_TICKET_ITEM_PREFIX)"

orchestrator-tickets-reset:
	@echo "[deprecated] orchestrator-tickets-reset -> conductor-tickets-reset (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-tickets-reset CONDUCTOR_BATCH_ID="$(BATCH_ID)"

orchestrator-tickets-reset-apply:
	@echo "[deprecated] orchestrator-tickets-reset-apply -> conductor-tickets-reset-apply (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-tickets-reset-apply CONDUCTOR_BATCH_ID="$(BATCH_ID)"

orchestrator-tickets-reset-scan:
	@echo "[deprecated] orchestrator-tickets-reset-scan -> conductor-tickets-reset-scan (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-tickets-reset-scan CONDUCTOR_BATCH_ID="$(BATCH_ID)"

orchestrator-tickets-reset-scan-apply:
	@echo "[deprecated] orchestrator-tickets-reset-scan-apply -> conductor-tickets-reset-scan-apply (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-tickets-reset-scan-apply CONDUCTOR_BATCH_ID="$(BATCH_ID)"

orchestrator-run-once:
	@echo "[deprecated] orchestrator-run-once -> conductor-run-once (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-run-once

orchestrator-status:
	@echo "[deprecated] orchestrator-status -> conductor-status (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-status

orchestrator-ops-status:
	@echo "[deprecated] orchestrator-ops-status -> conductor-ops-status (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-ops-status CONDUCTOR_AO_COMMAND="$(CONDUCTOR_AO_COMMAND)" CONDUCTOR_TICKET_REPO="$(ORCH_TICKET_REPO)"

orchestrator-events:
	@echo "[deprecated] orchestrator-events -> conductor-events (cleanup pending; use conductor-* targets)." >&2
	@$(MAKE) conductor-events
