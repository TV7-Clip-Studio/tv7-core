# Cross-repo convenience targets; run from repo root.

REPO_ROOT ?= ..
REPO_ROOT := $(abspath $(REPO_ROOT))
REPOS ?= tv7-core tv7-axum-engine tv7-fastapi-backend tv7-flutter-studio tv7-astro-site
TOOLING_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/tooling
SYNC_BASE ?= origin/main
SKIP_DEPS ?= 0
SKIP_IDE ?= 0

.PHONY: status pull-all bootstrap sync update set-secret update-secrets batch-pr batch-pr-dry-run batch-pr-report batch-pr-open repo-status

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
		if [ -n "$$note" ]; then \
			echo "$$status $$repo ($$branch) - $$note"; \
		else \
			echo "$$status $$repo ($$branch)"; \
		fi; \
	done

set-secret:
	@SECRET_NAME=$(SECRET_NAME) SECRET_VALUE=$(SECRET_VALUE) REPOS="$(REPOS)" ALL=$(ALL) ORG=$(ORG) bash "$(CURDIR)/tooling/set-secret.sh"

batch-pr:
	@REPO_ROOT="$(REPO_ROOT)" OPEN_PR=1 PUSH_BRANCH=1 RUN_CHECKS_IN_ALL_REPOS=1 bash "$(TOOLING_DIR)/batch-pr.sh"

batch-pr-dry-run:
	@REPO_ROOT="$(REPO_ROOT)" DRY_RUN=1 OPEN_PR=1 PUSH_BRANCH=1 RUN_CHECKS_IN_ALL_REPOS=1 bash "$(TOOLING_DIR)/batch-pr.sh"

batch-pr-open:
	@REPO_ROOT="$(REPO_ROOT)" OPEN_PR=1 PUSH_BRANCH=1 RUN_CHECKS_IN_ALL_REPOS=1 bash "$(TOOLING_DIR)/batch-pr.sh"

batch-pr-report repo-status:
	@REPO_ROOT="$(REPO_ROOT)" bash "$(TOOLING_DIR)/repo-status.sh"
