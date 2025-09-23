Q1: Why are you using nest_asyncio.apply()?
A: Because asyncio.run() can't be called inside another event loop (like Streamlit's), which causes runtime errors. nest_asyncio patches this so we can run concurrent evaluations safely.

Q2: Why not just run everything sequentially?
A: Sequential would take ~15–20 min for 10 questions due to multiple LLM calls per row. Concurrent execution reduces this to under 2 minutes, making it practical for demos and iteration.

Q3: Why use ThreadPoolExecutor instead of pure async?
A: Some libraries (like DeepEval) use blocking calls internally. ThreadPoolExecutor allows us to run them concurrently within an async context without freezing the UI.

Q4: Why do you fall back to ISO-8859-1 encoding?
A: Some CSVs (especially from Windows) use non-UTF-8 encodings. Without fallback, reading fails. This ensures compatibility across systems.

Q5: Why use KeyValueAlignmentScore even for non-KV tasks?
A: It’s smart enough to detect flat strings (like "POSITIVE") and treat them as {"value": "POSITIVE"}, allowing consistent scoring across structured and unstructured outputs.

Q6: Are these metrics reliable? Isn’t LLM-as-a-judge subjective?
A: Yes, there’s inherent subjectivity — but trends are stable. We use it for relative comparison, not absolute truth. Industry tools like LangSmith, W&B, and Confident AI use the same approach.

Q7: Why only these metrics? What do they mean?
Answer Relevancy
Does the answer address the input question?
Contextual Precision
Are retrieved facts actually used in the answer?
Contextual Recall
Did the answer include all relevant facts from context?
G-Eval (Correctness)
Is the output factually consistent with ground truth?
Levenshtein
String similarity (fast baseline)
Key-Value Alignment
Accuracy of extracted fields
These cover functional quality dimensions needed for production RAG/apps.

Q8: Why separate Run vs Compare?
A: Separation of concerns:

Run: Focus on generating outputs
Compare: Focus on evaluating quality
This mirrors real-world pipelines where different teams handle generation vs validation.
Q9: Can this scale to hundreds of rows?
A: With concurrency + paid API keys, yes. Add sampling (df.sample(n=20)) for fast previews. For full eval, batch processing or cloud workers can be added later.

Q10: How do I explain zero KV scores?
A: "Initially, our parser expected strict JSON format. Now it handles natural language too. The updated version correctly scores even simple outputs like 'POSITIVE'."
Q1: Why did you separate "Run Experiment" and "Compare Results" into two pages?
A: To enforce separation of concerns:

Run Experiment: Focuses on generating actual_output using inference models.
Compare Results: Evaluates quality using LLM-as-a-judge metrics.
This mirrors real-world MLOps pipelines where generation and evaluation are decoupled for reusability and reproducibility.
Q2: Why use Streamlit instead of Flask/Django or a full web app?
A: Streamlit allows rapid prototyping with minimal boilerplate. It’s ideal for internal tools, demos, and evaluators where interactivity matters more than scale. For production deployment, we can containerize it or migrate the backend later.

Q3: Why not just run everything in one script?
A: Modularity improves maintainability. Each page has a single responsibility, making debugging easier and enabling team collaboration (e.g., one person works on inference, another on evaluation).

Q4: How do you ensure API keys aren’t exposed?
A: We use Streamlit’s secure secrets management via .streamlit/secrets.toml, which is never committed to version control. In production, we’d use environment variables or secret managers like AWS Secrets Manager.

Q5: Why use nest_asyncio.apply()? Isn't that discouraged?
A: Yes, generally — but required here because:

DeepEval uses async internally (a_generate)
Streamlit runs its own event loop
Without nest_asyncio, calling asyncio.run() fails with “event loop already running”
It's a known workaround used in production-grade tools when integrating async libraries.
⚡ Concurrency & Performance
Q6: Why use ThreadPoolExecutor instead of pure async/await?
A: Because some underlying libraries (like DeepEval) make blocking calls. Using threads lets us run multiple blocking operations concurrently without freezing the UI. Pure async would require full non-blocking support down the stack.

Q7: Can this handle 1000 rows efficiently?
A: With current design, yes — but with caveats:

Use sampling (df.sample(n=50)) for fast feedback
For full eval, batch processing + retry logic should be added
Can scale horizontally by distributing evaluations across workers
Q8: What happens if one metric fails during concurrent execution?
A: The failure is caught and logged, while other metrics continue. This ensures partial results are preserved rather than failing the entire row. We return None for failed metrics and warn in debug logs.

Q9: Why not cache evaluation results between runs?
A: Great point — caching would speed up re-runs. We could hash (input, expected, actual) and store scores locally. Added complexity, but worth considering for large datasets. Would reduce redundant LLM calls.

Q10: Why does evaluation take so long even with concurrency?
A: Each metric makes an LLM API call (Answer Relevancy, G-Eval, etc.). Even with concurrency, each takes 5–10 seconds. For 5 rows × 5 metrics = ~25 calls → several minutes. This reflects real cost of semantic evaluation — there’s no shortcut.

🤖 LLM-as-a-Judge & DeepEval
Q11: Are these metrics reliable? Aren’t they subjective?
A: They’re as reliable as industry standards. Tools like LangChain, W&B, and Confident AI use the same approach. While subjectivity exists, trends (e.g., Model A > B) are stable. We use them for relative comparison, not absolute truth.

Q12: Why only these specific DeepEval metrics?
A: These cover key dimensions:

Answer Relevancy: Does output address input?
Contextual Precision: Are retrieved facts used?
Contextual Recall: Are all relevant facts included?
G-Eval (Correctness): Factuality vs ground truth
These are most critical for QA, summarization, extraction tasks.
Q13: Why not use BLEU or ROUGE?
A: BLEU/ROUGE rely on n-gram overlap — poor for paraphrasing or semantic similarity. For example:

Expected: "The sky is blue"
Actual: "It looks clear today"
→ Low BLEU score despite correct meaning
LLM-based metrics understand semantics better.
Q14: Can G-Eval be gamed by verbose outputs?
A: Potentially, yes. But our prompt asks: "Is the actual output factually consistent?" — focusing on accuracy, not length. Still, human review remains essential for high-stakes decisions.

Q15: Why not define custom metrics entirely outside DeepEval?
A: DeepEval provides battle-tested infrastructure: test cases, scoring, formatting. Building from scratch would reinvent the wheel. We extend it (e.g., KV Alignment) where needed.

💾 Data Handling & Robustness
Q16: How do you handle different CSV encodings?
A: We try UTF-8 first, fall back to ISO-8859-1. This handles most regional encodings (especially Windows-generated CSVs). Without fallback, reading fails silently.

Q17: What if column names differ across files?
A: We require standard columns (question, expected_output, actual_output). If missing, we show a warning and skip. Users must standardize data before upload — common in ETL workflows.

Q18: Can this process JSONL or Parquet files?
A: Not currently, but easily extensible. We chose CSV for simplicity and universal compatibility. Adding file type detection and parsers for JSONL/Parquet would take <1 hour.

Q19: How do you parse structured outputs like JSON?
A: Our KeyValueAlignmentScore tries:

JSON parsing
Regex for "Key: Value" patterns
Fallback: treat entire string as single value
This handles messy LLM outputs gracefully.
Q20: Why is Key-Value Alignment sometimes 0.0 even when outputs look similar?
A: Because parsing failed — e.g., no colons, invalid JSON, or mismatched keys. We now log parsed values so users can debug. Future improvement: allow fuzzy key matching (e.g., “sentiment” ≈ “mood”).

📊 Visualization & Interpretation
Q21: Are the charts meaningful or just decorative?
A: Charts reveal actionable insights:

Leaderboard: Shows overall ranking
Per-question winner analysis: Exposes model strengths/weaknesses
Distribution histograms: Reveal consistency (low variance = stable)
These help choose models based on task requirements.
Q22: Why include Levenshtein if you have G-Eval?
A: Levenshtein is fast and deterministic — great baseline. G-Eval is slow but semantic. Together, they give both surface-level and deep insight. Also useful for debugging: if Levenshtein ≈ 1.0, no need for deeper eval.

Q23: Can we export charts as images/PDF?
A: Not yet, but Plotly supports .write_image(). We can add PNG export buttons. PDF would require matplotlib or weasyprint, but feasible.

Q24: Why group by Model in leaderboard?
A: To compare average performance across all questions. This is standard in benchmarking (e.g., MLPerf). Individual results are available in tabs.

🔐 Safety & Reliability
Q25: What happens if Gemini hits rate limits?
A: The error is caught, logged, and user sees a message. With a paid key, quotas are high (~60K/day). We could add retry-with-backoff or fallback to OpenAI.

Q26: Is thread-safe logging really necessary?
A: Yes. st.session_state is not thread-safe. Writing to it from ThreadPoolExecutor causes race conditions and crashes. Using a shared Python list avoids this.

Q27: Could concurrent evaluation corrupt results?
A: No — each row is independent. No shared state between evaluations. Even if order changes, final aggregation is correct.

Q28: How do you prevent infinite loops or runaway costs?
A: By limiting:

Max rows per file (can add limit)
Max concurrent tasks
Timeout per LLM call
In future, add budget tracking (e.g., stop after $1 spent)
🚀 Future & Scalability
Q29: Can this be deployed on cloud platforms?
A: Yes — Streamlit Community Cloud, AWS, GCP, Azure all support it. Just package with Docker and expose via HTTPS. Can add auth, monitoring, CI/CD.

Q30: Can we evaluate RAG systems end-to-end?
A: Yes — and we already simulate it! The retrieval_context field mimics retrieved documents. Add citation checks or faithfulness metrics next.

Q31: Will this work offline?
A: Not currently — relies on cloud LLM APIs. But we could integrate local models (Llama 3, Mistral) via Ollama or HuggingFace for air-gapped environments.

Q32: Can we automate threshold-based pass/fail decisions?
A: Yes — add rules like:

python


1
2
⌄
if avg_correctness < 0.7:
    st.error("Model failed correctness threshold")
Useful for CI/CD pipelines.

Q33: Why not use vector similarity for answer relevance?
A: Cosine similarity works for embeddings, but doesn’t assess meaning. Two sentences can be close in vector space but factually wrong. LLM judges understand context better.

Q34: How do you validate the judge model itself?
A: Good question — we assume the judge is trusted (Gemini 1.5 Pro / GPT-4o). To validate, we could:

Run human-eval subset
Cross-check multiple judge models
Use consensus scoring
Q35: Can we add A/B testing between prompts?
A: Absolutely. Extend "Run Experiment" to accept multiple prompts, generate side-by-side outputs, then compare. That’s the next natural step.
