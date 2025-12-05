# Cross-repo convenience targets; run from repo root.

REPO_ROOT ?= ..
REPO_ROOT := $(abspath $(REPO_ROOT))
REPOS ?= tv7-core tv7-axum-engine tv7-fastapi-backend tv7-flutter-studio tv7-astro-site
SUBMODULE_PATH ?= 00-tv7-core
CORE_URL ?= git@github.com:TV7-Clip-Studio/tv7-core.git
TOOLING_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/tooling
SYNC_BASE ?= origin/main

.PHONY: status pull-all submodules-init submodules-update bootstrap sync update set-secret update-secrets sync-core bump-core-all update-core

status:
	@bash "$(TOOLING_DIR)/status.sh"

pull-all:
	@for repo in $(REPOS); do \
		path="$(REPO_ROOT)/$$repo"; \
		if [ ! -d "$$path/.git" ]; then \
			echo "!! $$repo missing at $$path"; \
			continue; \
		fi; \
		current_branch="$$(git -C "$$path" rev-parse --abbrev-ref HEAD)"; \
		echo "== pulling $$repo (branch $$current_branch) =="; \
		if git -C "$$path" rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then \
			git -C "$$path" pull --ff-only; \
		elif git -C "$$path" ls-remote --exit-code --heads origin "$$current_branch" >/dev/null 2>&1; then \
			echo "== setting upstream to origin/$$current_branch =="; \
			git -C "$$path" branch --set-upstream-to="origin/$$current_branch" "$$current_branch"; \
			git -C "$$path" pull --ff-only; \
		else \
			echo "!! no upstream for $$repo (branch $$current_branch not on origin) — skipping pull"; \
		fi; \
	done

submodules-init:
	@for repo in $(REPOS); do \
		if [ -d "$(REPO_ROOT)/$$repo/.git" ]; then \
			echo "== init submodules $$repo =="; \
			git -C "$(REPO_ROOT)/$$repo" submodule update --init --recursive; \
		else \
			echo "!! $$repo missing at $(REPO_ROOT)/$$repo"; \
		fi; \
	done

submodules-update:
	@for repo in $(REPOS); do \
		if [ -d "$(REPO_ROOT)/$$repo/.git" ]; then \
			echo "== updating $(SUBMODULE_PATH) in $$repo =="; \
			git -C "$(REPO_ROOT)/$$repo" submodule update --remote $(SUBMODULE_PATH); \
			git -C "$(REPO_ROOT)/$$repo" add $(SUBMODULE_PATH) || true; \
		else \
			echo "!! $$repo missing at $(REPO_ROOT)/$$repo"; \
		fi; \
	done

bootstrap:
	@REPO_ROOT="$(REPO_ROOT)" CORE_URL="$(CORE_URL)" bash "$(TOOLING_DIR)/bootstrap-repos.sh"

sync update:
	@REPO_ROOT="$(REPO_ROOT)" CORE_URL="$(CORE_URL)" QUIET=1 bash "$(TOOLING_DIR)/bootstrap-repos.sh"
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
		if [ "$$status" = "[✓]" ]; then \
			sub_output="$$(git -C "$$path" submodule update --init --recursive $(SUBMODULE_PATH) 2>&1)"; \
			rc_sub=$$?; \
			if [ $$rc_sub -ne 0 ]; then \
				status="[X]"; note="submodule update failed: $$sub_output"; \
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

sync-core:
	@bash "$(TOOLING_DIR)/sync_core_submodules.sh"

bump-core-all:
	@MODE=bump bash "$(TOOLING_DIR)/sync_core_submodules.sh"

update-core:
	@MODE=bump AUTO_PR=1 bash "$(TOOLING_DIR)/sync_core_submodules.sh"
