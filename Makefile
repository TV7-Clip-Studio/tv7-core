# Small day-to-day entry points. Advanced historical commands: make -f Makefile.legacy help

REPO_ROOT := $(abspath ..)
TOOLING_DIR := $(CURDIR)/tooling
PYTHON ?= python3
DEV_STATE_DIR ?= $(CURDIR)/docs/.tmp/dev-stack
BACKEND_PORT ?= 8000
ENGINE_PORT ?= 7070
SITE_PORT ?= 4321

.PHONY: help status dev-browser-up dev-browser-status dev-browser-stop dev-studio dev-browser-yt-dlp check precommit-context

help:
	@printf '%s\n' 'TV7 daily workflow (DEVELOPMENT.md; COHORT.md):' \
	  '  make status              Summarize sibling repository state' \
	  '  make dev-browser-up      Start Studio, Engine, and Backend for UI testing' \
	  '  make dev-browser-status  Check local service health' \
	  '  make dev-browser-stop    Stop the browser test stack' \
	  '  make dev-studio          Start the Studio Vite dev server' \
	  '  make dev-browser-yt-dlp Install isolated yt-dlp for local development' \
	  '  make check               Run Core unit tests and diff checks' \
	  'Advanced historical commands: make -f Makefile.legacy <target>'

status:
	@bash "$(TOOLING_DIR)/status.sh"

dev-browser-up dev-browser-status dev-browser-stop:
	@"$(PYTHON)" "$(TOOLING_DIR)/dev-browser-stack.py" $(patsubst dev-browser-%,%,$@)

dev-studio:
	@REPO_ROOT="$(REPO_ROOT)" DEV_STATE_DIR="$(DEV_STATE_DIR)" BACKEND_PORT="$(BACKEND_PORT)" ENGINE_PORT="$(ENGINE_PORT)" SITE_PORT="$(SITE_PORT)" bash "$(TOOLING_DIR)/dev-stack.sh" studio

dev-browser-yt-dlp:
	@"$(PYTHON)" -m venv "$(CURDIR)/docs/.tmp/dev-browser-stack/yt-dlp-venv"
	@"$(CURDIR)/docs/.tmp/dev-browser-stack/yt-dlp-venv/bin/python" -m pip install 'yt-dlp[default]==2026.8.19'
	@echo '[ok] installed isolated yt-dlp; Node 22+ is needed for YouTube JavaScript challenges'

check precommit-context:
	@"$(PYTHON)" -m compileall -q "$(TOOLING_DIR)"
	@PYTHONPATH="$(TOOLING_DIR):$${PYTHONPATH:-}" "$(PYTHON)" -m unittest discover -s "$(TOOLING_DIR)/tests" -p 'test_*.py'
	@git diff --check
