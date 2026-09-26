# AutoClean AI+: Phase 1 — Research & Requirements Document

**Project:** AutoClean AI+: A Multi-Agent Explainable Decision Support System for Multi-Objective Data Cleaning Strategy Optimization
**Research Foundation:** Hu, T., Wang, J., Pu, W., Li, J., Gu, R., Bi, X., Yin, H., & Wang, Y.-P. (2026). *A Multi-Objective Optimization Framework for Data Cleaning Using Large Language Models.* Big Data Mining and Analytics, 9(3), 672–686.
**Phase:** 1 of 12 — Research & Requirements
**Status:** Draft for approval

---

## How to Read This Document

Every section below follows the same structure required by the project specification: **Theory → Design Decisions → Alternatives Considered → Justification**. Throughout, content is explicitly tagged as either:

- 🟦 **[PAPER]** — a feature, formula, or finding taken directly from the IEEE paper, or
- 🟩 **[ORIGINAL]** — a contribution, feature, or design decision introduced by AutoClean AI+ that is *not* in the paper.

This tagging is carried through every subsequent phase so that, at the end of the project, it is possible to produce a clean traceability table for academic evaluation (e.g., a viva/defense panel asking "which parts of this are yours?").

---

## 1. Problem Statement

### Theory
Data cleaning — resolving missing values, duplicates, outliers, and inconsistent formatting — is a prerequisite for trustworthy analytics and machine learning. It is also one of the most labor-intensive stages of the data pipeline. The rise of Large Language Models (LLMs) has made it possible to *automate* many cleaning decisions that previously required a human data engineer (e.g., deciding whether "NY" and "New York" refer to the same entity), but LLM inference is computationally expensive, and applying an LLM uniformly to an entire dataset is often financially or operationally infeasible at scale 🟦[PAPER].

A second, distinct problem — one the source paper does not address — is that even when an optimal cleaning *method* has been selected, the strategy is typically applied **automatically and opaquely**. A practitioner is rarely told *why* a particular cleaning strategy was chosen, *what trade-offs* it implies (e.g., rows dropped, information lost, fairness impact across demographic subgroups, or downstream model accuracy), or given a chance to **approve or reject** the strategy before it irreversibly modifies their data 🟩[ORIGINAL].

### Design Decisions
AutoClean AI+ is framed as **two nested problems**:
1. *How do we choose a cost-effective, high-quality data cleaning strategy?* (the paper's problem)
2. *How do we make that choice transparent, auditable, and subject to human control before it is executed?* (AutoClean AI+'s problem)

### Alternatives Considered
- **Fully autonomous cleaning** (no human checkpoint): rejected — unacceptable risk of silent, irreversible data loss in a decision-support context.
- **Fully manual cleaning with AI suggestions only** (no optimization engine): rejected — abandons the paper's core research contribution and reduces the system to a chatbot wrapper.
- **Hybrid: optimization-driven strategy generation + mandatory human-in-the-loop approval + explainability** (chosen): retains the paper's quantitative rigor while directly addressing its stated limitation around trust and interpretability.

### Justification
The paper's own future-work statement explicitly calls for "deeper integrations with explainable AI and human-in-the-loop approaches to enhance trust and interpretability in data cleaning pipelines" 🟦[PAPER]. AutoClean AI+ is therefore not an arbitrary product idea — it is a direct, citable extension of an identified gap in the source research.

---

## 2. Research Motivation

### Theory
Organizations increasingly rely on automated or semi-automated data cleaning because manual cleaning does not scale with data volume. However, "automated" is often conflated with "unaccountable." In regulated or high-stakes domains (finance, healthcare, hiring), a cleaning pipeline that silently changes label distributions or removes minority-group records can introduce **fairness and validity risks** that are invisible until a downstream model fails or a compliance audit occurs.

### Design Decisions
The motivation for AutoClean AI+ is to demonstrate, at final-year-project scale, that a **multi-objective optimization core** (quantitative, deterministic, reproducible) can be combined with a **thin agentic/LLM layer** (qualitative, explanatory, human-facing) without letting the LLM contaminate the deterministic guarantees of the optimization — i.e., the LLM explains decisions, it does not make them numerically.

### Alternatives Considered
- **LLM-driven end-to-end cleaning** (LLM decides *and* executes cleaning logic): rejected — this is exactly the high-cost, low-reproducibility pattern the source paper is trying to move away from, and it violates the "LLM never performs deterministic calculations" constraint in this project's own operating rules.
- **Pure statistical/AutoML cleaning tool with no narrative layer**: rejected — provides no explainability, which is the primary academic differentiator of this project.

### Justification
This motivation directly targets the gap between two extremes in the current tooling landscape (see Literature Review, §4): black-box AutoML cleaning tools (e.g., data-quality SaaS platforms) that offer no reasoning, versus raw LLM-prompting pipelines that offer reasoning but no cost control or reproducibility.

---

## 3. Background

### 3.1 Data Cleaning as a Pipeline Stage
Data cleaning conventionally spans: profiling → issue detection → strategy selection → execution → validation. AutoClean AI+ formalizes this pipeline as an explicit multi-agent workflow with named responsibilities (Analysis, Evaluation, Decision & Reporting), rather than a monolithic script 🟩[ORIGINAL].

### 3.2 Multi-Objective Optimization (MOO)
MOO seeks solutions that balance two or more conflicting objectives (e.g., cost vs. quality) where no single solution dominates all others — the result is typically a Pareto-optimal set or a scalarized best compromise. The source paper scalarizes the problem into a single **budget-constrained quality maximization**: maximize total quality subject to a hard cost ceiling 🟦[PAPER] (Eq. 1). AutoClean AI+ extends the *objective vector* itself — from {quality, cost} to {data-quality improvement, computational cost, information preservation, statistical validity, fairness impact, downstream ML performance} 🟩[ORIGINAL], evaluated through a transparent weighted decision matrix rather than a hard-budget optimizer, because a data-cleaning *strategy* selection problem (rule-set A vs. rule-set B vs. imputation-method C) has a much smaller and more human-interpretable action space than the paper's *per-sub-task method routing* problem.

### 3.3 Quality Estimation Without Ground Truth (EM Algorithm)
The Expectation-Maximization (EM) algorithm iteratively estimates unknown "true" labels and each method's per-class accuracy (a confusion matrix) purely from the *pattern of agreement/disagreement* among multiple noisy methods applied to the same data — no ground truth is required 🟦[PAPER] (§3.3, Eqs. 2–6). This is directly applicable to AutoClean AI+'s Evaluation Agent when ground-truth labels for "correct" cleaning are unavailable, which is the common real-world case.

### 3.4 Multi-Agent Systems and LangGraph
A multi-agent system decomposes a complex task across specialized agents that communicate through a shared, typed state, rather than one monolithic prompt. LangGraph implements this as a directed graph of nodes (agents) and edges (transitions), with an explicit, inspectable state object passed between them — which is what makes an **audit trail** (§9 below) possible in the first place 🟩[ORIGINAL use of a 🟦[PAPER]-adjacent general technique].

### 3.5 Explainable AI (XAI) in Decision Support
XAI in this project does not mean interpreting a neural network's internal weights; it means natural-language justification of a **decision already reached by deterministic computation** — closer to "report generation over structured evidence" than to classical XAI techniques like SHAP/LIME. This distinction matters because it is what keeps the LLM out of the numerical decision loop.

### Alternatives Considered
- Using SHAP/LIME-style attribution over the ranking model: rejected as unnecessary — the ranking is a transparent weighted-sum decision matrix, which is inherently interpretable; attribution methods are designed for opaque models, and adding one here would be complexity without benefit.

### Justification
Grounding every subsystem in its cheapest sufficient theory (weighted-sum ranking over black-box ML attribution; EM over unsupervised clustering; LangGraph state over ad hoc function chaining) keeps the system explainable by construction rather than requiring add-on interpretability tooling.

---

## 4. Literature Review

| Area | Representative Approaches | Strengths | Limitations Relevant to AutoClean AI+ |
|---|---|---|---|
| Rule-based / statistical DCI (Data Cleaning & Integration) | Regex constraints, Jaccard/cosine similarity, distribution-based outlier detection 🟦[PAPER §2.1] | Cheap, deterministic, explainable by nature | Poor scalability and semantic coverage; brittle under schema drift |
| ML-based DCI | Neural entity matching, learned normalization 🟦[PAPER §2.1] | Captures cross-field/semantic patterns | Needs labeled data; low interpretability |
| LLM-based data cleaning | Entity matching, attribute standardization, anomaly detection via GPT/BERT-family models 🟦[PAPER §2.1] | Best raw accuracy; handles unstructured/semantic errors | High inference cost; opaque; no native cost governance |
| Inference cost optimization | Knowledge distillation, pruning, quantization 🟦[PAPER §2.2] | Reduces cost per call | Model-level fix, not workflow-level; typically trades away accuracy |
| Quality modeling without ground truth | EM-based confusion-matrix estimation 🟦[PAPER §2.3] | No labels required; statistically grounded | Assumes conditional independence of methods' errors; convergence not guaranteed to global optimum |
| Multi-objective optimization | Genetic algorithms, particle swarm, hybrid greedy+DP 🟦[PAPER §2.3, §3.4] | Balances competing goals | NP-hard in general; classic metaheuristics (GA/PSO) are costly at high dimensionality |
| Commercial/OSS data-quality tools (e.g., Great Expectations, OpenRefine, dedicated data-quality SaaS) | Rule/assertion-based validation, profiling dashboards | Mature, production-ready | No multi-objective *strategy comparison*; no LLM-based explanation; typically no human-in-the-loop *approval gate* tied to a quantified trade-off report |
| Human-in-the-loop ML systems (general literature) | Active learning, model cards, approval workflows | Establishes precedent for "AI proposes, human disposes" | Rarely applied specifically to the *data cleaning strategy selection* step, as opposed to labeling or model deployment |

### Theory
The literature clusters into two lineages that rarely intersect: **optimization-and-cost research** (the source paper's lineage) and **explainability/human-oversight research** (the AutoClean AI+ lineage). Multi-agent orchestration frameworks (LangGraph, AutoGen, CrewAI-style patterns) are a third, more recent lineage focused on *decomposing* a task across specialized roles rather than on optimization or explainability per se.

### Design Decisions
AutoClean AI+ is positioned at the intersection of all three lineages, using the multi-agent lineage as the *architectural substrate* that lets the optimization lineage (paper) and the explainability lineage (original contribution) coexist without one contaminating the other.

### Alternatives Considered
- Building on an existing commercial data-quality platform's API instead of implementing evaluation logic from scratch: rejected for academic purposes — a final-year project must demonstrate the student's own implementation of the optimization and evaluation logic, not orchestration of a third-party black box.

### Justification
No reviewed tool in the "commercial/OSS data-quality tools" row combines (a) multi-objective strategy comparison, (b) LLM-generated but non-authoritative explanation, and (c) a mandatory human approval gate keyed to those explanations. This absence is the concrete research gap formalized in §6.

---

## 5. Summary of the IEEE Paper

**Full citation:** Hu, T., Wang, J., Pu, W., Li, J., Gu, R., Bi, X., Yin, H., & Wang, Y.-P. (2026). A Multi-Objective Optimization Framework for Data Cleaning Using Large Language Models. *Big Data Mining and Analytics*, 9(3), 672–686. DOI: 10.26599/BDMA.2025.9020074.

### 5.1 Core Idea
The paper addresses the high inference cost of using LLMs for data cleaning by reframing the problem as **budget-constrained multi-objective optimization** over *method assignment*, rather than trying to make any single method cheaper.

### 5.2 Problem Formulation 🟦[PAPER]
Given a dataset partitioned into sub-datasets \(D_j\) (each tied to a sub-task \(T_j\), e.g., entity matching, attribute normalization, outlier detection) and a set of candidate methods \(S = \{s_1, ..., s_K\}\), the paper selects an assignment \(a(j)\) of a method to each sub-task to:

$$\max_{a(j)} \sum_{j=1}^{M} Q_{a(j)}(D_j) \quad \text{s.t.} \quad \sum_{j=1}^{M} C_{a(j)}(D_j) \le \text{Budget}, \quad a(j) \in \{1,...,K\}$$

### 5.3 The Three Core Components 🟦[PAPER]
1. **Task-aware cost optimization** — decomposes the cleaning pipeline into sub-tasks so that cheap methods can be used where sufficient, and expensive methods (LLMs) are reserved for genuinely hard sub-tasks.
2. **EM-based inference quality modeling** — estimates each method's per-class accuracy (confusion matrix \(\Theta_u\)) and each sample's true-label posterior \(\gamma_i(l)\) without ground truth, by alternating:
   - **E-step:** \(\gamma_i(l) \propto \pi_i(l)\prod_{u=1}^{K}\theta_{u,l,\hat{y}_{i,u}}\)
   - **M-step:** \(\theta_{u,l,c} = \dfrac{\sum_{x_n \in D_j}\gamma_n(l)\cdot \mathbb{1}(\hat{y}_{n,u}=c)}{\sum_{x_n \in D_j}\gamma_n(l)}\), then \(\pi_i(l) \leftarrow \gamma_i(l)\)
   until convergence, producing a per-method quality score \(Q_u(D_j)\).
3. **Hybrid greedy + Dynamic Programming (DP) optimization** — because exact optimization is NP-hard, the paper: (a) starts from a low-cost baseline assignment; (b) computes a **weighted gain metric** for every possible sub-task/method upgrade, \(\Delta_{wg} = \dfrac{\alpha(Q_u(D_j)-Q_{base}(D_j))}{(1-\alpha)(C_u(D_j)-C_{base}(D_j))+\epsilon}\); (c) greedily applies upgrades in descending \(\Delta_{wg}\) order until the budget is exhausted (producing solution \(Sol_0\)); then (d) refines \(Sol_0\) with DP restricted to high-impact sub-tasks: \(DP(r,b) = \max_u\{DP(r-1, b-C_u(D_r)) + Q_u(D_r)\}\).

### 5.4 Methods Compared 🟦[PAPER]
Four candidate methods, in increasing cost/accuracy order: rule-based tools (\(s_1\)), code generation (\(s_2\)), a mid-sized pre-trained language model such as FLAN-T5 (\(s_3\)), and a frontier LLM such as GPT-4o (\(s_4\)).

### 5.5 Complexity Analysis 🟦[PAPER]
Task partitioning: \(O(N\log N)\) (clustering) or \(O(N^2)\) (naive rule grouping). EM quality modeling: \(O(NK)\) per full pass across all sub-tasks (\(O(N_jK)\) per sub-task of size \(N_j\)). Greedy initialization: \(O(MK\log(MK))\), dominated by sorting all \(M(K-1)\) possible upgrades. DP refinement restricted to high-impact sub-tasks: \(O(MBK)\), where \(B\) is the number of discretized budget states.

### 5.6 Experimental Setup and Results 🟦[PAPER]
Evaluated on nine public datasets (Beers, Adult, Breast Cancer, Smart Factory, NASA, Bikes, Soil Moisture, Mercedes, HAR), ranging from ~700 to ~70,000 rows, with real per-dataset USD cost tables for each of the four methods. Compared against an exhaustive upper bound, a naive ("old") greedy baseline, and single-method baselines. The improved greedy+DP hybrid closely tracked the exhaustive optimum, especially in the 50–60% budget range, and achieved **20–30% cost savings relative to an all-LLM strategy with only minor accuracy trade-offs**, maintaining over 90% precision on some datasets (e.g., Breast Cancer) even under tight budgets.

### 5.7 Stated Limitations and Future Work 🟦[PAPER]
The authors explicitly note: (a) the framework has not been tested against mislabeled data or highly imbalanced distributions; (b) applicability to complex/hierarchical/multi-relational data structures is untested; (c) scalability to billions of records or streaming data is unaddressed; and (d) — most relevant here — future work should explore "dynamic adaptations for evolving sub-tasks or deeper integrations with explainable AI and human-in-the-loop approaches to enhance trust and interpretability in data cleaning pipelines."

---

## 6. Research Gap

### Theory
A research gap is a documented, citable absence in prior work that a new project can legitimately claim to fill, distinct from simply "a feature nobody happened to build yet."

### Identified Gap
The source paper solves *cost-optimal method selection* but explicitly leaves open, as future work, the question of **how to make that selection trustworthy and controllable for a human operator** 🟦[PAPER §5.7 / abstract]. Separately, the broader literature reviewed in §4 shows that existing data-quality tooling either (a) optimizes deterministically with no explanation layer, or (b) explains via LLM prompting with no deterministic optimization core and no cost governance. No system in the reviewed literature combines all of: multi-objective strategy scoring, EM-style quality estimation, mandatory human approval, natural-language trade-off explanation, fairness/information-preservation analysis, and full audit-trail persistence.

### Design Decisions
AutoClean AI+ targets exactly this intersection, using a three-agent architecture so each concern (analysis, evaluation, decision/explanation) remains independently testable and independently swappable — e.g., the LLM used for explanation could be replaced without touching the optimization engine.

### Alternatives Considered
- Framing the gap purely as "no open-source implementation of the paper exists": rejected as too narrow and not academically interesting on its own — reproducing a paper is not sufficient for an original final-year project.
- Framing the gap purely as "no XAI dashboard for data cleaning exists": rejected as too broad/unfalsifiable without a rigorous multi-objective core underneath it.

### Justification
Combining "reproduce the paper's optimization core" with "fill the paper's own named gap" yields a gap statement that is simultaneously specific, defensible, and directly traceable to a peer-reviewed source — the strongest possible framing for a final-year project research gap.

---

## 7. Project Objectives

1. 🟦[PAPER-derived] Implement a deterministic, Python-based multi-objective evaluation engine for candidate data-cleaning strategies, informed by the paper's quality/cost trade-off framing.
2. 🟦[PAPER-derived] Implement an EM-style quality/confidence estimation mechanism usable when no ground-truth "correct cleaning" is available.
3. 🟩[ORIGINAL] Design and implement a three-agent (Analysis, Evaluation, Decision & Reporting) architecture orchestrated with LangGraph and a shared, typed workflow state.
4. 🟩[ORIGINAL] Provide natural-language, LLM-generated explanations of the recommended strategy, including trade-offs against alternatives and a stated confidence level — with the LLM strictly prohibited from performing any calculation.
5. 🟩[ORIGINAL] Enforce a human-in-the-loop approval gate before any cleaning strategy is executed against the dataset.
6. 🟩[ORIGINAL] Extend the objective set beyond quality/cost to include information preservation, statistical validity, fairness impact, and downstream ML performance.
7. 🟩[ORIGINAL] Build an interactive Streamlit dashboard for uploading data, comparing strategies, reviewing explanations, and approving/rejecting recommendations.
8. 🟩[ORIGINAL] Automatically generate an executive report, a reproducible cleaning script, and a persistent SQLite audit trail for every run.
9. Deliver the system as a modular, tested, documented, Dockerized final-year project artifact suitable for academic evaluation, with clear paper-vs-original attribution throughout.

### Design Decisions / Alternatives / Justification
Objectives 1–2 are scoped to *preserve*, not *reproduce line-for-line*, the paper's method — AutoClean AI+ evaluates whole cleaning *strategies* (e.g., "median imputation + IQR outlier removal + fuzzy dedup") rather than routing *individual data-cleaning sub-tasks* to one of four LLM-tier methods, because the target use case is a single analyst cleaning one dataset at a time, not a large-scale pipeline optimizing thousands of sub-tasks under a dollar budget. This is a deliberate scope adaptation, not a simplification for its own sake, and it is why "Budget" in the paper's strict USD-cost sense is generalized to a "computational cost" objective in AutoClean AI+ (see §9, §11) rather than implemented as a literal per-API-call billing model.

---

## 8. Scope

### In Scope
- Tabular datasets in common formats (CSV, XLSX, Parquet) uploaded through the Streamlit UI.
- Detection of missing values, duplicate records, outliers, and inconsistent data types.
- Generation and multi-objective ranking of multiple candidate cleaning strategies per dataset.
- LLM-generated explanation, trade-off comparison, and confidence reporting for the top-ranked strategy(ies).
- Mandatory human approval step prior to executing any cleaning strategy.
- Post-cleaning validation, executive report generation, reproducible script export, and SQLite-backed audit trail/experiment history.
- Single-user, single-machine (or single-container) deployment via Docker.

### Out of Scope
- Real-time/streaming data cleaning (the paper itself flags this as unaddressed future work).
- Multi-user authentication, role-based access control, or multi-tenant deployment.
- Cleaning of unstructured data types (free text corpora, images, audio) beyond the tabular fields they may appear in.
- Fine-tuning or training any LLM; only inference-time use of an existing hosted or local LLM is in scope.
- Literal dollar-cost API billing optimization at the sub-task level, as implemented in the paper's large-scale multi-dataset experiments (Table 1) — AutoClean AI+ uses cost as a computational/latency proxy metric appropriate to its single-dataset, interactive use case (see §7 justification).

### Theory / Design Decisions / Alternatives / Justification
Scope boundaries were set using the standard academic project heuristic: everything necessary to demonstrate the research gap (§6) and objectives (§7) end-to-end within a supervised final-year timeline is in scope; everything that would primarily demonstrate *engineering scale* rather than *research contribution* (e.g., distributed streaming, multi-tenant auth) is out of scope. This was chosen over an "implement everything the paper's future-work section mentions" scope, which was rejected as unachievably broad for a single final-year project.

---

## 9. Features Implemented from the IEEE Paper 🟦[PAPER]

| # | Feature | Paper Reference |
|---|---|---|
| 1 | Multi-objective framing of "cleaning quality vs. cost" as a scalarized, budget-constrained maximization problem | §3.1, Eq. 1 |
| 2 | Deterministic, Python-implemented evaluation of candidate strategies (no LLM in the scoring loop) | §3.2–3.4 (methodology) |
| 3 | EM-style quality/confidence estimation without requiring ground truth, adapted for strategy-level rather than sample-level confusion matrices | §3.3, Eqs. 2–6 |
| 4 | Weighted scoring/decision logic conceptually derived from the weighted-gain metric \(\Delta_{wg}\), adapted from a greedy-upgrade selector into a general weighted decision matrix across six objectives | §3.4, Eq. 7 |
| 5 | Explicit, tabulated cost accounting per candidate method/strategy, in the spirit of the paper's Table 1 cost breakdown | §5.1, Table 1 |
| 6 | Baseline-vs-candidate comparison methodology (comparing a low-cost baseline against upgraded strategies) | §5.3–5.4 |
| 7 | Recognition that method/strategy selection is fundamentally a trade-off problem best solved by optimization rather than heuristic default choices | Abstract, §1 |

---

## 10. Original Contributions Introduced in AutoClean AI+ 🟩[ORIGINAL]

| # | Contribution | Rationale |
|---|---|---|
| 1 | Lightweight three-agent architecture (Analysis, Evaluation, Decision & Reporting) on LangGraph with shared workflow state | Not present in paper; enables modularity, testability, and auditability |
| 2 | Explainable AI layer: LLM-generated, non-authoritative natural-language justification of the top-ranked strategy | Directly answers the paper's stated future-work gap (§5.7) |
| 3 | Mandatory human-in-the-loop approval before any cleaning is executed | Directly answers the paper's stated future-work gap (§5.7) |
| 4 | Interactive Streamlit dashboard for strategy comparison | No UI/HCI component exists in the paper (a research-methods paper, not a tool) |
| 5 | Downstream ML impact evaluation as a first-class objective (e.g., train/test a benchmark model pre- and post-cleaning) | Extends the objective set beyond the paper's quality/cost pair |
| 6 | Fairness and information-preservation analysis as first-class objectives | Not addressed anywhere in the paper |
| 7 | Automatic executive report generation (LLM-authored narrative over Python-computed evidence) | Not present in the paper, which reports results manually in prose/figures |
| 8 | Persistent audit trail and experiment history via SQLite (every recommendation, explanation, and human decision logged) | Not present in the paper; required for trust/accountability |
| 9 | Reproducible cleaning script auto-export (so the exact accepted transformation can be re-run outside the app) | Not present in the paper |
| 10 | Streamlit-based, single-analyst interactive workflow, replacing the paper's offline, dataset-partitioned, sub-task-routing workflow | Adapts the paper's batch-experiment design to an interactive decision-support use case |

---

## 11. Functional Requirements

| ID | Requirement | Source |
|---|---|---|
| FR-1 | The system shall accept an uploaded tabular dataset (CSV/XLSX/Parquet) via the Streamlit UI. | 🟩 |
| FR-2 | The Analysis Agent shall profile the dataset and detect missing values, duplicates, outliers, and inconsistent data types, deterministically via Pandas/NumPy/Scikit-learn. | 🟩 (mechanism) / 🟦 (motivation: sub-task/error-characteristic decomposition) |
| FR-3 | The Analysis Agent shall generate at least two candidate cleaning strategies per detected issue profile. | 🟩 |
| FR-4 | The Evaluation Agent shall score every candidate strategy on: data-quality improvement, computational cost, information preservation, statistical validity, fairness impact, and downstream ML performance, using deterministic Python implementations only. | 🟦 (quality/cost core) + 🟩 (extended objective set) |
| FR-5 | The Evaluation Agent shall rank candidate strategies using a documented, reproducible weighted decision matrix. | 🟦 (weighted-gain concept) adapted 🟩 |
| FR-6 | The Evaluation Agent shall estimate strategy confidence using an EM-style estimation procedure when no ground truth is available. | 🟦 |
| FR-7 | The Decision & Reporting Agent shall use an LLM only to explain the Evaluation Agent's numeric output — never to alter, override, or recompute it. | 🟩 |
| FR-8 | The system shall present the top-ranked strategy, its explanation, its confidence, and its trade-offs against alternatives to the user before any execution occurs. | 🟩 |
| FR-9 | The system shall not execute any cleaning strategy without explicit human approval. | 🟩 |
| FR-10 | Upon approval, the Decision & Reporting Agent shall execute the approved strategy and validate the resulting dataset. | 🟩 (workflow) using 🟦-informed metrics |
| FR-11 | The system shall generate an executive report (PDF/Markdown/HTML) summarizing the run. | 🟩 |
| FR-12 | The system shall export a reproducible, standalone Python cleaning script corresponding to the approved strategy. | 🟩 |
| FR-13 | The system shall persist every run (inputs, candidate strategies, scores, chosen strategy, human decision, timestamps) to a SQLite audit trail. | 🟩 |
| FR-14 | The dashboard shall allow interactive, side-by-side comparison of candidate strategies (charts via Plotly). | 🟩 |
| FR-15 | The system shall allow a user to browse past experiment history from SQLite. | 🟩 |

---

## 12. Non-Functional Requirements

| ID | Requirement | Category |
|---|---|---|
| NFR-1 | All deterministic calculations (metrics, scoring, ranking, statistics, ML evaluation, fairness/information-preservation analysis) shall be implemented in Python only; the LLM shall never be invoked for numeric computation. | Correctness / Reproducibility |
| NFR-2 | The system shall follow Clean Architecture and SOLID principles, with clear separation between domain logic, agent orchestration, and presentation (Streamlit). | Maintainability |
| NFR-3 | All public functions/classes shall carry type hints and docstrings. | Code Quality |
| NFR-4 | The system shall use structured logging (not print statements) across all agents and services. | Observability |
| NFR-5 | The system shall handle and report errors gracefully (e.g., malformed uploads, LLM API failures) without crashing the Streamlit session. | Reliability |
| NFR-6 | Configuration (weights, thresholds, model names, DB paths) shall be externalized to configuration files/environment variables, not hard-coded. | Configurability |
| NFR-7 | Core evaluation and optimization logic shall be covered by unit tests (Pytest), independent of the LLM/UI layers. | Testability |
| NFR-8 | The system shall be containerized (Docker) for reproducible deployment. | Portability |
| NFR-9 | The system shall be version-controlled (Git) with meaningful, phase-tagged commit history. | Reproducibility |
| NFR-10 | End-to-end evaluation of a moderately sized dataset (≤100K rows, in line with the paper's largest evaluated dataset, HAR at 70,000 rows) shall complete within an interactively acceptable time (target: under a few minutes on commodity hardware), acknowledging the paper's own scalability caveats for larger data. | Performance |
| NFR-11 | No dataset shall be transmitted to an external LLM API without the fields actually required for the explanation prompt (e.g., aggregate statistics rather than raw sensitive values), to limit unnecessary data exposure. | Privacy/Security |

---

## 13. Stakeholders

| Stakeholder | Interest |
|---|---|
| Student / Developer (you) | Deliver an academically rigorous, demonstrably original final-year project |
| Academic Supervisor / Evaluation Panel | Assess correctness, originality, rigor, and clear paper-vs-original attribution |
| End User (Data Analyst persona) | Wants trustworthy, explainable cleaning recommendations with control over execution |
| Downstream ML Consumer (implicit persona) | Cares about the effect of cleaning decisions on model performance and fairness |
| Original Paper Authors (Hu et al.) | Not a direct stakeholder, but their published gap statement is the citation basis for this project's originality claim |

---

## 14. Use Cases

**UC-1: Upload and Profile a Dataset**
Actor: Data Analyst. The analyst uploads a CSV; the Analysis Agent profiles it and reports detected issues (missing values, duplicates, outliers, type inconsistencies).

**UC-2: Compare Candidate Cleaning Strategies**
Actor: Data Analyst. The analyst reviews multiple candidate strategies ranked by the Evaluation Agent across six objectives, visualized in the Streamlit dashboard.

**UC-3: Review Explanation and Approve/Reject a Strategy**
Actor: Data Analyst. The Decision & Reporting Agent presents the top strategy's LLM-generated explanation, confidence, and trade-offs; the analyst approves, rejects, or requests the next-ranked alternative.

**UC-4: Execute Approved Strategy and Validate Results**
Actor: System (Decision & Reporting Agent), triggered by analyst approval. The approved strategy is executed and the cleaned dataset is validated against expected quality thresholds.

**UC-5: Generate Executive Report and Reproducible Script**
Actor: Data Analyst. After execution, the analyst downloads an executive report and a standalone reproducible Python script.

**UC-6: Review Experiment History**
Actor: Data Analyst / Supervisor. A user browses past runs stored in SQLite, including which strategies were proposed, which were chosen, and by whom/when.

---

## 15. Assumptions

1. The user has access to a working LLM API (e.g., an Anthropic or OpenAI-compatible endpoint) for the Decision & Reporting Agent's explanation function; the system does not assume the LLM is free of cost.
2. Datasets are tabular and fit in memory on the deployment machine (consistent with the paper's largest tested dataset, HAR, at 70,000 rows).
3. Ground-truth "correct" cleaning is *not* generally available, which is why the EM-style estimation approach (🟦[PAPER]) is retained rather than assuming supervised evaluation is always possible.
4. A single analyst operates the system per session; concurrent multi-user editing of the same dataset is not assumed.
5. "Fairness impact" is evaluated with respect to user-specified sensitive/protected columns present in the dataset; the system does not infer protected attributes that are not present.

---

## 16. Constraints

1. **Academic timeline constraint:** the project must be deliverable phase-by-phase within a final-year project schedule; Phase 2 will not begin until this document is approved.
2. **LLM-determinism constraint (project-level rule):** the LLM must never perform or override deterministic calculations, statistics, optimization, or metric computation — enforced architecturally, not just by prompting.
3. **Technology constraint:** the stack is fixed to Python, LangGraph, Pandas, NumPy, Scikit-learn, Plotly, Streamlit, SQLite, Pytest, Git, and Docker, per the project specification.
4. **Data constraint:** no fabricated experimental results, evaluation metrics, or benchmark values may be reported at any phase; all reported numbers must come from actual code execution on actual data.
5. **Attribution constraint:** every feature must be traceable as either 🟦[PAPER] or 🟩[ORIGINAL] throughout all subsequent phases and documentation.

---

## 17. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM explanation drifts from or contradicts the underlying deterministic scores | Medium | High (undermines trust, the project's core value proposition) | Explanation prompts are grounded strictly in the Evaluation Agent's structured output; automated consistency checks can flag numeric mismatches between the explanation text and the source scores (planned for Phase 7) |
| Weighted decision matrix weights are arbitrary/unjustified | Medium | Medium | Default weights will be documented and justified in Phase 6; the dashboard will allow the user to adjust and see the resulting re-ranking, making subjectivity visible rather than hidden |
| EM-style estimation fails to converge or is not meaningfully applicable to whole-strategy (vs. per-sample) evaluation | Medium | Medium | Phase 6 will include a fallback deterministic scoring path if EM-based confidence estimation is not well-posed for a given dataset/strategy set |
| Fairness/information-preservation metrics chosen are contested or dataset-dependent | Medium | Medium | Metrics and their limitations will be explicitly documented (Phase 6/7), not presented as absolute truth |
| Scope creep beyond a completable final-year timeline | Medium | High | Strict phase gating (this document; no Phase 2 without approval) and the explicit Out-of-Scope list (§8) |
| Large datasets causing slow interactive performance in Streamlit | Low–Medium | Medium | NFR-10 sets an explicit performance target; sampling/preview strategies can be used for profiling large files |

---

## 18. Success Criteria

1. All 12 phases are completed and documented with clear 🟦[PAPER] vs. 🟩[ORIGINAL] attribution throughout.
2. The Evaluation Agent's scoring, ranking, and EM-style confidence estimation are implemented entirely in deterministic Python and unit-tested (Pytest), with no LLM involvement in the numeric path (verifiable by code review / architecture diagram).
3. For at least one real dataset, the system can: profile it, generate ≥2 candidate strategies, score/rank them across all six objectives, produce an LLM explanation, require and record human approval, execute the approved strategy, and produce a report, script, and audit-trail entry — end to end, without fabricated numbers.
4. The system demonstrably preserves the paper's core research contribution (multi-objective, quality-vs-cost strategy evaluation) while adding at least the eight original contributions listed in §10.
5. The final artifact is reproducible via Docker and version-controlled with a clear, phase-tagged Git history.
6. The project is presentable to an academic panel with a defensible answer to "what did you take from the paper, and what did you add yourself?" — directly supported by the tables in §9 and §10.

---

## Appendix A: Symbol Reference Carried Forward from the Paper 🟦[PAPER]

| Symbol | Meaning |
|---|---|
| \(D = \{x_i\}_{i=1}^N\) | Original dataset of \(N\) samples |
| \(T = \{T_j\}_{j=1}^M\) | \(M\) sub-tasks (e.g., missing-value handling, outlier detection) |
| \(D_j\) | Sub-dataset for sub-task \(T_j\) |
| \(S = \{s_u\}_{u=1}^K\) | \(K\) candidate methods |
| \(Q_u(D_j)\), \(C_u(D_j)\) | Quality and cost of method \(u\) on sub-dataset \(D_j\) |
| \(a(j)\) | Method index assigned to sub-task \(j\) |
| \(\Theta_u = [\theta_{u,l,c}]\) | Confusion matrix for method \(u\): \(P(\hat{y}=c \mid y=l)\) |
| \(\gamma_i(l)\) | Posterior probability that sample \(i\)'s true label is \(l\) |
| \(\pi_i(l)\) | Prior probability that sample \(i\)'s true label is \(l\) |
| \(\Delta_{wg}\) | Weighted gain metric for a candidate method upgrade |
| \(\alpha\) | Quality-emphasis weight, \(\alpha \in (0.5, 1)\) |
| \(DP(r,b)\) | Best achievable quality using the first \(r\) sub-datasets within budget \(b\) |

This reference table will be reused (and extended with AutoClean AI+-specific notation) starting in Phase 6, so that Evaluation Agent code and documentation stay notationally consistent with the paper wherever the paper's concepts are directly reused.

---

## Summary of Completed Work

Phase 1 has produced a complete research and requirements baseline for AutoClean AI+: a problem statement, motivation, background theory, literature review, a full technical summary of the source IEEE paper (problem formulation, EM algorithm, hybrid greedy+DP optimization, complexity analysis, experimental results, and the paper's own stated limitations/future work), an explicit research gap grounded in the paper's own future-work statement, project objectives, in/out-of-scope boundaries, a paper-vs-original feature traceability pair of tables, 15 functional and 11 non-functional requirements, stakeholders, six use cases, assumptions, constraints, risks with mitigations, and success criteria.

## Suggested Improvements (for consideration before/entering Phase 2)

1. Consider naming the specific downstream ML task(s) (e.g., a benchmark classifier) that will be used for the "downstream ML performance" objective, so Phase 6 can implement it concretely rather than generically.
2. Consider deciding early which LLM provider/model will be used for the Decision & Reporting Agent, since this affects Phase 3 environment setup and Phase 7 prompt design.
3. Consider identifying 1–2 candidate real datasets (could include one of the paper's own public datasets, e.g., Breast Cancer or Beers, for direct comparability) to use consistently across later phases' testing and demonstration.

## Remaining Work
Phases 2–12, beginning with Phase 2 (System Design), pending your approval of this document.

## Recommended Next Step
Review and approve this Phase 1 document (or request revisions). Once approved, Phase 2 – System Design will translate these requirements into the Clean Architecture layer diagram, component design, data model, and LangGraph state schema, with the same theory/design-decisions/alternatives/justification structure.

## Git Commit Message
```
docs(phase-1): add research & requirements baseline for AutoClean AI+

- Summarize IEEE source paper (problem formulation, EM algorithm,
  hybrid greedy+DP optimization, complexity analysis, results,
  stated limitations/future work)
- Define research gap grounded in paper's own future-work statement
  (explainability + human-in-the-loop)
- Document objectives, scope, functional (15) and non-functional (11)
  requirements, stakeholders, use cases, assumptions, constraints,
  risks, and success criteria
- Establish paper-vs-original feature attribution tables (PAPER/ORIGINAL)
  to be carried through all subsequent phases
- No source code in this phase, per specification
```
