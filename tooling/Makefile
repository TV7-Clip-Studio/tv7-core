# Cross-repo convenience targets for TV7 (edit REPOS as needed).

REPO_ROOT ?= ..
REPOS ?= tv7-axum-engine tv7-fastapi-backend tv7-flutter-studio tv7-astro-site
SUBMODULE_PATH ?= 00-tv7-core

.PHONY: status pull-all submodules-init submodules-update

status:
	@for repo in $(REPOS); do \
		if [ -d "$(REPO_ROOT)/$$repo/.git" ]; then \
			echo "== $$repo =="; \
			git -C "$(REPO_ROOT)/$$repo" status --short; \
		else \
			echo "!! $$repo missing at $(REPO_ROOT)/$$repo"; \
		fi; \
	done

pull-all:
	@for repo in $(REPOS); do \
		if [ -d "$(REPO_ROOT)/$$repo/.git" ]; then \
			echo "== pulling $$repo =="; \
			git -C "$(REPO_ROOT)/$$repo" pull --ff-only; \
		fi; \
	done

submodules-init:
	@for repo in $(REPOS); do \
		if [ -d "$(REPO_ROOT)/$$repo/.git" ]; then \
			echo "== init submodules $$repo =="; \
			git -C "$(REPO_ROOT)/$$repo" submodule update --init --recursive; \
		fi; \
	done

submodules-update:
	@for repo in $(REPOS); do \
		if [ -d "$(REPO_ROOT)/$$repo/.git" ]; then \
			echo "== updating $(SUBMODULE_PATH) in $$repo =="; \
			git -C "$(REPO_ROOT)/$$repo" submodule update --remote $(SUBMODULE_PATH); \
			git -C "$(REPO_ROOT)/$$repo" add $(SUBMODULE_PATH) || true; \
		fi; \
	done
