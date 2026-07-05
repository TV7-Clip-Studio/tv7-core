import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Bot, Boxes, CheckCircle2, ChevronDown, ChevronRight, CircleAlert,
  GitBranch, LoaderCircle, Play, RefreshCw, Terminal, X,
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true);
    try {
      const data = await api("/api/workspace");
      setRepositories(data.repositories || []);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);
  return { repositories, loading, error, load };
}

function useJobRunner(onDone) {
  const [jobs, setJobs] = useState({});
  const [activeJob, setActiveJob] = useState(null);

  const run = async (label, path, body) => {
    const job = await api(path, { method: "POST", body: JSON.stringify(body) });
    setJobs(current => ({ ...current, [job.repo]: { ...job, status: "running", label, log: "" } }));
    setActiveJob(job.id);
    const stream = new EventSource(`/api/jobs/${job.id}/events`);
    stream.addEventListener("log", event => {
      const text = JSON.parse(event.data);
      setJobs(current => ({
        ...current,
        [job.repo]: { ...current[job.repo], log: `${current[job.repo]?.log || ""}${text}` },
      }));
    });
    stream.addEventListener("done", event => {
      const result = JSON.parse(event.data);
      setJobs(current => ({ ...current, [job.repo]: { ...current[job.repo], ...result } }));
      stream.close();
      onDone(job.repo, result);
    });
  };

  return { jobs, activeJob, setActiveJob, run };
}

function WorkspacePlan({ repositories }) {
  const ordered = [...repositories]
    .filter(repo => !repo.status_ok || repo.action?.state !== "idle")
    .sort((a, b) => (a.action?.priority ?? 99) - (b.action?.priority ?? 99));
  return (
    <aside className="workspace-rail">
      <div className="rail-title"><Boxes size={17} /> Workspace action plan</div>
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
    </aside>
  );
}

function ReviewPanel({ repo, busy, runJob }) {
  const [report, setReport] = useState(null);
  const [reviewer, setReviewer] = useState(localStorage.getItem(`review-${repo}`) || "deepseek");
  const [resolver, setResolver] = useState(localStorage.getItem(`resolve-${repo}`) || "codex");

  const load = async () => {
    try { setReport(await api(`/api/reviews/${repo}`)); } catch { setReport(null); }
  };
  useEffect(() => { load(); }, [repo, busy?.status]);

  const select = (kind, setter) => event => {
    localStorage.setItem(`${kind}-${repo}`, event.target.value);
    setter(event.target.value);
  };

  return (
    <section className="assessment">
      <div className="section-heading">
        <span><Bot size={17} /> AI code assessment</span>
        <span className={`status ${report?.ready_to_commit ? "success" : report?.issues?.length ? "warning" : "neutral"}`}>
          {report?.ready_to_commit ? "Ready" : report?.issues?.length ? `${report.issues.length} findings` : "Not assessed"}
        </span>
      </div>
      <div className="agent-actions">
        <label>Review with<select value={reviewer} onChange={select("review", setReviewer)}>{providers.map(p => <option key={p}>{p}</option>)}</select></label>
        <button disabled={!!busy} onClick={() => runJob("AI review", "/api/ai/review", { repo, model: reviewer })}>Review</button>
        <label>Resolve with<select value={resolver} onChange={select("resolve", setResolver)}>{providers.map(p => <option key={p}>{p}</option>)}</select></label>
        <button className="primary" disabled={!!busy || !report?.issues?.length} onClick={() => runJob("AI resolution", "/api/ai/resolve", { repo, model: resolver, run_id: report?.active_run_id })}>Resolve</button>
      </div>
      {report?.summary && <p className="review-summary">{report.summary}</p>}
      {!!report?.issues?.length && <ul className="findings">{report.issues.map((issue, index) => <li key={index}>{issue}</li>)}</ul>}
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

function RepositoryCard({ state, busy, runJob, refreshState }) {
  const [expanded, setExpanded] = useState(localStorage.getItem(`expanded-${state.repo}`) === "true");
  const toggle = () => {
    setExpanded(value => { localStorage.setItem(`expanded-${state.repo}`, String(!value)); return !value; });
  };
  const action = state.action || {};
  const executable = [
    "dirty-needs-ready", "ahead-needs-review", "pr-changes-requested",
    "pr-awaiting-review", "pr-ready", "clean-needs-agent-work", "validated-needs-commit",
  ].includes(action.state);
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
        <div className="next-action">
          <div><strong>{action.label || "Inspect repository"}</strong><p>{action.why || state.next_action}</p></div>
          {executable && <button className="primary" disabled={!!busy} onClick={() => runJob(action.label || "Action", "/api/actions", { repo: state.repo, action_type: action.state, command: action.command || "" })}>
            {busy ? <LoaderCircle size={16} className="spin" /> : <Play size={16} />} {busy ? "Running" : action.label}
          </button>}
        </div>
        <ReviewPanel repo={state.repo} busy={busy} runJob={runJob} />
        {state.test_plan && <ValidationPanel state={state} refreshState={refreshState} />}
      </div>}
    </article>
  );
}

function JobConsole({ job, close }) {
  if (!job) return null;
  return <aside className="job-console">
    <header><span><Terminal size={16} /> {job.label || job.kind} · {job.repo}</span><button onClick={close} title="Close console"><X size={18} /></button></header>
    <pre>{job.log || "Waiting for command output..."}</pre>
  </aside>;
}

function App() {
  const workspace = useWorkspace();
  const runner = useJobRunner(async () => workspace.load({ quiet: true }));
  const active = Object.values(runner.jobs).find(job => job.id === runner.activeJob);
  const dirty = workspace.repositories.filter(repo => repo.dirty_file_count > 0).length;

  const refresh = async () => runner.run("Workspace refresh", "/api/workspace/refresh", {});
  return <>
    <div className="app-shell">
      <header className="topbar">
        <div><h1>TV7 Cockpit</h1><p>{workspace.repositories.length}/6 repositories · {dirty} with pending changes</p></div>
        <button onClick={refresh} disabled={!!runner.jobs.workspace && runner.jobs.workspace.status === "running"}><RefreshCw size={16} /> Refresh workspace</button>
      </header>
      {workspace.error && <div className="error-banner"><CircleAlert size={18} />{workspace.error}</div>}
      <div className="workspace-layout">
        <WorkspacePlan repositories={workspace.repositories} />
        <main className="repository-area">
          <div className="area-heading"><h2>Repositories</h2>{workspace.loading && <span><LoaderCircle size={15} className="spin" /> Reading cached state</span>}</div>
          <div className="repo-list">
            {workspace.repositories.map(repo => <RepositoryCard key={repo.repo} state={repo} busy={runner.jobs[repo.repo]?.status === "running" ? runner.jobs[repo.repo] : null} runJob={runner.run} refreshState={workspace.load} />)}
          </div>
        </main>
      </div>
    </div>
    <JobConsole job={active} close={() => runner.setActiveJob(null)} />
  </>;
}

createRoot(document.getElementById("root")).render(<App />);
