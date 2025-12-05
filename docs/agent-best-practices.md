# TV7 Agent Best Practices  
*A unified standard for all automated development agents in the TV7 ecosystem.*

---

## 1. Overview & Purpose

TV7 uses multiple AI-powered development agents (Codex, Architect, Repo Agents, Specialized Agents) to support code generation, analysis, refactoring, and documentation across many repositories.

This document provides **one centralized set of rules** that all agents must follow.

Goals:

- Predictable, safe automation  
- High-quality and maintainable code  
- Clear repo boundaries & ownership  
- Human-controlled execution  
- Consistent workflows across all TV7 repos  

All agents must read and follow this document at the start of each new session.

---

## 2. Agent Roles

### 2.1 Core / Architect Agent
- Maintains `tv7-core` standards, architecture docs, reusable workflows, and templates.
- Responsible for multi-repo thinking.
- May propose cross-repo changes, but only edits other repos when explicitly instructed.

### 2.2 Repo Agents
- One per repo (backend, astro-site, flutter-studio, axum-engine, etc.).
- Modify **only their own repo** unless authorized by the human.
- Must follow the standards defined in `tv7-core`.

### 2.3 Specialized Agents
Examples: Testing agent, Documentation agent, CI/CD agent.  
They follow the same rules but focus on their specialty.

---

## 3. Global Principles (The Five Rules)

1. **Plan first — never execute automatically.**  
2. **Modify only the current repo unless explicitly told otherwise.**  
3. **PRs and code changes must be small, focused, and easy to review.**  
4. **Never expose secrets or tokens in logs, drafts, or docs.**  
5. **Prefer clarity and safety over cleverness.**

These rules override all others.

---

## 4. Planning vs Execution Protocol

### 4.1 Planning Phase (default)
Agents must:

- Restate the task  
- Produce a numbered **Implementation Plan**  
- Wait for human approval before making ANY changes  

Agents must NOT:

- Modify files  
- Stage commits  
- Push branches  
- Open PRs  
- Make permanent changes  

If the human writes “let’s plan,” “what’s the approach,” or similar, the agent stays in planning mode.

---

### 4.2 Execution Phase  
Agent enters execution only if the human explicitly says:

- “Execute the plan”  
- “Implement this”  
- “Go ahead”  
- “Apply the changes”

Once in execution:

- Follow the plan step by step  
- Report progress  
- Stop and re-plan if unexpected issues occur  
- Provide a final summary of what changed and why  

---

### 4.3 Forbidden Auto-Actions

Agents must **never**:

- Assume previous instructions still apply  
- Auto-execute on ambiguous wording  
- Modify repo secrets or config unintentionally  
- Perform destructive git actions (`rebase -f`, deleting branches, etc.)

---

## 5. Cross-Repo Behavior: Read Global, Write Local

### 5.1 Default Rule
> **Agents may read any TV7 repo, but may only modify their own repo.**

They may inspect:

- File structures  
- Workflows  
- Architecture  
- Cross-repo dependencies  

But must NOT modify other repos unless explicitly allowed.

---

### 5.2 Cross-Repo Handoff Protocol

If a change affects other repos, the agent must:

1. Read and analyze the repo(s) involved.  
2. Write a **handoff plan**, either:
   - As a section in chat titled  
     **“Instructions for `<repo>` Agent”**,  
   - Or as a temp file:  
     `docs/_agent-handoff-<repo>.md`

The handoff plan must include:

- Files to update  
- Exact changes required  
- Order of operations  
- Risks or migration notes  
- Dependency on tv7-core or other PRs  

Human then copies that plan to the other repo’s agent.

---

### 5.3 Explicit Override Rule  
If the human explicitly says:

- “You may modify both repos for this task”  
- “This requires modifying backend + core; proceed”  

Then the agent may edit multiple repos **for that task only**.

Agent responsibilities in multi-repo mode:

- Create separate, clearly documented changes per repo  
- List which repos were modified  
- Explain ordering dependencies  
- Ensure PRs do not break CI in dependent repos  

---

## 6. Coding Standards & Tooling

### 6.1 Python / FastAPI Backend
- Formatter: **black**
- Linter: **ruff**
- Type checking: **mypy** (if enabled)
- Tests: **pytest**

### 6.2 Astro / React
- Formatter: **prettier**
- Linter: **eslint**

### 6.3 Flutter / Dart
- Formatter: **dart format**
- Analyzer: **dart analyze**

### 6.4 Rust (Axum)
- Formatter: **cargo fmt**
- Linter: **cargo clippy**
- Tests: **cargo test**

### 6.5 General Coding Style Rules
- Prefer clarity over cleverness  
- Keep functions small and focused  
- Follow existing patterns before adding new ones  
- Add docstrings/comments for non-obvious logic  

---

## 7. Git & GitHub Conventions (Human-driven, Agent-assisted)

Agents may run **read-only git commands** (status, diff, fetch) to report state, but do **not** push, commit, or create PRs.  
Humans execute:

- `git add`
- `git commit`
- `git push`
- PR creation and merging

Agents simply **propose** the metadata.

---

### 7.1 Suggested Branch Naming (agent proposes, human creates)

Agents should propose a branch name when applicable:

- `feat/<short-description>`
- `fix/<bug>`
- `chore/<task>`
- `refactor/<module>`

Example proposal:

> **Suggested branch name:**  
> `feat/deepseek-ai-review`

---

### 7.2 Suggested Commit Messages (agent proposes, human commits)

Agents propose commit messages grouped by logical change.

Rules:

- One logical change per commit  
- Imperative tense  
- Short, clear messages  

Examples:

- `feat: add DeepSeek AI review workflow`
- `fix: correct audio clipping in ffmpeg pipeline`
- `chore: update README instructions`

Agents should output something like:

> **Suggested commits:**  
> 1. `feat: add DeepSeek AI review workflow`  
> 2. `docs: document DeepSeek setup in ai-code-review.md`

---

### 7.3 Suggested Pull Request Metadata (agent drafts, human creates PR)

Agents provide a **PR title and body**.  
Human pastes or adapts these into GitHub.

PR title example:

> `feat: add DeepSeek AI code review workflow`

PR description should include:

- **Summary** of changes  
- **Reason** for the change  
- **Impacted files/modules**  
- **Tests added/updated**  
- **Notes on repo setup**  
- **Cross-repo dependencies**, if any  

The **CR agent** will review both code and PR description.

---

## 8. Testing & Validation Before Marking Code “Ready”

Agents must:

- Run or reference appropriate tests  
- Ensure formatting/linting follows repo rules  
- Confirm workflows (YAML) do not contain syntactic errors  
- Validate cross-repo compatibility when needed  

If full test suites are too heavy, agents must:

- Explain what subset was validated  
- List what still needs testing by humans or CI  

---

## 9. AI Model & Cost Guardrails

To keep operational costs predictable:

- Use **DeepSeek** for automated code review workflows (GitHub Actions)  
- Use OpenAI/Codex only for architectural planning or summaries when needed  
- Use cheap or free-tier models unless the human requests otherwise  
- Avoid retriggering expensive actions on minor changes  
- Always prefer minimal, necessary context rather than entire repo dumps  

---

## 10. Security Rules

Agents must **never**:

- Output secrets or credentials  
- Commit `.env`, API keys, tokens, or credential files  
- Reference secret values in logs or PR text  
- Replace or rewrite sensitive files without explicit permission  

If a file looks like it may contain secrets:

> The agent must stop and ask the human what to do.

---

## 11. Documentation Responsibilities

Agents must update or create documentation when logic, workflows, or architecture changes.

This includes:

- README updates  
- Architecture diagrams  
- Workflow documentation  
- Feature documentation  
- Migration notes  

If any change modifies standards or recurring practices:

> The Architect agent must update **this** file (`agent-best-practices.md`).

---

## 12. File Location & Reuse

This document is located at:
tv7-core/docs/agent-best-practices.md

It is the **single source of truth**.  
All repo-level agent instructions must reference this document.

Other repos may include a stub pointing here, for example:
See tv7-core/docs/agent-best-practices.md for current agent rules.


---

