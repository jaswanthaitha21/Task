Here's a comprehensive project specification that you can hand to Codex (or another coding agent) as the design document.

Project Specification

Project Name

SASD (Structure-Aware Speculative Delegation)

Subtitle:

A Hierarchical AI Inference Framework for Cost-Efficient Enterprise Document Intelligence

---

1. Vision

Enterprise document extraction pipelines typically send the entire document to a large multimodal LLM (such as Gemini) regardless of document complexity.

This results in:

- High inference cost
- High latency
- Unnecessary compute
- Poor scalability

SASD introduces a hierarchical delegation layer that decides which parts of a document require expensive reasoning and which can be handled by a lightweight local model.

The objective is to preserve extraction quality while significantly reducing LLM usage.

---

2. Research Hypothesis

Not every page, region, table, or field requires the same amount of reasoning.

A lightweight model should solve easy extraction tasks.

Only difficult regions should be delegated to a large LLM.

---

3. High-Level Architecture

                PDF / Image
                     │
                     ▼
        Structure Analyzer
     (Layout + Region Detection)
                     │
                     ▼
         Document Structure Graph
                     │
                     ▼
          Delegation Planner
                     │
      ┌──────────────┴──────────────┐
      │                             │
      ▼                             ▼
 Small Local Model           Gemini / Large LLM
      │                             │
      └──────────────┬──────────────┘
                     ▼
              Result Merger
                     │
                     ▼
             Structured JSON Output

---

4. Core Components

Component 1

Structure Analyzer

Purpose:

Understand document layout before extraction.

Responsibilities:

- Detect pages
- Detect tables
- Detect paragraphs
- Detect key-value regions
- Detect signatures
- Detect stamps
- Detect checkboxes

Possible models:

- DocLayout-YOLO
- PaddleOCR Layout
- LayoutParser
- MinerU
- Docling

Output:

{
  "page": 1,
  "regions": [
    {
      "type": "table",
      "bbox": [x1,y1,x2,y2]
    },
    {
      "type": "paragraph"
    }
  ]
}

---

Component 2

Structure Graph Builder

Convert detected regions into a hierarchical graph.

Example:

Document

 ├── Page 1

 │      ├── Header

 │      ├── Vehicle Table

 │      ├── Signature

 │      └── Footer

 ├── Page 2

 └── Page 3

Every node should store:

- type
- coordinates
- page number
- extracted text (optional)
- confidence

---

Component 3

Small Local Model

Purpose:

Extract straightforward fields.

Candidate models:

- Qwen2.5-3B-Instruct
- Qwen2.5-VL
- Phi-4 Mini
- Gemma 3 (small)
- SmolDocling (for document understanding if suitable)

Responsibilities:

Extract:

- Name
- DOB
- Policy Number
- Premium
- Registration Number
- Engine Number
- Chassis Number
- PAN
- Aadhaar
- Dates

Also output confidence.

Example:

{
  "policy_number":{
      "value":"ABC12345",
      "confidence":0.99
  }
}

---

Component 4

Delegation Planner

This is the main research contribution.

Input:

- Region type
- Field type
- Local model confidence
- Layout complexity
- Table complexity
- Handwritten detection
- OCR confidence (if OCR is used)
- Business rules

Output:

Local

or

Gemini

Example:

Field| Decision
Name| Local
Premium| Local
Policy Number| Local
Accident Description| Gemini
Handwritten Notes| Gemini
Medical Narrative| Gemini

Version 1:

Rule-based planner.

Version 2:

Learned planner.

---

Component 5

Gemini Verification

Gemini should receive ONLY:

- difficult regions
- uncertain fields
- ambiguous sections

Instead of:

Entire document

Gemini receives:

Verify

Policy Number

Verify

Nominee

Verify

Handwritten Notes

---

Component 6

Result Merger

Merge outputs from:

Local model

+ 

Gemini

Produce final JSON.

---

5. Pipeline

PDF

↓

Structure Analysis

↓

Region Detection

↓

Small Model Extraction

↓

Confidence Estimation

↓

Delegation Planner

↓

Gemini Verification

↓

Merge Results

↓

JSON

---

6. Research Questions

RQ1

Can hierarchical delegation reduce LLM usage without reducing extraction accuracy?

RQ2

Can field-level routing outperform sending the full document to Gemini?

RQ3

How much latency reduction is achieved?

RQ4

How much API cost reduction is achieved?

RQ5

What percentage of fields can be solved locally?

---

7. Evaluation Metrics

Accuracy

Field-level precision

Field-level recall

Field-level F1

Exact Match

JSON Accuracy

---

Performance

Latency

Average latency per document

Throughput

Documents/sec

GPU utilization

Memory

---

Cost

Gemini tokens

Gemini requests

Estimated API cost

Average cost/document

---

Delegation Metrics

Percentage handled locally

Percentage delegated

Delegation accuracy

Planner precision

Planner recall

---

8. Baselines

Baseline 1

Entire PDF → Gemini

Baseline 2

OCR → Gemini

Baseline 3

OCR → Local LLM

Baseline 4

SASD

---

9. Suggested Tech Stack

Python

FastAPI

PyTorch

Transformers

vLLM (optional)

DocLayout-YOLO or LayoutParser

PaddleOCR or Docling (optional)

Gemini API

Pydantic

OpenCV

NetworkX (for structure graph)

MLflow or Weights & Biases (optional for experiment tracking)

---

10. Project Directory

sasd/

    data/

    models/

    planner/

    structure/

    extraction/

    verification/

    evaluation/

    api/

    experiments/

    notebooks/

    docs/

---

11. Milestones

Week 1

- Build structure analyzer
- Parse documents
- Build graph representation

Week 2

- Integrate local model
- Extract fields
- Confidence estimation

Week 3

- Build delegation planner
- Integrate Gemini verification
- Merge outputs

Week 4

- Benchmark against Gemini baseline
- Measure latency, cost, and accuracy
- Prepare demo and report

---

12. Risks

- Planner routes difficult fields to the local model, reducing quality.
- Planner overhead outweighs latency savings.
- Local model quality is insufficient for some document types.
- Gemini API latency dominates overall runtime.

Mitigations:

- Start with conservative delegation.
- Escalate low-confidence predictions.
- Benchmark using multiple document types.

---

13. Success Criteria

Minimum:

- ≥95% of Gemini field-level accuracy.
- 30–50% reduction in Gemini usage.

Strong:

- ≥98% of Gemini accuracy.
- 60–80% reduction in Gemini requests or processed content.
- 2–5× improvement in throughput.

Stretch Goal:

- Demonstrate that SASD is a reusable inference orchestration framework applicable beyond insurance (banking, healthcare, legal, finance).

---

14. Future Extensions

- Learned delegation planner using reinforcement learning.
- Multi-agent verification.
- Dynamic compute budgeting.
- Hierarchical speculative page navigation.
- Cross-document memory reuse.
- Adaptive routing based on latency or cost budgets.
- Support for multiple backend LLMs (Gemini, GPT, Claude, local VLMs).

---

15. Important Note

This POC is not intended to replace Gemini.

The goal is to create an AI inference orchestration layer that intelligently decides when a powerful LLM is actually needed. If successful, the same orchestration strategy could be applied to many enterprise document workflows where reducing latency and cloud inference cost is important while maintaining high extraction quality.One recommendation before you start coding: validate the novelty with your manager first. Present the architecture and research hypothesis, and ask whether the team has already explored field-level routing or delegation. A 15-minute discussion now can save weeks of building something that overlaps with an existing internal prototype.
