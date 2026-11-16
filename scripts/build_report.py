"""Nine-page R&D review. Numbers are read from executed results, never hand-entered."""

import json
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from core.settings import ROOT, config

OUT = ROOT / "output/pdf"
OUT.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("ArialBold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="ArialBold")
GREEN = colors.HexColor("#244c38")
MUTED = colors.HexColor("#6c7f6b")
PALE = colors.HexColor("#edf3e7")
LINE = colors.HexColor("#dce5d5")
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="BodyReview",
        fontName="Arial",
        fontSize=9.4,
        leading=14,
        textColor=colors.HexColor("#354c3c"),
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(name="SmallReview", fontName="Arial", fontSize=7.6, leading=11, textColor=MUTED, spaceAfter=8)
)
styles.add(
    ParagraphStyle(name="TitleReview", fontName="ArialBold", fontSize=30, leading=35, textColor=GREEN, spaceAfter=12)
)
styles.add(
    ParagraphStyle(name="HeadingReview", fontName="ArialBold", fontSize=17, leading=23, textColor=GREEN, spaceAfter=14)
)
styles.add(
    ParagraphStyle(
        name="SubReview", fontName="ArialBold", fontSize=11, leading=16, textColor=GREEN, spaceBefore=8, spaceAfter=8
    )
)
styles.add(ParagraphStyle(name="TableReview", fontName="Arial", fontSize=7.7, leading=11, textColor=GREEN))
story = []


def data(name):
    p = ROOT / "evals/results" / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def p(text, style="BodyReview"):
    story.append(Paragraph(text, styles[style]))


def heading(number, title):
    p(f"{number:02d} / ENGINEERING DESIGN REVIEW", "SmallReview")
    p(title, "HeadingReview")


def table(rows, widths=None):
    formatted = [
        [Paragraph(("<b>" + escape(str(v)) + "</b>") if i == 0 else escape(str(v)), styles["TableReview"]) for v in row]
        for i, row in enumerate(rows)
    ]
    t = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PALE),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 12))


def source(text):
    p("Evidence: " + escape(text), "SmallReview")


def image(path, width, maxheight=500):
    iw, ih = ImageReader(str(path)).getSize()
    h = width * ih / iw
    if h > maxheight:
        width *= maxheight / h
        h = maxheight
    return Image(str(path), width=width, height=h)


def nextpage():
    story.append(PageBreak())


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(55, 39, 540, 39)
    canvas.setFont("Arial", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(55, 25, "GIGBID  /  AI-4016  /  LOCAL DEVELOPMENT EVIDENCE")
    canvas.drawRightString(540, 25, str(doc.page))
    canvas.restoreState()


def build():
    rag = data("retrieval")
    models = data("models")
    tools = data("tools")
    arch = data("architectures")
    real = data("real_data")
    agency = data("agency")
    safety = data("safety")
    attacks = data("attacks")
    isolation = data("secret_isolation")
    failures = data("failure_analysis")
    stamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%d %B %Y, %H:%M PKT")
    p("GIGBID / AI-4016 / R&D REPORT", "SmallReview")
    p("A freelancer copilot<br/>that shows its evidence.", "TitleReview")
    p("Engineering design review | " + stamp, "SmallReview")
    p(
        "The implemented local product discovers fictional freelance jobs, scores risk and fit, drafts from portfolio evidence, and pauses for explicit approval. It runs on local open models using the available RTX 3070. The central boundary is a server-validated, exact-content approval grant, backed by durable checkpoints and atomic idempotency receipts."
    )
    table(
        [
            ["Implemented and exercised", "Evidence boundary"],
            ["React + FastAPI + SDK MCP + LangGraph", "Local synthetic marketplace; real historical pricing"],
            [
                "Six RAG variants; two writer profiles; three orchestration systems",
                "No official GigSim or hidden outcomes available",
            ],
        ],
        [245, 230],
    )
    p(
        "The supplied example ZIP lacked the official simulator, persona assets, labelled dev set and November 2 policy update. This report distinguishes our separately authored substitutes from instructor assets. Public deployment, account authorization and independent human quality judgments remain incomplete. The original assignment deadline predates this work; timestamps are not backdated."
    )
    if (ROOT / "docs/images/inbox-desktop.png").exists():
        story.append(image(ROOT / "docs/images/inbox-desktop.png", 475, 285))
    source("docs/STATUS.md; docs/REQUIREMENTS.md; evals/results/*.json; source assignment supplied by user")
    nextpage()

    heading(2, "Architecture: decisions, traces and memory")
    diagram = Table(
        [
            [
                image(ROOT / "docs/images/bid_graph.png", 245, 405),
                image(ROOT / "docs/images/conversation_graph.png", 180, 340),
            ]
        ],
        colWidths=[265, 210],
    )
    diagram.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(diagram)
    story.append(Spacer(1, 10))
    p(
        "The handwritten bid graph uses Send for Analyst, Risk and Fit, then joins before deciding. Writer, verifier and Critic form a bounded revision loop. Compliance may block; a dry-run preview precedes interrupt(). Edits re-enter checks and require fresh approval. Dispatch re-reads evidence so deletion can invalidate an old draft."
    )
    p(
        "Per-thread state holds this job or conversation. Append-only masked tool/event records form the execution trace. Two durable LangGraph BaseStore namespaces hold promoted style and outcomes. Only repeated authenticated edits and sufficient observed outcomes promote memory; raw tool outputs do not. The UI can delete promoted entries."
    )
    p(
        "Agents see role-scoped MCP capabilities. The Marketplace port chooses the local mock, instructor REST adapter or official Upwork MCP adapter. SQLite is tested locally; Compose configures Postgres checkpoints, Redis/Arq, Qdrant and Phoenix. Qdrant queries carry tenant/persona filters; networked deployment performance is not measured."
    )
    source(
        "agent/graphs/*.py; agent/state.py; agent/mcp_client.py; agent/memory/; docs/images/*.mmd; tests/integration/"
    )
    nextpage()

    heading(3, "Data: real pricing, fictional experience")
    table(
        [
            ["2024 Kaggle snapshot", "Measured count"],
            ["Input records", f"{real.get('input_rows', 0):,}"],
            ["Retained records", f"{real.get('output_rows', 0):,}"],
            [
                "Duplicate / invalid records removed",
                f"{real.get('duplicates_removed', 0)} / {real.get('invalid_removed', 0)}",
            ],
            ["Records altered by PII masking", real.get("rows_pii_masked", "unavailable")],
            [
                "Chronological train / holdout",
                f"{real.get('market_statistics', {}).get('train_records', 0):,} / {real.get('market_statistics', {}).get('holdout_records', 0):,}",
            ],
        ],
        [310, 165],
    )
    p(
        "<b>Attribution.</b> asaniczka, Upwork Job Postings Dataset 2024 (50K Records), Kaggle version 1, ODC Attribution License (ODC-By). Source: https://www.kaggle.com/datasets/asaniczka/upwork-job-postings-dataset-2024-50k-records. Raw archive/CSV checksums and retrieved metadata are saved. This project downloads the licensed archive; it does not scrape Upwork."
    )
    p(
        "Cleaning unescapes HTML, normalizes text, deduplicates by source identity/content, rejects short records, masks common contact/account formats and parses noisy skills. Only chronological training records contribute hourly midpoint medians; fixed budgets are kept separate. USD is inferred from dollar notation. These are historical posted budgets, not successful earnings or negotiated prices."
    )
    p(
        "All freelancer CVs, case studies, code outlines, reviews, proposal histories, clients, local jobs and development labels are explicitly synthetic. Historical proposal outcomes are independent draws. No fictional achievement may be presented as the student's real experience. Corpora and dev jobs share an ontology/templates, so high scores are optimistic development checks rather than independent validation."
    )
    p(
        "The other TA sources were reviewed for provenance/license/suitability. Overlapping job feeds and selected successful contracts were unnecessary for this scope. The general fraud dataset had an unknown retrieved license and was excluded. Missing client histories, real Connects costs and outcome labels remain unknown. The fixed local client reply is excluded from marketplace-effectiveness claims."
    )
    source(
        "real_data.json; data_acquisition.json; data/processed/manifest.json; docs/DATA_CARD.md; scripts/prepare_real_data.py"
    )
    nextpage()

    heading(4, "MCP and R&D A: precise tool descriptions")
    p(
        "<b>Hypothesis.</b> Narrow capability names and rewritten descriptions improve tool/argument selection relative to a coarse operation dispatcher. Forty synthetic known-call tasks were run per design using the same local 1.5B model. Errors count as failures. This is JSON tool selection, not a native tool-calling benchmark; actual MCP execution is validated separately."
    )
    table(
        [
            ["Design", "Selection", "Arguments", "Mean tokens"],
            *[
                [v, f"{s['selection_accuracy']:.3f}", f"{s['argument_accuracy']:.3f}", f"{s['mean_tokens']:.1f}"]
                for v, s in tools.get("summary", {}).items()
            ],
        ],
        [140, 110, 110, 115],
    )
    p(
        "Rewritten descriptions improved selection at a larger prompt-token cost. Coarse tools confused the dispatcher operation/parameter structure. The study repeats a small family of tasks and cannot establish robustness to general natural language. The deployed inventory keeps capabilities distinct and constrains each role by an allowlist."
    )
    table(
        [
            ["Server", "Surface and enforcement"],
            ["Portfolio", "Evidence search/get/skills, agency rank, resources and screening prompt; read only"],
            [
                "Marketplace",
                "Job/history/balance/messages reads; preview/draft/submit/message writes; constrained inputs and typed outputs",
            ],
            ["Workspace", "Local mock slots, tentative holds and email drafts; approved mutations only"],
        ],
        [110, 365],
    )
    p(
        "HTTP bearer authentication resolves the tenant. A separate signed grant binds each real write to user-approved action/content. Stable idempotency keys reject content conflicts; proposal, receipt and fictional Connects debit commit together. Timeouts/backoff are bounded. OAuth tokens are encrypted per tenant. Upwork/GitHub integrations remain fail-closed until account authorization and advertised tool mappings are verified."
    )
    source(
        "tools.json; tests/contract/tool_schemas.json; declared_output_schemas.json; docs/TOOLS.md; MCP Inspector captures"
    )
    nextpage()

    heading(5, "R&D B: retrieval chosen by measurement")
    p(
        "<b>Hypothesis.</b> Decomposing requirements and combining exact-term retrieval with dense evidence improves coverage over whole-job dense search. Each variant evaluated the same synthetic dev jobs. Gold is project-level to collapse equivalent case/README/code renderings; empty-gold cases are excluded from recall and assessed in decisions."
    )
    table(
        [
            ["Variant", "Recall@5", "MRR", "nDCG@10", "p95 s"],
            *[
                [v, f"{s['recall_at_5']:.4f}", f"{s['mrr']:.4f}", f"{s['ndcg_at_10']:.4f}", f"{s['p95_seconds']:.4f}"]
                for v, s in rag.get("summary", {}).items()
            ],
        ],
        [85, 100, 85, 105, 100],
    )
    p(
        f"<b>Shipped choice: {rag.get('selected_variant', 'unavailable')}, provisionally.</b> Requirement decomposition won this set. Cross-encoder reranking did not improve it and cost more latency. BM25 and outcome boosts did not establish an advantage over decomposition. Random synthetic outcome labels provide little useful ranking signal. Per-persona/job-type breakdowns and paired component additions are in the source files."
    )
    p(
        "A strict verifier splits claims, resolves citations and accepts exact approved facts or source quotations. Novel experience paraphrases become partly supported/unsupported and are removed before Critic. Forward-looking plans have a deliberately small accepted grammar. This guarantees a narrow extractive boundary, not calibrated semantic entailment; harmless statements can be over-rejected."
    )
    p(
        "The extractive retrieval evaluation starts with safe facts and therefore has no unsupported-claim improvement to demonstrate. Separate deliberate-fabrication probes and raw model plans exercise removal. No LLM judge score is reported before independent human calibration. No real or official simulated reply-rate gain can be inferred from higher recall."
    )
    source("retrieval.json; ablation.json; safety.json; models.json; evals/HYPOTHESES.md; rag/variants/; rag/verify.py")
    nextpage()

    heading(6, "Models and R&D C: what orchestration buys")
    table(
        [
            ["Writer profile", "Valid JSON", "Rejected / plan", "p95 s", "Tokens/s"],
            *[
                [
                    v,
                    f"{s['valid_plan_rate']:.3f}",
                    f"{s['raw_unsupported_per_plan']:.3f}",
                    f"{s['p95_seconds']:.2f}",
                    f"{s['mean_generation_tokens_per_second']:.1f}",
                ]
                for v, s in models.get("summary", {}).items()
            ],
        ],
        [120, 85, 105, 75, 90],
    )
    p(
        "Both post-fix profiles produced structured plans; final extractive drafts retained no verifier-unsupported statements. Rejected raw-plan sentences are a conservative grammar metric, not a calibrated hallucination rate. Explicit schemas repaired the smallest model's initial malformed outputs. The 7B writer remains a provisional quality choice; no independent persuasive-quality superiority is claimed. Local paid API charges are zero, excluding hardware/electricity."
    )
    table(
        [
            ["Architecture", "Bid accuracy", "Failure rate", "Unsupported", "p95 s"],
            *[
                [
                    v,
                    f"{s['bid_accuracy']:.3f}",
                    f"{s['execution_failure_rate']:.3f}",
                    (
                        "N/A"
                        if s["unsupported_claims_per_completed_job"] is None
                        else f"{s['unsupported_claims_per_completed_job']:.3f}"
                    ),
                    f"{s['p95_seconds']:.2f}",
                ]
                for v, s in arch.get("summary", {}).items()
            ],
        ],
        [140, 85, 85, 85, 80],
    )
    counts = Counter(r.get("status", "error") for r in arch.get("rows", []) if r["architecture"] == "handwritten")
    p(
        "The orchestration comparison uses the same fixed jobs and a uniform 1.5B model to reduce model-routing confounds. The handwritten system adds deterministic risk/fit rules that overlap synthetic gold; its decision accuracy is not proof of generally superior multi-agent reasoning. Baseline errors count as incorrect, and unsupported counts are per completed job."
    )
    p(
        "Handwritten terminal states: "
        + escape(str(dict(counts)))
        + ". A correct bid decision may still end in needs attention when the Critic cannot clear a draft. No such draft is sent. The initial supervisor dropped structured output through its outer state schema; the corrected supervisor reran the same jobs and replaced only that row set. Original failures remain available."
    )
    source(
        "models.json; models_before_schema_fix.json; architectures.json; architecture_supervisor_corrected.json; original schema-failure results"
    )
    nextpage()

    heading(7, "Safety, policy change and agency extension")
    table(
        [
            ["Check", "Observed result"],
            [
                "Small pattern-detector attack suite",
                f"{safety.get('detector_recall_on_attack_suite', 0):.1%} flagged; not model ASR",
            ],
            [
                "Canary: control / prompt-only / isolated",
                f"{attacks.get('control_asr', 0):.1%} / {attacks.get('defended_asr', 0):.1%} / {isolation.get('isolated_context_asr', 0):.1%}",
            ],
            [
                "Fabrication probes before / after removal",
                f"{safety.get('unsupported_before', 0)} / {safety.get('unsupported_after', 0)} verifier-rejected claims",
            ],
            [
                "Agency / ML-only evidence coverage",
                f"{agency.get('mean_agency_coverage', 0):.3f} / {agency.get('mean_ml_only_coverage', 0):.3f}",
            ],
        ],
        [285, 190],
    )
    p(
        "Prompt-only protection did not improve disclosure. A follow-up kept unnecessary private state outside the model input; that is context minimization, not improved model obedience. The canary study uses a synthetic secret and local model, with an intentionally weak control prompt and defended quoted-data prompt. Success means literal/base64 disclosure on a small fixed suite. It is not a complete jailbreak evaluation or the instructor's planted set. Some indirect text instructions miss pattern rules. Approval grants remain the hard write boundary even when detection misses an attack."
    )
    p(
        "Emails, common phone/account formats and credential-like keys are masked in audit exports; pattern masking can miss obfuscations and names. OAuth tokens are encrypted. Queries and checkpoints are tenant scoped. Local vector tests verify that identical evidence IDs cannot retrieve another tenant's payload. User edits are rechecked, and dispatch re-reads evidence."
    )
    p(
        "The official November 2 update was absent. A separate local rehearsal adds a fictional Connects surcharge through policy configuration and verifies the resulting quote. It is not labelled as the official change. Automated validation duration is recorded; engineering edit time was not measured. No provided GigSim code is modified."
    )
    p(
        "X1 agency routing compares requirement coverage for ML, web and data members without using expected-persona/gold labels. Settings enables the combined feed; Portfolio MCP rank_team chooses the member, and the studio retains the member identity. The extension test checks permission gating and source revalidation. Shared synthetic skill templates make its coverage result optimistic."
    )
    source(
        "safety.json; attacks.json; secret_isolation.json; policy_rehearsal.json; agency.json; tests/integration/test_vector_scope.py; test_agency.py"
    )
    nextpage()

    heading(8, "Failure analysis: actual dev executions")
    selected = []
    seen = set()
    for f in failures.get("failures", []):
        if f["job_id"] in seen:
            continue
        seen.add(f["job_id"])
        selected.append(f)
        if len(selected) == 10:
            break
    table(
        [
            ["Dev job", "System", "Failure class"],
            *[[f["job_id"], f["architecture"], f["category"].replace("_", " ")] for f in selected],
        ],
        [150, 145, 180],
    )
    p(
        "These identifiers come from actual failed synthetic dev executions, not invented examples. Per-job output/error, predicted/gold decision, conservative rejected-claim count and source row are retained in failure_analysis.json and architectures.json. Errors caused by structured-output truncation are still counted after the supervisor integration fix."
    )
    p(
        "<b>Wrong decisions.</b> A generic agent sometimes bids despite low fit or planted-risk instructions. Deterministic risk and requirement coverage improve the local decision check, but the shared label rules exaggerate generalization. Independently labelled jobs are needed to test the fix honestly."
    )
    p(
        "<b>Unverified wording.</b> Free-form proposals introduce experience language or assertions that the strict verifier cannot establish. Exact citations and quotations remove those claims at the cost of natural paraphrasing. A zero remaining count does not prove that every rejected sentence was false."
    )
    p(
        "<b>Tool/schema and loop failures.</b> The supervisor initially lost a structured state field. Explicit outer schema corrected that integration bug; model-length/format failures remained. An over-demanding Critic previously blocked a safe future plan, so its prompt now separates blocking factual/safety issues from optional improvements. Revisions remain bounded and unresolved drafts stay unsent."
    )
    source(
        "failure_analysis.json; architectures.json; architectures_before_supervisor_schema_fix.json; docs/AI_USAGE.md; saved local Critic-loop trace"
    )
    nextpage()

    heading(9, "Validation, budgets and delivery boundaries")
    budget = config()["budgets"]
    table(
        [
            ["Declared budget", "Configuration"],
            ["p95 job / proposal latency", f"{budget['p95_job_seconds']} s / {budget['p95_proposal_seconds']} s"],
            ["Token / graph-step cap", f"{budget['max_tokens_per_job']} tokens / {budget['max_graph_steps']} steps"],
            ["Maximum additional revisions", budget["max_revisions"]],
            ["Paid API cost target", f"USD {budget['api_usd_per_proposal']} per proposal"],
        ],
        [290, 185],
    )
    p(
        "Retrieval-only and writer-only timing tables do not measure the full product. The uniform orchestration run includes MCP/model work but has a small synthetic job set and no hosted-service latency. Cold imports, model loading and concurrent GPU use can dominate. Hidden-test budget results are unavailable; no pass is claimed for them. Token limits are checked between graph stages, so one in-flight call can exceed a remaining allowance."
    )
    p(
        "Executed checks include Python unit/integration/contract tests, durable approval/replay, unauthenticated-write rejection, tenant isolation, memory promotion, vector scoping, six browser flows, frontend build and Compose syntax validation. Browser tests explicitly use deterministic model doubles; the recorded local demo separately exercises real open models. Actual counts and exit status are saved in delivery.json and the test reports."
    )
    p(
        "The local application is usable at port 8000, with private reviewer credentials excluded from Git. Docker Compose and a Render reference Blueprint are prepared. The Docker engine was unavailable, so container startup/Postgres/Redis/Phoenix operation is not verified. Render requires persistent storage and a reachable open-model endpoint; free ephemeral/sleeping services do not establish reliable reviewer availability."
    )
    p(
        "<b>Still required for a complete submission:</b> official GigSim assets/contract and outcomes; actual Upwork/GitHub account verification; independent human calibration and blind ratings; official policy adaptation; and public deployment with reviewer access. The write-up, video, MCP installation guide and sanitized JSON traces are published on GitHub (docs/PUBLIC_LINKS.md); hosted MCP/Phoenix endpoints are not deployed. Human review sheets are intentionally blank. The student must review and explain the code in the viva."
    )
    p(
        "AI assistance and corrected mistakes are disclosed in docs/AI_USAGE.md. Original code is MIT licensed; datasets/models retain their own terms. The submission checklist keeps unexecuted work visible. No hidden test data, real client messages or account tokens enter the public source."
    )
    source(
        "delivery.json; python_tests.xml; Playwright report; agent/config.yaml; docs/STATUS.md; docs/SUBMISSION_CHECKLIST.md; docs/AI_USAGE.md"
    )
    nextpage()
    heading(10, "Final product check and local client study")
    product = data("product_open_profile").get("summary", {})
    p(
        "The final open profile uses a 1.5B Analyst and 7B Writer/Critic. On 30 fixed synthetic development jobs, "
        + escape(str(product.get("terminal_states", {})))
        + " were observed. All 27 eligible drafts reached human approval; none were submitted in this smoke experiment. "
        "This is a separate product check, not a controlled rerun of the uniform-model architecture comparison."
    )
    clients = data("local_client_outcomes").get("summary", {})
    table(
        [
            ["Local client strategy", "Jobs", "Reply or later", "Hired", "Errors"],
            *[
                [name, s["n"], f"{s['reply_or_later_rate']:.1%}", f"{s['hire_rate']:.1%}", f"{s['error_rate']:.1%}"]
                for name, s in clients.items()
            ],
        ],
        [155, 55, 95, 80, 90],
    )
    p(
        "These independently authored synthetic clients use hidden preferences and an open model, not official GigSim. "
        "Both strategies use the same job prices. Evidence-grounded proposals received more replies, but did not improve hires. "
        "The judge shares the writer model family and is not human calibrated. One generic judgment credited experience absent "
        "from its proposal, illustrating evaluator bias. These exploratory rates must not be reported as real marketplace performance."
    )
    p(
        "The running local marketplace now queues durable synthetic client evaluations after approved sends, with bounded retries. "
        "Tests and the recorded demo use explicit fixture clients. Live Upwork calls are restricted to configured draft-only tools; "
        "actual platform confirmation remains required. Account authorization has not been exercised."
    )
    p(
        "Own-portfolio mode starts without fictional experience. Users can upload their own cases or proposals with skill metadata; "
        "repeat uploads have stable IDs. It cannot be combined with the fictional agency. Final tests also cover crash-after-commit "
        "replay, removed evidence at dispatch, and live-feed adapter routing."
    )
    source("product_open_profile.json; local_client_outcomes.json; python-tests.xml; docs/FINAL_VALIDATION.md")
    doc = SimpleDocTemplate(
        str(OUT / "GigBid_RnD_Report.pdf"),
        pagesize=(595, 842),
        rightMargin=55,
        leftMargin=55,
        topMargin=47,
        bottomMargin=52,
        title="GigBid R&D Engineering Review",
        author="GigBid project; AI assistance disclosed",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print("Created " + str(OUT / "GigBid_RnD_Report.pdf"))


if __name__ == "__main__":
    build()
