# AI Code Reviewer

This project uses a custom AI agent (powered by DeepSeek) to act as a **Senior Code Reviewer** on every Pull Request.

## How it Works
1.  **Automated Context**: When you open a PR, the local workflow (e.g., `ai-review.yml` in your repo) automatically scans your project files (like `pubspec.yaml` or `pyproject.toml`).
2.  **Context Injection**: It builds a summary of your key dependencies and versions (e.g., "Flutter 3.x, Riverpod 2.x") and sends this along with your PR diff to the AI.
3.  **Review**: The AI analyzes your changes, checking for logic errors, security risks, and architectural issues.

## The Reviewer Persona
The AI is instructed to behave like a strict Senior Engineer. It prioritizes:
*   **Correctness**: Logic bugs, race conditions, off-by-one errors.
*   **Security**: leaked secrets, SQL injection, unsafe data handling.
*   **Architecture**: adherence to project patterns (it reads `tv7-core/docs` for this).
*   **Maintenance**: readability, variable naming, and complexity.

> **Note**: It explicitly avoids "nitpicking" style or formatting issues, as those are handled by linters.

## The Verdict
The AI will post a **single comment** on your PR with one of two verdicts:

### Comment Schema (Enforced)
The posted DeepSeek review uses a minimal wrapper:
- `DeepSeek review`
- `Confidence: NN%` (or `unknown`)
- `Final verdict: APPROVED | REJECTED | COMMENT`
- `Model narrative` (DeepSeek output preserved as-is)

Rules:
- PR title/body are **not** modified by DeepSeek workflow.
- DeepSeek narrative must follow this mini-structure in order: `Summary`, `Findings`, `Risks`, `Recommendations`.
- Findings must describe problem + impact + evidence (`path[:line]`) when available.
- If verdict parsing fails, the workflow posts `COMMENT` with `Confidence: unknown`.

### ✅ APPROVED (NN%)
*   **Meaning**: The code looks safe and correct.
*   **Action**: You may proceed to merge (pending human approval if required).
*   **Score**: The percentage indicates the AI's confidence in code quality (0-100%).

### ❌ REQUEST CHANGES (NN%)
*   **Meaning**: The AI found a **blocking issue** (e.g., a bug or security flaw).
*   **Action**:
    1.  Read the specific feedback.
    2.  Fix the issue or explain why it is a false positive in a reply.
    3.  Push a new commit to trigger a re-review.
