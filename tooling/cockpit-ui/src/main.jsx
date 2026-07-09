import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Bot, Boxes, CheckCircle2, ChevronDown, ChevronLeft, ChevronRight, CircleAlert,
  Cpu, Database, GitBranch, Globe, LoaderCircle, Play, RefreshCw, Square, Terminal, Timer, Tv, X,
} from "lucide-react";
import "./styles.css";

const providers = ["gemini", "codex", "deepseek"];

function sliceTitle(value) {
  const text = String(value || "General / Clean Slice");
  return (text.split("\n")[0] || text).replace(/^Slice\s*:\s*/i, "").trim();
}

function roadmapTarget(state) {
  if (state.focus?.item_id) return state.focus.item_id;
  const match = String(state.resolved_focus_display || "").match(/[A-Z]{2}-A\d{2}-\d{2}-\d{2}/);
  return match?.[0] || "No active item";
}

async function api(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    ...options,
  });
  if (!response.ok) throw new Error((await response.text()) || response.statusText);
  return response.json();
}

function useWorkspace() {
  const [repositories, setRepositories] = useState([]);
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true);
    try {
      const data = await api("/api/workspace");
      setRepositories(data.repositories || []);
      setServers(data.servers || []);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);
  return { repositories, servers, loading, error, load };
}

function useJobRunner(onDone) {
  const [jobs, setJobs] = useState({});
  const [activeJob, setActiveJob] = useState(null);
  const [openJobs, setOpenJobs] = useState([]);

  const addTab = (jobId) => {
    setOpenJobs(prev => prev.includes(jobId) ? prev : [...prev, jobId]);
    setActiveJob(jobId);
  };

  const closeTab = (jobId) => {
    setOpenJobs(prev => {
      const next = prev.filter(id => id !== jobId);
      if (activeJob === jobId) {
        setActiveJob(next.length ? next[next.length - 1] : null);
      }
      return next;
    });
  };

  const run = async (label, path, body) => {
    const job = await api(path, { method: "POST", body: JSON.stringify(body) });
    setJobs(current => ({ ...current, [job.id]: { ...job, status: "running", label, log: "" } }));
    addTab(job.id);
    const stream = new EventSource(`/api/jobs/${job.id}/events`);
    stream.addEventListener("log", event => {
      const text = JSON.parse(event.data);
      setJobs(current => ({
        ...current,
        [job.id]: { ...current[job.id], log: `${current[job.id]?.log || ""}${text}` },
      }));
    });
    stream.addEventListener("status", event => {
      const result = JSON.parse(event.data);
      setJobs(current => ({ ...current, [job.id]: { ...current[job.id], ...result } }));
    });
    stream.addEventListener("done", event => {
      const result = JSON.parse(event.data);
      setJobs(current => ({ ...current, [job.id]: { ...current[job.id], ...result } }));
      stream.close();
      onDone(job.repo, result);
    });
  };

  const viewLogs = async (jobId) => {
    if (!jobId) return;
    addTab(jobId);
    if (jobs[jobId]) return;
    try {
      const job = await api(`/api/jobs/${jobId}`);
      setJobs(current => ({ ...current, [job.id]: { ...job, status: job.status, label: job.kind, log: "" } }));
      const stream = new EventSource(`/api/jobs/${jobId}/events`);
      stream.addEventListener("log", event => {
        const text = JSON.parse(event.data);
        setJobs(current => ({
          ...current,
          [job.id]: { ...current[job.id], log: `${current[job.id]?.log || ""}${text}` },
        }));
      });
      stream.addEventListener("status", event => {
        const result = JSON.parse(event.data);
        setJobs(current => ({ ...current, [job.id]: { ...current[job.id], ...result } }));
      });
      stream.addEventListener("done", event => {
        const result = JSON.parse(event.data);
        setJobs(current => ({ ...current, [job.id]: { ...current[job.id], ...result } }));
        stream.close();
      });
    } catch (err) {
      console.error("Failed to load existing job logs:", err);
    }
  };

  const cancel = async job => {
    const result = await api(`/api/jobs/${job.id}/cancel`, { method: "POST" });
    setJobs(current => ({ ...current, [job.id]: { ...current[job.id], ...result } }));
  };

  return { jobs, activeJob, openJobs, setActiveJob, run, viewLogs, cancel, closeTab };
}

function ServerIcon({ repo, ...props }) {
  if (repo === "tv7-backend") return <Database {...props} />;
  if (repo === "tv7-engine") return <Cpu {...props} />;
  if (repo === "tv7-site") return <Globe {...props} />;
  if (repo === "tv7-studio") return <Tv {...props} />;
  return <Boxes {...props} />;
}

function cleanServerName(repo) {
  return repo.replace("tv7-", "");
}

function WorkspacePlan({ repositories, servers, runJob, setActiveJob, workspaceLoad, collapsed, setCollapsed }) {
  const [editingPorts, setEditingPorts] = useState({});
  const ordered = [...repositories]
    .filter(repo => !repo.status_ok || repo.action?.state !== "idle")
    .sort((a, b) => (a.action?.priority ?? 99) - (b.action?.priority ?? 99));

  const toggleServer = async (server) => {
    const active = server.status === "active";
    const endpoint = active ? "/api/servers/stop" : "/api/servers/start";
    const selectedPort = Number(editingPorts[server.repo] || server.port);
    const body = { repo: server.repo };
    if (!active && server.can_change_port && selectedPort && selectedPort !== server.port) {
      body.port = selectedPort;
    }
    try {
      await api(endpoint, { method: "POST", body: JSON.stringify(body) });
      await workspaceLoad({ quiet: true });
      setTimeout(() => workspaceLoad({ quiet: true }), 1500);
    } catch (err) {
      alert(`Server action failed: ${err.message}`);
    }
  };

  if (collapsed) {
    return (
      <aside className="workspace-rail collapsed">
        <button className="collapse-btn" onClick={() => setCollapsed(false)} title="Expand sidebar">
          <ChevronRight size={17} />
        </button>
        <div className="collapsed-servers">
          {servers.map(server => (
            <div
              className={`collapsed-server-dot-container`}
              key={server.repo}
              title={`${cleanServerName(server.repo)} (${server.status})`}
            >
              <span className={`collapsed-server-icon ${server.status}`}>
                <ServerIcon repo={server.repo} size={15} />
              </span>
              <span className={`dot-indicator ${server.status}`} />
            </div>
          ))}
        </div>
      </aside>
    );
  }

  return (
    <aside className="workspace-rail">
      <div className="rail-header">
        <div className="rail-title"><Boxes size={17} /> Control Panel</div>
        <button className="collapse-btn" onClick={() => setCollapsed(true)} title="Collapse sidebar">
          <ChevronLeft size={17} />
        </button>
      </div>

      <section className="rail-section">
        <div className="rail-subtitle">🔌 Dev Servers</div>
        <div className="server-list">
          {servers.map(server => {
            const active = server.status === "active";
            const isCore = server.repo === "tv7-core";
            const editing = Object.prototype.hasOwnProperty.call(editingPorts, server.repo);
            return (
              <div className="server-row" key={server.repo}>
                <div className="server-info">
                  <ServerIcon repo={server.repo} size={14} className={`server-icon-symbol ${server.status}`} />
                  <div>
                    <span className="server-name">{cleanServerName(server.repo)}</span>
                    {server.port && !editing && <button
                      className="server-port"
                      disabled={!server.can_change_port || active}
                      onClick={() => setEditingPorts(current => ({ ...current, [server.repo]: String(server.port) }))}
                      title={server.can_change_port ? "Click to choose another port before starting" : "Fixed port"}
                    >:{server.port}</button>}
                    {editing && <input
                      className="server-port-input"
                      value={editingPorts[server.repo]}
                      onChange={event => setEditingPorts(current => ({ ...current, [server.repo]: event.target.value.replace(/\D/g, "").slice(0, 5) }))}
                      onKeyDown={event => {
                        if (event.key === "Escape") setEditingPorts(current => {
                          const next = { ...current };
                          delete next[server.repo];
                          return next;
                        });
                      }}
                      aria-label={`${cleanServerName(server.repo)} port`}
                    />}
                  </div>
                </div>
                <div className="server-controls">
                  {server.active_job_id && (
                    <button
                      className="server-action-btn"
                      onClick={() => setActiveJob(server.active_job_id)}
                      title="View logs"
                    >
                      <Terminal size={12} />
                    </button>
                  )}
                  {!isCore && (
                    <button
                      className={`server-action-btn ${active ? "stop" : "start"}`}
                      onClick={() => toggleServer(server)}
                      title={active ? "Stop server" : "Start server"}
                    >
                      {active ? <Square size={10} fill="currentColor" /> : <Play size={10} fill="currentColor" />}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="rail-section" style={{ marginTop: "20px" }}>
        <div className="rail-subtitle">📋 Action Plan</div>
        <div className="plan-list">
          {ordered.length === 0 && <div className="empty-copy">No repository needs attention.</div>}
          {ordered.map((repo, index) => (
            <a className="plan-row" href={`#${repo.repo}`} key={repo.repo}>
              <span className="plan-index">{index + 1}</span>
              <span><strong>{repo.repo}</strong><small>{repo.action?.label || "Inspect repository"}</small></span>
              <ChevronRight size={15} />
            </a>
          ))}
        </div>
      </section>
    </aside>
  );
}

function ReviewPanel({ state, busy, runJob }) {
  const repo = state.repo;
  const [report, setReport] = useState(null);
  const [reviewer, setReviewer] = useState(localStorage.getItem(`review-${repo}`) || "deepseek");
  const [resolver, setResolver] = useState(localStorage.getItem(`resolve-${repo}`) || "codex");
  const [target, setTarget] = useState(null);

  const load = async () => {
    try { setReport(await api(`/api/assessments/${repo}`)); } catch { setReport(null); }
  };
  useEffect(() => { load(); }, [repo, busy?.status]);
  useEffect(() => {
    if (report && !target) setTarget(report.recommended_scope || "worktree");
  }, [report, target]);

  const select = (kind, setter) => event => {
    localStorage.setItem(`${kind}-${repo}`, event.target.value);
    setter(event.target.value);
  };

  const selectedTarget = target || report?.recommended_scope || "worktree";
  const targetRuns = (report?.runs || []).filter(run => !run.stale && (run.scope || "worktree") === selectedTarget);
  const active = targetRuns[targetRuns.length - 1];
  const latestPr = report?.latest_pr;
  const roadmap = selectedTarget === "roadmap";
  const reviewLabel = roadmap ? "Plan" : selectedTarget === "pull_request" ? "Review PR" : "Review changes";
  const resolveLabel = roadmap ? "Implement" : "Resolve";
  return (
    <section className="assessment">
      <div className="section-heading">
        <span><Bot size={17} /> {roadmap ? "Roadmap planning" : selectedTarget === "pull_request" ? "PR assessment" : "Worktree assessment"}</span>
        <span className={`status ${active?.ready_to_commit ? "success" : active?.issues?.length ? "warning" : "neutral"}`}>
          {active?.verdict === "APPROVED" ? `Approved ${active.confidence ?? ""}%` : active?.ready_to_commit ? "Ready" : active?.issues?.length ? `${active.issues.length} findings` : "Not assessed"}
        </span>
      </div>
      <div className="agent-actions">
        <label>Target<select value={selectedTarget} onChange={event => setTarget(event.target.value)}>{(report?.available_scopes || ["worktree", "roadmap"]).map(scope => <option key={scope} value={scope}>{scope === "pull_request" ? `Pull request #${state.pr?.number}` : scope === "roadmap" ? "Roadmap slice" : "Current changes"}</option>)}</select></label>
        <label>{roadmap ? "Plan with" : "Review with"}<select value={reviewer} onChange={select("review", setReviewer)}>{providers.map(p => <option key={p}>{p}</option>)}</select></label>
        <button disabled={!!busy} onClick={() => runJob(roadmap ? "AI roadmap plan" : "AI review", "/api/ai/review", { repo, model: reviewer, scope: selectedTarget })}>{reviewLabel}</button>
        <label>{roadmap ? "Implement with" : "Resolve with"}<select value={resolver} onChange={select("resolve", setResolver)}>{providers.map(p => <option key={p}>{p}</option>)}</select></label>
        <button className="primary" disabled={!!busy || !active?.issues?.length} onClick={() => runJob(roadmap ? "AI implementation" : "AI resolution", "/api/ai/resolve", { repo, model: resolver, run_id: active?.id })}>{resolveLabel}</button>
      </div>
      {active && <div className="assessment-evidence">
        <div className="evidence-meta"><strong>{active.source === "github_deepseek" ? "GitHub DeepSeek" : active.provider}</strong><span>{active.scope.replace("_", " ")}</span><code>{active.head_sha?.slice(0, 12)}</code>{active.pr_number && <span>PR #{active.pr_number}</span>}</div>
        <p className="review-summary">{active.summary}</p>
        {!!active.issues?.length && <ul className="findings">{active.issues.map((issue, index) => <li key={index}>{issue}</li>)}</ul>}
        {active.raw_output && <details><summary>Full review</summary><pre className="full-review">{active.raw_output}</pre></details>}
      </div>}
      {!active && latestPr && <div className="assessment-evidence secondary-evidence">
        <div className="evidence-meta"><strong>GitHub DeepSeek</strong><span className="status success">{latestPr.verdict} {latestPr.confidence}%</span><code>{latestPr.head_sha?.slice(0, 12)}</code><span>PR #{latestPr.pr_number}</span></div>
        <p className="review-summary">This review covers the committed PR HEAD. Current uncommitted worktree changes still require their own assessment.</p>
        <details><summary>Full PR review</summary><pre className="full-review">{latestPr.raw_output}</pre></details>
      </div>}
      {(report?.runs || []).length > 1 && <details className="assessment-history"><summary>Assessment history ({report.runs.length})</summary>
        <div>{[...(report.runs || [])].reverse().map(run => <div className={run.stale ? "history-row stale" : "history-row"} key={run.id}><strong>{run.source === "github_deepseek" ? "GitHub DeepSeek" : run.provider}</strong><span>{run.scope || "worktree"}</span><code>{run.head_sha?.slice(0, 8)}</code><span>{run.stale ? "stale" : run.verdict || (run.ready_to_commit ? "ready" : "findings")}</span></div>)}</div>
      </details>}
    </section>
  );
}

function ValidationPanel({ state, refreshState }) {
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const plan = state.test_plan || {};
  const submit = async status => {
    setSaving(true);
    try {
      await api("/api/validation", { method: "POST", body: JSON.stringify({ repo: state.repo, status, note }) });
      await refreshState({ quiet: true });
    } finally {
      setSaving(false);
    }
  };
  const machineReady = ["ready", "passed", "failed"].includes(state.queue_status);
  return <section className="validation">
    <div className="section-heading"><span><CheckCircle2 size={17} /> Human validation</span><span className={`status ${state.queue_status === "passed" ? "success" : state.queue_status === "failed" ? "warning" : "neutral"}`}>{state.queue_status || "pending"}</span></div>
    <strong>{plan.title || plan.slice || "General verification"}</strong>
    <p>{plan.where || "Run in the local workspace"}</p>
    {machineReady ? <div className="validation-grid">
      <div><span>Preconditions</span><ul>{(plan.preconditions || []).map(item => <li key={item}>{item}</li>)}</ul></div>
      <div><span>Test steps</span><ol>{(plan.steps || []).map(item => <li key={item}>{item}</li>)}</ol></div>
      <div><span>Expected</span><ul>{(plan.expected || []).map(item => <li key={item}>{item}</li>)}</ul></div>
    </div> : <p className="validation-wait">Run Ready first to unlock the human test contract.</p>}
    {state.queue_status === "ready" && <div className="validation-actions">
      <input value={note} onChange={event => setNote(event.target.value)} placeholder="Optional validation note" />
      <button disabled={saving} onClick={() => submit("failed")}>Fail</button>
      <button className="primary" disabled={saving} onClick={() => submit("passed")}>Pass validation</button>
    </div>}
  </section>;
}

function PrReviewDecision({ state, busy, runJob }) {
  const review = state.workflow?.review;
  const action = state.action || {};
  const mode = state.workflow?.mode;
  const freshDecision = mode === "pr-review-decision";
  const canMerge = freshDecision && review?.head_sha === state.head_sha && state.dirty_file_count === 0 && !state.ahead;
  const confidence = review?.confidence ? `${review.confidence}%` : "unknown confidence";
  const verdict = review?.verdict || "UNKNOWN";

  return (
    <section className="pr-decision">
      <div className="section-heading">
        <span><Bot size={17} /> PR review decision</span>
        <span className={`status ${verdict === "APPROVED" ? "success" : "warning"}`}>{verdict} {confidence}</span>
      </div>
      <p>{state.workflow?.summary}</p>
      {review && <div className="assessment-evidence">
        <div className="evidence-meta">
          <strong>GitHub DeepSeek</strong>
          <span className={review.stale ? "status warning" : "status success"}>{review.stale ? "stale" : "fresh"}</span>
          <code>{review.head_sha?.slice(0, 12)}</code>
          {review.pr_number && <span>PR #{review.pr_number}</span>}
        </div>
        <p className="review-summary">{review.summary}</p>
        {!!review.issues?.length && <ul className="findings">{review.issues.map((issue, index) => <li key={index}>{issue}</li>)}</ul>}
        {review.raw_output && <details open><summary>Full PR review</summary><pre className="full-review">{review.raw_output}</pre></details>}
      </div>}
      <div className="decision-actions">
        {freshDecision && review && (
          <button
            disabled={!!busy}
            onClick={() => runJob("Fix PR review with Codex", "/api/ai/resolve", { repo: state.repo, model: "codex", run_id: review.id })}
          >
            Fix with Codex
          </button>
        )}
        {freshDecision && (
          <button
            className="primary"
            disabled={!!busy || !canMerge}
            onClick={() => runJob("Merge pull request", "/api/actions", { repo: state.repo, action_type: "merge-pr" })}
            title={canMerge ? "Merge reviewed PR and delete branch" : "Latest review must match the current clean HEAD before merge"}
          >
            Merge and delete branch
          </button>
        )}
        {!freshDecision && (
          <button
            className="primary"
            disabled={!!busy}
            onClick={() => runJob(action.label || "Prepare PR follow-up", "/api/actions", { repo: state.repo, action_type: action.state, command: action.command || "" })}
          >
            {busy ? <LoaderCircle size={16} className="spin" /> : <Play size={16} />} Prepare follow-up
          </button>
        )}
        <button disabled={!!busy} onClick={() => window.location.hash = ""}>Defer</button>
      </div>
    </section>
  );
}

function RepositoryCard({ state, busy, runJob, refreshState }) {
  const [expanded, setExpanded] = useState(localStorage.getItem(`expanded-${state.repo}`) === "true");
  const toggle = () => {
    setExpanded(value => { localStorage.setItem(`expanded-${state.repo}`, String(!value)); return !value; });
  };
  const action = state.action || {};
  const [commitMessage, setCommitMessage] = useState(state.suggested_commit_message || "");
  useEffect(() => setCommitMessage(state.suggested_commit_message || ""), [state.suggested_commit_message]);
  const executable = [
    "dirty-needs-ready", "dirty-pr-needs-ready", "ahead-needs-review", "pr-updates-need-review",
    "pr-changes-requested", "pr-awaiting-review", "clean-needs-agent-work", "validated-needs-commit",
  ].includes(action.state);
  const workflowMode = state.workflow?.mode || "idle";
  const decisionMode = ["pr-review-decision", "pr-follow-up", "pr-awaiting-review"].includes(workflowMode);
  return (
    <article id={state.repo} className={`repo-panel ${expanded ? "expanded" : ""}`}>
      <button className="repo-header" onClick={toggle} aria-expanded={expanded}>
        <span className="repo-identity"><strong>{state.repo}</strong><span><GitBranch size={13} />{state.branch}</span></span>
        <span className="repo-indicators">
          {busy && <span className="status running"><LoaderCircle size={13} className="spin" /> {busy.kind}</span>}
          {state.dirty_file_count > 0 && <span className="status warning">{state.dirty_file_count} dirty</span>}
          {state.dirty_file_count === 0 && <span className="status success">Clean</span>}
          <ChevronDown size={18} />
        </span>
      </button>
      {expanded && <div className="repo-content">
        <div className="context-grid">
          <div><span>Active slice</span><strong>{sliceTitle(state.resolved_focus_display)}</strong></div>
          <div><span>Roadmap target</span><strong>{roadmapTarget(state)}</strong></div>
          <div><span>Head</span><code>{state.head_sha?.slice(0, 12)}</code></div>
        </div>
        {!decisionMode && <div className="next-action">
          <div><strong>{action.label || "Inspect repository"}</strong><p>{action.why || state.next_action}</p>{state.pr?.url && <a className="pr-link" href={state.pr.url} target="_blank" rel="noreferrer">PR #{state.pr.number}</a>}</div>
          <div className="next-action-buttons">
            {action.state === "validated-needs-commit" && <input className="commit-message" value={commitMessage} onChange={event => setCommitMessage(event.target.value)} aria-label="Commit message" />}
            {executable && <button className="primary" disabled={!!busy || (action.state === "validated-needs-commit" && !commitMessage.trim())} onClick={() => runJob(action.label || "Action", "/api/actions", { repo: state.repo, action_type: action.state, command: action.command || "", commit_message: commitMessage })}>
              {busy ? <LoaderCircle size={16} className="spin" /> : <Play size={16} />} {busy ? "Running" : action.label}
            </button>}
            {action.state === "pr-ready" && <button className="primary" disabled={!!busy} onClick={() => runJob("Merge pull request", "/api/actions", { repo: state.repo, action_type: "merge-pr" })}>Merge PR</button>}
          </div>
        </div>}
        {decisionMode ? <PrReviewDecision state={state} busy={busy} runJob={runJob} /> : <ReviewPanel state={state} busy={busy} runJob={runJob} />}
        {!decisionMode && state.test_plan && <ValidationPanel state={state} refreshState={refreshState} />}
      </div>}
    </article>
  );
}

function JobConsole({ jobs, openJobs, activeJob, setActiveJob, closeTab, cancel }) {
  const active = jobs[activeJob];
  const [inputValue, setInputValue] = useState("");
  const preRef = React.useRef(null);

  useEffect(() => {
    if (preRef.current) {
      preRef.current.scrollTop = preRef.current.scrollHeight;
    }
  }, [active?.log]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || !active) return;

    const textToSend = inputValue.endsWith("\n") ? inputValue : `${inputValue}\n`;
    setInputValue("");

    try {
      await api(`/api/jobs/${active.id}/input`, {
        method: "POST",
        body: JSON.stringify({ text: textToSend }),
      });
    } catch (err) {
      console.error("Failed to send terminal input:", err);
    }
  };

  if (!active) return null;

  const started = active.started_at ? new Date(active.started_at) : null;
  const elapsed = started ? Math.max(0, Math.floor((Date.now() - started.getTime()) / 1000)) : 0;
  const isRunning = ["queued", "running"].includes(active.status);

  return (
    <aside className="job-console">
      <div className="terminal-tabs-bar">
        <div className="terminal-tabs">
          {openJobs.map(id => {
            const job = jobs[id];
            if (!job) return null;
            const tabActive = id === activeJob;
            const tabRunning = ["queued", "running"].includes(job.status);
            const label = `${job.repo.replace("tv7-", "")} · ${job.label || job.kind.split(":")[0]}`;
            return (
              <div
                key={id}
                className={`terminal-tab ${tabActive ? "active" : ""} ${tabRunning ? "running" : ""}`}
                onClick={() => setActiveJob(id)}
              >
                <span className={`tab-status-dot ${job.status}`} />
                <span className="tab-label">{label}</span>
                <span
                  className="tab-close-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    closeTab(id);
                  }}
                  title="Close tab"
                >
                  <X size={12} />
                </span>
              </div>
            );
          })}
        </div>
        <button className="console-close-all-btn" onClick={() => openJobs.forEach(closeTab)} title="Close all tabs">
          <X size={18} />
        </button>
      </div>
      <header>
        <span><Terminal size={16} /> {active.label || active.kind} · {active.repo}</span>
        <span className="job-meta">
          <span><Timer size={14} /> {active.phase || active.status} · {elapsed}s / {active.timeout_seconds || 600}s</span>
          {isRunning && <button onClick={() => cancel(active)} title="Cancel job"><Square size={15} /> Cancel</button>}
        </span>
      </header>
      <pre ref={preRef}>{active.log || "Waiting for command output..."}</pre>
      {isRunning && (
        <form onSubmit={handleSend} className="terminal-input-form">
          <span className="terminal-prompt">&gt;</span>
          <input
            type="text"
            className="terminal-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type input here and press Enter..."
            autoFocus
          />
        </form>
      )}
    </aside>
  );
}

function App() {
  const workspace = useWorkspace();
  const runner = useJobRunner(async () => workspace.load({ quiet: true }));
  const dirty = workspace.repositories.filter(repo => repo.dirty_file_count > 0).length;
  const [sidebarCollapsed, setSidebarCollapsed] = useState(localStorage.getItem("sidebar-collapsed") === "true");

  const toggleSidebar = (value) => {
    localStorage.setItem("sidebar-collapsed", String(value));
    setSidebarCollapsed(value);
  };

  const refresh = async () => runner.run("Workspace refresh", "/api/workspace/refresh", {});
  return <>
    <div className="app-shell">
      <header className="topbar">
        <div><h1>TV7 Cockpit</h1><p>{workspace.repositories.length}/6 repositories · {dirty} with pending changes</p></div>
        <button onClick={refresh} disabled={Object.values(runner.jobs).some(job => job.kind === "Workspace refresh" && job.status === "running")}><RefreshCw size={16} /> Refresh workspace</button>
      </header>
      {workspace.error && <div className="error-banner"><CircleAlert size={18} />{workspace.error}</div>}
      <div className={`workspace-layout ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
        <WorkspacePlan
          repositories={workspace.repositories}
          servers={workspace.servers || []}
          runJob={runner.run}
          setActiveJob={runner.viewLogs}
          workspaceLoad={workspace.load}
          collapsed={sidebarCollapsed}
          setCollapsed={toggleSidebar}
        />
        <main className="repository-area">
          <div className="area-heading"><h2>Repositories</h2>{workspace.loading && <span><LoaderCircle size={15} className="spin" /> Reading cached state</span>}</div>
          <div className="repo-list">
            {workspace.repositories.map(repo => <RepositoryCard key={repo.repo} state={repo} busy={Object.values(runner.jobs).find(job => job.repo === repo.repo && job.status === "running")} runJob={runner.run} refreshState={workspace.load} />)}
          </div>
        </main>
      </div>
    </div>
    {runner.openJobs.length > 0 && <JobConsole jobs={runner.jobs} openJobs={runner.openJobs} activeJob={runner.activeJob} setActiveJob={runner.setActiveJob} closeTab={runner.closeTab} cancel={runner.cancel} />}
  </>;
}

createRoot(document.getElementById("root")).render(<App />);
