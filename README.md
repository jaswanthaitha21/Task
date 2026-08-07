I think we should not jump into coding yet. One thing I've learned from production AI projects is:

> 80% of the success comes from validating the hypothesis before writing thousands of lines of code.



If I were leading this as a research engineer, this is exactly the roadmap I'd follow.


---

Project: AIRS (Adaptive Inference Routing System)

Goal

Build a research POC that reduces enterprise document extraction cost and latency by intelligently routing work to the cheapest capable engine while maintaining near-Gemini extraction quality.

Research Question

> Can adaptive inference routing reduce cloud LLM usage while maintaining ≥98% of Gemini's extraction accuracy?




---

Phase 0 — Literature & Novelty Check (1–2 days)

Objective

Ensure AIRS is genuinely novel and identify the closest related work.

Tasks

Read and summarize:

EcoDoc (adaptive modality selection)

LongSpec

QuantSpec

SpecCache

MARS (adaptive reasoning)

MoLoRAG

FLOWREADER


Create a comparison table:

Problem solved

Core idea

Limitation

How AIRS differs



Deliverable

docs/literature_review.md


---

Phase 1 — Validate the Core Assumption (2–3 days)

Objective

Answer the most important question before building anything.

Experiment 1

Measure Gemini performance on:

Full document

Single page

Cropped region


Record:

Latency

Token usage (if available)

API cost

Accuracy


Experiment 2

Measure parsing cost using one parser (Docling, PaddleOCR, or another).

Record:

Parsing time

OCR time

Layout detection time


Success Criterion

Determine whether reducing the input size to Gemini actually yields meaningful savings.

Deliverable

docs/feasibility_report.md


---

Phase 2 — Dataset Preparation (2–3 days)

Collect Documents

Gather a representative set of insurance documents.

Examples:

Proposal forms

RC books

Driving licences

Aadhaar

PAN

Invoices

Medical reports

Claim forms


Target:

100–300 documents for a POC.


Annotation

Define a schema (20–40 KVPs).

Example:

{
  "policy_number": "",
  "premium": "",
  "registration_number": "",
  "engine_number": "",
  "nominee": "",
  "claim_amount": ""
}

Create ground truth labels.


---

Phase 3 — Baseline (3–4 days)

Build the simplest benchmark.

Pipeline:

PDF
 ↓
Gemini
 ↓
JSON

Measure:

Accuracy

Latency

Cost

Throughput


This becomes the baseline every future experiment must beat.


---

Phase 4 — AIRS Architecture (Week 2)

Module 1 — Document Parser

Input:

PDF


Output:

Document Graph


The graph should contain:

Pages

Regions

Tables

Paragraphs

Bounding boxes

Extracted text (if available)


Only parse once.


---

Module 2 — Task Generator

Convert the schema into extraction tasks.

Example:

Extract Policy Number
Extract Premium
Extract VIN
Extract Claim Description


---

Module 3 — Evidence Locator

Find the minimum region relevant to each task.

Example:

Policy Number
→ Page 2, Box 14

Premium
→ Page 4, Table 2

Nominee
→ Page 5, Form Section

Initially use heuristics. Later improve.


---

Module 4 — Routing Engine

This is the research contribution.

For each task, decide:

Skip

Rules / Regex

Small Model

Gemini

Version 1:

Rule-based routing.


Version 2:

Learned routing.



---

Module 5 — Execution Engine

Run only the selected engine for each task.

No engine should process the entire document.

Each engine receives only the evidence relevant to its task.


---

Module 6 — Result Fusion

Merge outputs into one final JSON.


---

Phase 5 — Evaluation (Week 3)

Compare:

Baseline

PDF
 ↓
Gemini

vs

AIRS

PDF
 ↓
Parser
 ↓
Task Generator
 ↓
Router
 ↓
Regex / Local / Gemini
 ↓
Merge

Metrics:

Field-level precision

Recall

F1

Exact match

Latency

Cost per document

Gemini invocation rate

Throughput



---

Phase 6 — Ablation Studies

Measure the impact of each component.

Examples:

1. Parser + Gemini


2. Parser + Router + Gemini


3. Parser + Router + Regex + Gemini


4. Parser + Router + Local + Gemini


5. Full AIRS



This shows where gains come from.


---

Suggested Tech Stack

Language:

Python


API:

FastAPI


Models:

Gemini

Small local VLM/LLM (later)


Parsing:

Docling or PaddleOCR


Libraries:

Transformers

OpenCV

Pydantic

NetworkX


Evaluation:

Pandas

NumPy

Matplotlib



---

Repository Structure

airs/
│
├── data/
├── docs/
├── parser/
├── graph/
├── tasks/
├── router/
├── engines/
│   ├── regex/
│   ├── local/
│   └── gemini/
├── fusion/
├── evaluation/
├── experiments/
├── api/
└── notebooks/


---

Success Metrics

Metric	Target

Accuracy	≥98% of Gemini baseline
Gemini usage	Reduce by 60–80%
Cost	Reduce by 5–10× (if routing is effective)
Throughput	Improve by 2–5×
Parser overhead	Small relative to end-to-end runtime



---

Risks to Validate Early

Does Gemini become significantly faster when given only relevant pages or regions?

Can the parser reliably locate evidence without expensive processing?

Can the router make correct decisions without introducing excessive overhead?

Does the local model add enough value to justify its execution time?



---

What to Ask Codex to Build First

Sprint 1 (Do not use AI yet)

PDF ingestion.

Document graph generation.

Page/region representation.

Schema configuration.

Benchmark framework.


Sprint 2

Baseline Gemini pipeline.

Metrics collection.

Cost and latency logging.


Sprint 3

Evidence locator.

Rule-based router.

Regex engine.


Sprint 4

Gemini verification on evidence only.

Result merger.

Evaluation dashboard.


Sprint 5

Plug in a local model.

Experiment with adaptive routing.

Optimize based on benchmarks.



---

One final recommendation

Before you ask Codex to write any code, make it build the project as a research platform rather than a single pipeline. Every module (parser, router, engines, evaluator) should be swappable through configuration. That way, you can easily compare different parsers, local models, routing strategies, and LLMs without rewriting the system. That flexibility will make the POC far more valuable for experimentation and much easier to present to your manager.
