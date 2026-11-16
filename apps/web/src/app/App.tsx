import { useEffect, useState, useCallback } from "react";
import {
  Link,
  NavLink,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  Inbox,
  LayoutDashboard,
  MessageSquare,
  Activity,
  BarChart3,
  Settings,
  Search,
  ShieldCheck,
  Sparkles,
  Briefcase,
  LogOut,
  FileCheck,
  ChevronRight,
  Plus,
  Menu,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Layers,
} from "lucide-react";
import {
  api,
  watchRun,
  type Profile,
  type Job,
  type Run,
  type Approval,
} from "../lib/api/client";
import { EvidenceHover, type Evidence } from "../components/EvidenceHover";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { RunTimeline } from "../components/RunTimeline";

type Data = Record<string, any>;
function useData<T>(path: string) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState("");
  const load = useCallback(
    () =>
      api<T>(path)
        .then((x) => {
          setData(x);
          setError("");
        })
        .catch((e) => setError(e.message)),
    [path],
  );
  useEffect(() => {
    load();
    if (path === "/health") {
      const timer = setInterval(load, 5000);
      return () => clearInterval(timer);
    }
  }, [load, path]);
  return { data, error, reload: load };
}
function ErrorBox({ error }: { error: string }) {
  return error ? (
    <div role="alert" className="error-box">
      <AlertTriangle size={18} />
      {error}
    </div>
  ) : null;
}
function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty">
      <Layers size={34} />
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}
function Badge({ value }: { value: string }) {
  return (
    <span
      className={
        "badge " +
        (["submitted", "sent", "bid", "approved"].includes(value)
          ? "green"
          : ["blocked", "skipped", "rejected"].includes(value)
            ? "red"
            : "amber")
      }
    >
      {value.replaceAll("_", " ")}
    </span>
  );
}

export default function App() {
  const [signed, setSigned] = useState(!!localStorage.getItem("gigbid-token")),
    [menu, setMenu] = useState(false);
  const { data: health } = useData<Data>("/health");
  if (!signed) return <Auth onSignIn={() => setSigned(true)} />;
  const nav = [
    ["/inbox", "Job inbox", Inbox],
    ["/pipeline", "Pipeline", LayoutDashboard],
    ["/messages", "Messages", MessageSquare],
    ["/runs", "Agent runs", Activity],
    ["/analytics", "Analytics", BarChart3],
    ["/settings", "Settings", Settings],
  ] as const;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className={menu ? "sidebar open" : "sidebar"}>
        <Link to="/inbox" className="brand">
          <span className="brand-mark">
            g<span>↗</span>
          </span>
          gigbid<span className="brand-period">.</span>
        </Link>
        <div className="workspace-tag">
          <span className="avatar">SK</span>
          <div>
            My workspace<small>Independent freelancer</small>
          </div>
          <span className="online-dot" />
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav>
          {nav.map(([to, label, Icon]) => (
            <NavLink key={to} to={to} onClick={() => setMenu(false)}>
              <Icon size={19} />
              {label}
              {to === "/inbox" && <span className="nav-count">New</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="control-card">
            <ShieldCheck size={21} />
            <strong>You’re in control</strong>
            <p>Every proposal and message waits for your approval.</p>
            <Link to="/settings">
              Manage preferences <ArrowUpRight size={14} />
            </Link>
          </div>
          <button
            className="account"
            onClick={() => {
              localStorage.removeItem("gigbid-token");
              setSigned(false);
            }}
          >
            <span className="avatar dark">Y</span>
            <span>
              Your account<small>Local workspace</small>
            </span>
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <button
              className="icon-button mobile-menu"
              aria-label="Toggle navigation"
              onClick={() => setMenu(!menu)}
            >
              <Menu size={20} />
            </button>
            <span className="breadcrumb">
              Workspace <ChevronRight size={13} />{" "}
              <strong>Freelancer copilot</strong>
            </span>
          </div>
          <div className="topbar-right">
            <span className="status-dot" />
            Local workspace
            <span className="separator" />
            <span className="small-avatar">Y</span>
          </div>
        </header>
        {health?.marketplace === "unavailable" && (
          <div role="alert" className="degraded">
            <AlertTriangle size={17} />
            Marketplace unavailable. Work is saved and will retry when the
            service returns.
          </div>
        )}
        <main id="main">
          <Routes>
            <Route path="/inbox" element={<InboxPage />} />
            <Route path="/jobs/:id" element={<JobPage />} />
            <Route path="/studio/:id" element={<StudioPage />} />
            <Route path="/pipeline" element={<PipelinePage />} />
            <Route path="/messages" element={<MessagesPage />} />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="/runs/:id" element={<RunPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/onboarding" element={<SettingsPage onboarding />} />
            <Route path="*" element={<InboxPage />} />
          </Routes>
        </main>
        <footer>
          Built around your evidence. Guided by your judgment.
          <span>GigBid · AI-4016</span>
        </footer>
      </div>
    </div>
  );
}

function Auth({ onSignIn }: { onSignIn: () => void }) {
  const [register, setRegister] = useState(false),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  return (
    <div className="auth-layout">
      <section className="auth-story">
        <div className="brand light">
          <span className="brand-mark">g↗</span>gigbid.
        </div>
        <span className="eyebrow">LESS SEARCHING. MORE MEANINGFUL WORK.</span>
        <h1>
          Your next opportunity.
          <br />
          <em>Backed by evidence.</em>
        </h1>
        <p>
          A thoughtful copilot for finding the right freelance jobs and telling
          your story with work you can prove.
        </p>
        <div className="auth-points">
          <p>
            <ShieldCheck />
            Portfolio-grounded proposals
          </p>
          <p>
            <FileCheck />
            Your approval, every time
          </p>
          <p>
            <Activity />A clear view of every decision
          </p>
        </div>
        <small>Local development mode · Synthetic personas and jobs</small>
      </section>
      <section className="auth-form">
        <span className="eyebrow">YOUR FREELANCE WORKSPACE</span>
        <h2>{register ? "Make room for better work." : "Welcome back."}</h2>
        <p>
          {register
            ? "Create an account to choose your persona and preferences."
            : "Sign in to your opportunities, proposals, and conversations."}
        </p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            try {
              const d = await api<Data>(
                "/auth/" + (register ? "register" : "login"),
                "POST",
                { email, password },
              );
              localStorage.setItem("gigbid-token", d.access_token);
              onSignIn();
              navigate(register ? "/onboarding" : "/inbox");
            } catch (err) {
              setError(String(err));
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Email address
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              minLength={8}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
            />
          </label>
          <ErrorBox error={error} />
          <button className="primary" disabled={busy}>
            {busy
              ? "Opening workspace…"
              : register
                ? "Create account"
                : "Sign in"}
            <ArrowRight size={17} />
          </button>
        </form>
        <button className="text-button" onClick={() => setRegister(!register)}>
          {register
            ? "Already have an account? Sign in"
            : "New here? Create an account"}
        </button>
        <p className="auth-note">
          <ShieldCheck size={15} />
          Nothing is sent without your approval.
        </p>
      </section>
    </div>
  );
}

function InboxPage() {
  const { data: feedHealth } = useData<Data>("/health");
  const [query, setQuery] = useState(""),
    [filter, setFilter] = useState("All opportunities");
  const { data, error, reload } = useData<{ jobs: Job[] }>("/jobs");
  const jobs = (data?.jobs || []).filter(
    (j) =>
      (j.title + " " + j.description)
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (filter === "All opportunities" ||
        (filter === "Ready to review"
          ? j.run?.status === "awaiting_approval"
          : j.run?.status === "skipped")),
  );
  const analyzed = (data?.jobs || []).filter(
    (j) => j.run?.state?.decision,
  ).length;
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">YOUR NEXT CHAPTER</span>
          <h1>
            Good work starts with a good fit<span>.</span>
          </h1>
          <p>
            Your opportunities, with the context to make a confident decision.
          </p>
        </div>
        <button className="secondary" onClick={reload}>
          <Activity size={16} /> Refresh feed
        </button>
      </div>
      <div className="stats-grid">
        <Stat
          label="In your inbox"
          value={String(data?.jobs.length ?? "—")}
          sub="Opportunities to explore"
          icon={<Inbox />}
        />
        <Stat
          label="Analyzed for you"
          value={String(analyzed)}
          sub="Fit, risk & evidence reviewed"
          icon={<Sparkles />}
        />
        <Stat
          label="Awaiting your review"
          value={String(
            (data?.jobs || []).filter(
              (j) => j.run?.status === "awaiting_approval",
            ).length,
          )}
          sub="You decide what goes out"
          icon={<FileCheck />}
        />
      </div>
      <section className="opportunity-section">
        <div className="section-header">
          <div>
            <h2>
              Your opportunities{" "}
              <span className="count-pill">{jobs.length}</span>
            </h2>
            <p>A clearer picture before you invest your time.</p>
          </div>
          <span className="subtle-label">
            <span className="status-dot" />{" "}
            {feedHealth?.mode === "upwork"
              ? "Connected Upwork feed"
              : feedHealth?.mode === "gigsim"
                ? "Connected GigSim feed"
                : "Synthetic development feed"}
          </span>
        </div>
        <div className="inbox-toolbar">
          <div className="tabs">
            {["All opportunities", "Ready to review", "Skipped"].map((x) => (
              <button
                key={x}
                className={filter === x ? "active" : ""}
                onClick={() => setFilter(x)}
              >
                {x}
              </button>
            ))}
          </div>
          <label className="search-field">
            <Search size={17} />
            <input
              aria-label="Search opportunities"
              placeholder="Search opportunities…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
        </div>
        <ErrorBox error={error} />
        {!data && !error ? (
          <p className="loading">Loading your opportunities…</p>
        ) : jobs.length === 0 ? (
          <Empty
            title="A little quiet here"
            body="Try another search or change your saved filters."
          />
        ) : (
          <div className="job-grid">
            {jobs.map((j) => (
              <JobCard key={j.id} job={j} />
            ))}
          </div>
        )}
      </section>
      <div className="inbox-note">
        <ShieldCheck size={18} />
        <span>
          <strong>Specific claims. Real evidence. Your call.</strong> Every
          draft links to portfolio sources and waits for your approval.
        </span>
      </div>
    </>
  );
}
function Stat({
  label,
  value,
  sub,
  icon,
}: {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="stat">
      <div className="stat-title">
        {label}
        <span>{icon}</span>
      </div>
      <strong>{value}</strong>
      <p>{sub}</p>
    </div>
  );
}
function JobCard({ job: j }: { job: Job }) {
  const state = (j.run?.state || {}) as Data;
  return (
    <article className="job-card">
      <div className="card-top">
        <span className="category">
          <Briefcase size={13} />
          {j.skills[0] || "Freelance project"}
        </span>
        {state.risk ? (
          <span
            className={
              "risk-label " + (state.risk.score >= 0.7 ? "high" : "low")
            }
          >
            <span />
            {state.risk.score >= 0.7 ? "High risk" : "Risk reviewed"}
          </span>
        ) : (
          <span className="unreviewed">Unreviewed</span>
        )}
      </div>
      <Link className="job-title" to={"/jobs/" + j.id}>
        <h3>{j.title}</h3>
        <ArrowUpRight size={18} />
      </Link>
      <div className="job-money">
        <strong>
          ${j.budget_min}–{j.budget_max}
        </strong>
        <span>/ hr · USD</span>
      </div>
      <p className="job-excerpt">{j.description.split(" Ignore")[0]}</p>
      <div className="skill-tags">
        {j.skills.slice(0, 3).map((s) => (
          <span key={s}>{s}</span>
        ))}
      </div>
      <div className="card-divider" />
      <div className="card-bottom">
        <span className="fit-score">
          <span className="fit-icon">✦</span>
          {state.fit ? (
            <>
              <strong>{Math.round(state.fit.score * 100)}%</strong> evidence fit
            </>
          ) : (
            "Ready for analysis"
          )}
        </span>
        <span className="connects">{j.connects} Connects</span>
      </div>
      {j.run && (
        <div className="card-run">
          <Badge value={j.run.status} />
          <Link to={"/studio/" + j.run.id}>
            Open workspace <ArrowRight size={14} />
          </Link>
        </div>
      )}
    </article>
  );
}

function JobPage() {
  const { id } = useParams();
  const { data, error } = useData<{ jobs: Job[] }>("/jobs");
  const job = data?.jobs.find((j) => j.id === id);
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false),
    [localError, setError] = useState("");
  const state = (job?.run?.state || {}) as Data;
  return (
    <>
      <Link to="/inbox" className="back-link">
        ← Back to opportunities
      </Link>
      <ErrorBox error={error || localError} />
      {job ? (
        <>
          <div className="page-heading">
            <div>
              <span className="eyebrow">OPPORTUNITY DETAIL</span>
              <h1>{job.title}</h1>
              <p>
                ${job.budget_min}–{job.budget_max}/hr · {job.connects} Connects
                · Synthetic job
              </p>
            </div>
            <button
              className="primary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  const run = await api<Run>("/runs", "POST", {
                    job_id: job.id,
                  });
                  navigate("/studio/" + run.id);
                } catch (e) {
                  setError(String(e));
                  setBusy(false);
                }
              }}
            >
              {busy
                ? "Queueing…"
                : job.run
                  ? "Open analysis"
                  : "Analyze & draft"}
              <Sparkles size={16} />
            </button>
          </div>
          <div className="detail-grid">
            <section className="panel">
              <h2>The brief</h2>
              <p className="preserve-text">{job.description}</p>
              <div className="skill-tags">
                {job.skills.map((s) => (
                  <span key={s}>{s}</span>
                ))}
              </div>
              <h3>What we know</h3>
              {state.spec ? (
                <>
                  <p>{state.spec.deliverables?.join("; ")}</p>
                  <p>{state.spec.hidden_needs?.join("; ")}</p>
                </>
              ) : (
                <p className="muted">
                  Run an analysis to inspect deliverables and hidden needs.
                </p>
              )}
            </section>
            <aside className="panel">
              <h2>Before you bid</h2>
              {state.risk ? (
                <>
                  <Badge value={state.decision?.action || "watch"} />
                  <p>Risk score: {Math.round(state.risk.score * 100)}%</p>
                  {state.risk.flags.map((x: string) => (
                    <p key={x} className="warning">
                      {x}
                    </p>
                  ))}
                  <p>{state.decision?.reasons.join("; ")}</p>
                  <p>{state.price?.rationale}</p>
                </>
              ) : (
                <>
                  <ShieldCheck className="large-icon" />
                  <p>
                    We’ll review client risk, portfolio coverage, and price
                    before drafting.
                  </p>
                  <small>
                    Analysis does not submit a proposal or spend Connects.
                  </small>
                </>
              )}
            </aside>
          </div>
          <section className="panel">
            <h2>Requirement → evidence</h2>
            {state.fit?.matrix ? (
              <div className="requirement-grid">
                {state.fit.matrix.map((m: Data) => (
                  <div key={m.requirement}>
                    <strong>{m.requirement}</strong>
                    <Badge value={m.supported ? "supported" : "missing"} />
                    {m.evidence_ids.map((eid: string) => {
                      const item = state.fit.evidence.find(
                        (e: Evidence) => e.id === eid,
                      );
                      return item ? (
                        <EvidenceHover key={eid} item={item} />
                      ) : null;
                    })}
                  </div>
                ))}
              </div>
            ) : (
              <Empty
                title="Evidence comes first"
                body="The fit matcher will connect each requirement to specific portfolio items."
              />
            )}
          </section>
        </>
      ) : (
        !error && <p className="loading">Loading opportunity…</p>
      )}
    </>
  );
}

function useRun(id: string | undefined) {
  const { data, error, reload } = useData<Run>("/runs/" + id);
  const [live, setLive] = useState<Run | null>(null);
  useEffect(() => {
    setLive(null);
    if (!id) return;
    const abort = new AbortController();
    watchRun(id, setLive, abort.signal).catch(() => {});
    return () => abort.abort();
  }, [id, data?.updated]);
  return {
    run: live && live.updated >= (data?.updated || 0) ? live : data,
    error,
    reload,
  };
}
function StudioPage() {
  const { id } = useParams();
  const { run, error, reload } = useRun(id);
  const [text, setText] = useState(""),
    [base, setBase] = useState(""),
    [message, setMessage] = useState("");
  const state = (run?.state || {}) as Data;
  useEffect(() => {
    const draft =
      typeof state.draft === "string" ? state.draft : state.draft?.text;
    if (draft !== undefined) {
      setText(draft);
      setBase(draft);
    }
  }, [state.draft?.text, typeof state.draft === "string" ? state.draft : ""]);
  const action = async (a: Approval) => {
    await api("/runs/" + id + "/approval", "POST", {
      ...a,
      text: a.action === "edit" ? text : undefined,
    });
    setMessage(
      a.action === "edit"
        ? "Edits saved. Checks are running again."
        : a.action === "reject"
          ? "Rejected. Your reason was saved."
          : "Approved. The worker will dispatch this exact draft.",
    );
    reload();
  };
  const claims = state.draft?.claims || [];
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">PROPOSAL STUDIO</span>
          <h1>
            A proposal you can stand behind<span>.</span>
          </h1>
          <p>
            {state.job?.title || "Your agent is collecting the context."}
            {state.fit?.persona
              ? ` ? Routed to ${state.fit.persona.toUpperCase()} member`
              : ""}
          </p>
        </div>
        {run && <Badge value={run.status} />}
      </div>
      <ErrorBox error={error || run?.error || ""} />
      {message && (
        <div role="status" className="success-box">
          {message}
        </div>
      )}
      {run &&
        ["queued", "running", "analysing", "drafting", "queued_retry"].includes(
          run.status,
        ) && (
          <div className="progress-banner">
            <Activity size={20} />
            <div>
              <strong>
                {run.status === "queued_retry"
                  ? "Marketplace unavailable. Run queued for recovery."
                  : "Your copilot is working."}
              </strong>
              <p>Progress is saved. You can leave this page and come back.</p>
            </div>
          </div>
        )}
      <div className="studio-grid">
        <div>
          <section className="panel">
            <div className="section-header">
              <h2>Your draft</h2>
              <span className="subtle-label">
                {text.split(/\s+/).filter(Boolean).length} words
              </span>
            </div>
            <label className="sr-only" htmlFor="draft-editor">
              Proposal draft
            </label>
            <textarea
              id="draft-editor"
              className="draft-editor"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Your evidence-grounded draft will appear here."
            />
            <div className="editor-footer">
              <ShieldCheck size={15} />
              Edited claims are checked before approval.
              <button
                className="text-button"
                disabled={!run || run.status !== "awaiting_approval"}
                onClick={() => {
                  setText(
                    base
                      .split("\n")
                      .map((line, i) =>
                        i === base.split("\n").length - 1
                          ? "Could you share the acceptance criteria and sample inputs?"
                          : line,
                      )
                      .join("\n"),
                  );
                }}
              >
                Regenerate closing question
              </button>
            </div>
          </section>
          {Object.keys(state.draft?.screening_answers || {}).length > 0 && (
            <section className="panel">
              <h2>Screening answers</h2>
              {Object.entries(state.draft.screening_answers).map(([q, a]) => (
                <details key={q} className="evidence">
                  <summary>{q}</summary>
                  <p>{String(a)}</p>
                </details>
              ))}
            </section>
          )}
          {state.preview && (
            <ApprovalPanel
              kind={run?.kind === "conversation" ? "message" : "proposal"}
              pending={run?.status === "awaiting_approval"}
              changed={text !== base}
              preview={state.preview}
              onAction={action}
            />
          )}
          <section className="panel">
            <h2>Agent progress</h2>
            <RunTimeline events={state.events || []} />
            {id && (
              <Link to={"/runs/" + id} className="inline-link">
                Inspect full run <ArrowUpRight size={14} />
              </Link>
            )}
          </section>
        </div>
        <aside>
          <section className="panel evidence-panel">
            <span className="eyebrow">GROUNDED IN YOUR WORK</span>
            <h2>Evidence behind the words</h2>
            <p className="muted">
              Open a claim to inspect the portfolio source.
            </p>
            {claims.map((c: Data, i: number) => (
              <div className="claim" key={i}>
                <Badge value={c.status} />
                <p tabIndex={0} title={c.reason}>
                  {c.text}
                </p>
                {c.evidence_ids.map((eid: string) => {
                  const item = state.fit?.evidence?.find(
                    (e: Evidence) => e.id === eid,
                  );
                  return item ? <EvidenceHover key={eid} item={item} /> : null;
                })}
              </div>
            ))}
            {!claims.length && (
              <p className="muted">Cited claims will appear after drafting.</p>
            )}
          </section>
          <section className="panel">
            <h3>Checks & feedback</h3>
            {state.critique ? (
              <p>
                {state.critique.passed
                  ? "Critic: passed"
                  : state.critique.issues.join("; ")}
              </p>
            ) : (
              <p className="muted">Critic review pending.</p>
            )}
            {state.compliance && (
              <>
                <Badge
                  value={
                    state.compliance.allowed ? "policy cleared" : "blocked"
                  }
                />
                <p>{state.compliance.violations.join("; ")}</p>
                <small>{state.compliance.policy_version}</small>
              </>
            )}
            {state.price && <p>{state.price.rationale}</p>}
            {state.decision?.action === "skip" && (
              <p>{state.decision.reasons.join("; ")}</p>
            )}
          </section>
        </aside>
      </div>
    </>
  );
}

function PipelinePage() {
  const { data, error } = useData<Data>("/pipeline");
  const columns = [
    "drafted",
    "submitted",
    "viewed",
    "replied",
    "interview",
    "hired",
    "lost",
  ];
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">FROM POSSIBILITY TO PROJECT</span>
          <h1>
            Your work in motion<span>.</span>
          </h1>
          <p>
            Keep the next step in view, from first draft to the right client.
          </p>
        </div>
      </div>
      <ErrorBox error={error} />
      <div className="kanban">
        {columns.map((col) => {
          const items = (data?.proposals || []).filter(
            (p: Data) => p.status === col,
          );
          return (
            <section className="kanban-column" key={col}>
              <h3>
                <span className={"column-dot " + col} />
                {col}
                <span>{items.length}</span>
              </h3>
              {items.map((p: Data) => (
                <article key={p.id}>
                  <strong>{p.job_id}</strong>
                  <p>${p.amount}/hr</p>
                  <small>{p.connects_spent} Connects spent</small>
                </article>
              ))}
              {col === "drafted" &&
                (data?.runs || [])
                  .filter(
                    (r: Run) =>
                      r.status === "awaiting_approval" && r.kind === "bid",
                  )
                  .map((r: Run) => (
                    <Link
                      className="kanban-draft"
                      key={r.id}
                      to={"/studio/" + r.id}
                    >
                      <FileCheck size={18} />
                      {String((r.state as Data).job?.title || "Draft proposal")}
                      <span>Needs your review</span>
                    </Link>
                  ))}
              {!items.length && (
                <div className="kanban-empty">No {col} proposals</div>
              )}
            </section>
          );
        })}
      </div>
      <p className="muted">
        Local mock replies appear in Messages. Official marketplace events
        require the instructor API.
      </p>
    </>
  );
}

function MessagesPage() {
  const { data, error, reload } = useData<Data>("/messages");
  const { data: runs } = useData<{ runs: Run[] }>("/runs");
  const [active, setActive] = useState(""),
    [errorLocal, setError] = useState("");
  const navigate = useNavigate();
  const threads = [
    ...new Set<string>(
      (data?.messages || []).map((m: Data) => m.conversation_id),
    ),
  ];
  const selected = active || threads[0];
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">KEEP THE CONVERSATION MOVING</span>
          <h1>
            A thoughtful next reply<span>.</span>
          </h1>
          <p>Read the context. Review a response. Send when you’re ready.</p>
        </div>
        <button className="secondary" onClick={reload}>
          Refresh messages
        </button>
      </div>
      <ErrorBox error={error || errorLocal} />
      {threads.length ? (
        <div className="messages-layout">
          <aside className="thread-list">
            {threads.map((t) => (
              <button
                className={selected === t ? "active" : ""}
                onClick={() => setActive(t)}
                key={t}
              >
                <MessageSquare size={18} />
                <span>
                  {t}
                  <small>Synthetic client thread</small>
                </span>
              </button>
            ))}
          </aside>
          <section className="panel">
            <h2>{selected}</h2>
            {(data?.messages || [])
              .filter((m: Data) => m.conversation_id === selected)
              .sort((a: Data, b: Data) => a.created - b.created)
              .map((m: Data) => (
                <div className={"message " + m.sender} key={m.id}>
                  <small>{m.sender === "client" ? "Client" : "You"}</small>
                  <p>{m.text}</p>
                </div>
              ))}
            <button
              className="primary"
              onClick={async () => {
                try {
                  const r = await api<Run>("/conversations", "POST", {
                    conversation_id: selected,
                  });
                  navigate("/studio/" + r.id);
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              <Sparkles size={16} />
              Draft a reply
            </button>
            <p className="muted">
              Interview slots are tentative mock availability in UTC.
            </p>
          </section>
        </div>
      ) : (
        <Empty
          title="Conversations start here"
          body="Approve a local proposal to receive a labelled synthetic client reply."
        />
      )}
    </>
  );
}

function RunsPage() {
  const { data, error } = useData<{ runs: Run[] }>("/runs");
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">A CLEAR LINE OF SIGHT</span>
          <h1>
            Every decision, in view<span>.</span>
          </h1>
          <p>
            Follow the agents, inspect their evidence, and pick up where you
            left off.
          </p>
        </div>
      </div>
      <ErrorBox error={error} />
      <div className="panel">
        {data?.runs.length ? (
          data.runs.map((r) => (
            <Link className="run-row" to={"/runs/" + r.id} key={r.id}>
              <span className="run-icon">
                <Activity size={19} />
              </span>
              <div>
                <strong>
                  {String(
                    (r.state as Data).job?.title ||
                      r.job_id ||
                      r.conversation_id,
                  )}
                </strong>
                <small>
                  {r.kind} · {r.id.slice(0, 12)}
                </small>
              </div>
              <Badge value={r.status} />
              <ArrowUpRight size={18} />
            </Link>
          ))
        ) : (
          <Empty
            title="Your first run is ahead"
            body="Choose an opportunity in your inbox and select Analyze & draft."
          />
        )}
      </div>
    </>
  );
}
function RunPage() {
  const { id } = useParams();
  const { run, error } = useRun(id);
  const { data: trace } = useData<Data>("/traces/" + id);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">AGENT RUN</span>
          <h1>
            The reasoning behind the draft<span>.</span>
          </h1>
          <p>Trace {id}</p>
        </div>
        <Link className="primary" to={"/studio/" + id}>
          Open proposal studio <ArrowRight size={16} />
        </Link>
      </div>
      <ErrorBox error={error || run?.error || ""} />
      <div className="panel">
        <h2>Execution timeline</h2>
        <RunTimeline events={(run?.state as Data)?.events || []} />
      </div>
      <details className="panel">
        <summary>Inspect masked tool audit</summary>
        <pre>{JSON.stringify(trace, null, 2)}</pre>
      </details>
      {run && ["needs_attention", "queued_retry"].includes(run.status) && (
        <button
          className="primary"
          onClick={() => api("/runs/" + id + "/retry", "POST")}
        >
          Retry saved run
        </button>
      )}
    </>
  );
}
function AnalyticsPage() {
  const { data, error } = useData<Data>("/analytics");
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">LEARN FROM THE WORK</span>
          <h1>
            A clearer picture of your pipeline<span>.</span>
          </h1>
          <p>Measured activity, with the limits kept visible.</p>
        </div>
      </div>
      <ErrorBox error={error} />
      <div className="stats-grid">
        <Stat
          label="Jobs analyzed"
          value={String(data?.jobs_analyzed ?? "—")}
          sub="Completed fit and risk decisions"
          icon={<Search />}
        />
        <Stat
          label="Proposals submitted"
          value={String(data?.proposals_submitted ?? "—")}
          sub="After your explicit approval"
          icon={<FileCheck />}
        />
        <Stat
          label="Connects spent"
          value={String(data?.connects?.spent ?? "—")}
          sub={`${data?.connects?.balance ?? "—"} remaining`}
          icon={<Briefcase />}
        />
      </div>
      <div className="detail-grid">
        <section className="panel">
          <h2>Speed & cost</h2>
          <dl className="metrics">
            <div>
              <dt>p95 run latency</dt>
              <dd>
                {data?.p95_seconds
                  ? Number(data.p95_seconds).toFixed(2) + "s"
                  : "No completed runs"}
              </dd>
            </div>
            <div>
              <dt>Paid API spend</dt>
              <dd>$0 · local open models</dd>
            </div>
            <div>
              <dt>Official reply / hire rate</dt>
              <dd>Awaiting official GigSim</dd>
            </div>
          </dl>
          <p className="muted">
            Hardware and electricity costs are excluded from paid API spend.
          </p>
        </section>
        <section className="panel">
          <h2>Independent local client simulation</h2>
          <p className="muted">
            Synthetic LLM judgments, separate from official GigSim and real
            client outcomes.
          </p>
          <dl className="metrics">
            <div>
              <dt>Evaluated proposals</dt>
              <dd>{data?.independent_local_simulator?.evaluated ?? 0}</dd>
            </div>
            <div>
              <dt>Simulated reply rate</dt>
              <dd>
                {data?.independent_local_simulator?.reply_rate == null
                  ? "Not measured"
                  : (data.independent_local_simulator.reply_rate * 100).toFixed(
                      1,
                    ) + "%"}
              </dd>
            </div>
            <div>
              <dt>Simulated hire rate</dt>
              <dd>
                {data?.independent_local_simulator?.hire_rate == null
                  ? "Not measured"
                  : (data.independent_local_simulator.hire_rate * 100).toFixed(
                      1,
                    ) + "%"}
              </dd>
            </div>
          </dl>
          <h3>Keep outcomes honest</h3>
          <ShieldCheck className="large-icon" />
          <p>{data?.note}</p>
          <p>
            Human ratings, official simulator outcomes, and hidden test results
            are reported only when measured.
          </p>
        </section>
      </div>
    </>
  );
}

function SettingsPage({ onboarding = false }: { onboarding?: boolean }) {
  const { data: connections } = useData<Data>("/connections");
  const { data, error, reload } = useData<Profile>("/profile"),
    { data: memory, reload: reloadMemory } = useData<Data>("/memory");
  const [form, setForm] = useState<Profile | null>(null),
    [notice, setNotice] = useState(""),
    [errorLocal, setError] = useState("");
  const [uploadSkills, setUploadSkills] = useState("");
  const [uploadKind, setUploadKind] = useState("case_study");
  const navigate = useNavigate();
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            {onboarding ? "MAKE IT YOURS" : "YOUR WORKSPACE, YOUR RULES"}
          </span>
          <h1>
            {onboarding
              ? "Start with the way you work."
              : "A copilot that follows your lead."}
          </h1>
          <p>Set your portfolio, rate floor, and the boundaries that matter.</p>
        </div>
      </div>
      <ErrorBox error={error || errorLocal} />
      {notice && (
        <div role="status" className="success-box">
          {notice}
        </div>
      )}
      {form && (
        <div className="settings-grid">
          <form
            className="panel settings-form"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api("/profile", "PUT", form);
                setNotice("Preferences saved.");
                reload();
                if (onboarding) navigate("/inbox");
              } catch (err) {
                setError(String(err));
              }
            }}
          >
            <h2>Your profile & preferences</h2>
            <label>
              Portfolio persona
              <select
                value={form.persona}
                onChange={(e) =>
                  setForm({
                    ...form,
                    persona: e.target.value as Profile["persona"],
                    agency_mode:
                      e.target.value === "own" ? false : form.agency_mode,
                  })
                }
              >
                <option value="ml">AI / ML engineer · synthetic</option>
                <option value="web">Full-stack developer · synthetic</option>
                <option value="data">Data analyst · synthetic</option>
              </select>
            </label>
            <div className="form-row">
              <label>
                Minimum hourly rate (USD)
                <input
                  type="number"
                  min={1}
                  value={form.floor_rate}
                  onChange={(e) =>
                    setForm({ ...form, floor_rate: +e.target.value })
                  }
                />
              </label>
              <label>
                Weekly Connects budget
                <input
                  type="number"
                  min={0}
                  value={form.weekly_connects}
                  onChange={(e) =>
                    setForm({ ...form, weekly_connects: +e.target.value })
                  }
                />
              </label>
            </div>
            <label>
              Saved search
              <input
                value={form.saved_search}
                onChange={(e) =>
                  setForm({ ...form, saved_search: e.target.value })
                }
                placeholder="Python, analytics, web applications…"
              />
            </label>
            <label>
              Autonomy
              <select
                value={form.autonomy}
                onChange={(e) =>
                  setForm({
                    ...form,
                    autonomy: e.target.value as Profile["autonomy"],
                  })
                }
              >
                <option value="suggest">
                  Suggest only · always approve sends
                </option>
                <option value="auto_skip">
                  Auto-skip low fit · always approve sends
                </option>
              </select>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                disabled={form.persona === "own"}
                checked={form.agency_mode || false}
                onChange={(e) =>
                  setForm({ ...form, agency_mode: e.target.checked })
                }
              />
              Agency mode ? route to the strongest portfolio member
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={form.scheduled_scouting}
                onChange={(e) =>
                  setForm({ ...form, scheduled_scouting: e.target.checked })
                }
              />
              Scout every four hours (Redis worker required)
            </label>
            <button className="primary" type="submit">
              {onboarding ? "Save & open inbox" : "Save preferences"}
              <ArrowRight size={16} />
            </button>
          </form>
          <div>
            <section className="panel">
              <h2>Connected accounts</h2>
              <div className="connection-row">
                <span className="connection-icon">
                  <Briefcase size={20} />
                </span>
                <div>
                  <strong>Local marketplace</strong>
                  <small>Synthetic simulator · active</small>
                </div>
                <CheckCircle2 size={19} />
              </div>
              <div className="connection-row">
                <span className="connection-icon">U</span>
                <div>
                  <strong>Upwork</strong>
                  <small>
                    {connections?.upwork_authorization_stored
                      ? "Authorization stored; verify live tool mapping"
                      : "OAuth not connected"}
                  </small>
                </div>
                <Badge value="not connected" />
              </div>
              <button
                type="button"
                className="secondary"
                onClick={async () => {
                  try {
                    const flow = await api<Data>("/oauth/upwork/start", "POST");
                    if (flow.authorization_url) {
                      window.location.assign(flow.authorization_url);
                    } else {
                      setError(
                        "Upwork did not provide an authorization URL. Check the configured official endpoint and server logs.",
                      );
                    }
                  } catch (err) {
                    setError(String(err));
                  }
                }}
              >
                Connect Upwork with OAuth
              </button>
              <p className="muted">
                Official GigSim service details and real account authorization
                have not been supplied. Local mode is ready to use.
              </p>
            </section>
            <section className="panel">
              <h2>Add portfolio evidence</h2>
              <p className="muted">
                PDF CVs, Markdown, text, or code. Up to 3 MB. Never upload
                another client’s confidential material.
              </p>
              <label>
                Evidence type
                <select
                  value={uploadKind}
                  onChange={(e) => setUploadKind(e.target.value)}
                >
                  <option value="case_study">Case study</option>
                  <option value="cv">CV</option>
                  <option value="readme">Repository README</option>
                  <option value="code">Code</option>
                  <option value="review">Client review</option>
                  <option value="proposal">Past proposal</option>
                </select>
              </label>
              <label>
                Evidence skills
                <input
                  value={uploadSkills}
                  onChange={(e) => setUploadSkills(e.target.value)}
                  placeholder="Python, FastAPI, React"
                />
              </label>
              <p className="muted">
                Save your selected profile before uploading. Own portfolio mode
                excludes all fictional persona evidence.
              </p>
              <label className="upload-control">
                Choose portfolio file
                <input
                  aria-label="Upload portfolio"
                  type="file"
                  accept=".pdf,.md,.txt,.py,.js,.ts,.json,.sql"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    const fd = new FormData();
                    fd.append("file", file);
                    fd.append("skills", uploadSkills);
                    fd.append("kind", uploadKind);
                    try {
                      await api("/portfolio/upload", "POST", fd);
                      setNotice(
                        "Evidence uploaded. Incremental index refreshed.",
                      );
                    } catch (err) {
                      setError(String(err));
                    }
                  }}
                />
              </label>
            </section>
          </div>
        </div>
      )}
      <section className="panel">
        <h2>What your copilot remembers</h2>
        <p className="muted">
          Style needs three repeated edits. Category outcomes need five
          observations. Raw tool results never become memory.
        </p>
        {["style", "outcome"].map((kind) => (
          <div key={kind}>
            <h3>
              {kind === "style" ? "Style preferences" : "Outcome patterns"}
            </h3>
            {(memory?.[kind] || []).length ? (
              (memory?.[kind] || []).map((m: Data) => (
                <div className="memory-row" key={m.id}>
                  <span>
                    {m.rule || `${m.category}: ${m.observations} observations`}
                  </span>
                  <button
                    className="text-button danger"
                    onClick={async () => {
                      await api("/memory/" + kind + "/" + m.id, "DELETE");
                      reloadMemory();
                    }}
                  >
                    Delete memory
                  </button>
                </div>
              ))
            ) : (
              <p className="muted">No promoted {kind} memory yet.</p>
            )}
          </div>
        ))}
      </section>
    </>
  );
}
