# MAGI System (Experimental Multi-Agent Decision Engine)

This project implements a small experimental decision system inspired by the **Magi System** from *Neon Genesis Evangelion*.

Instead of relying on a single model response, the system evaluates a scenario through **three distinct reasoning perspectives**, each implemented as an AI agent.

The final decision is produced by comparing their outputs and aggregating the result.

The goal is not to produce "the correct answer", but to **surface structured disagreement and reasoning diversity**.

---

# Architecture

The system contains three decision agents:

### Melchior — Analytical
Focuses on:

- logical consistency
- risk analysis
- expected outcomes
- robustness under uncertainty

Typical question:
> "Which option is the most logically defensible?"

---

### Balthasar — Human-Centered
Focuses on:

- human impact
- fairness
- trust and legitimacy
- organizational stability

Typical question:
> "Which option minimizes disproportionate human harm?"

---

### Casper — Strategic / Pragmatic
Focuses on:

- strategic advantage
- competitive positioning
- capability building
- resource leverage

Typical question:
> "Which option strengthens our position in the real world?"

---

# Decision Aggregation

After all agents evaluate a scenario, their outputs are combined using a comparator that performs:

### Majority vote
The option selected by the majority of agents becomes the final decision.

### Weighted vote
Confidence scores are summed per decision to measure the strength of support.

Example:
```
Melchior → B (75)
Balthasar → B (85)
Casper → B (75)

Weighted support: B = 235
```
### Agreement score
Measures convergence among agents.

| Pattern | Score |
|-------|------|
| unanimous | 1.0 |
| 2–1 majority | 0.67 |
| full disagreement | 0.33 |

### Consistency checks
Basic heuristics detect cases where an agent:

- selects an option
- but describes it using strongly negative reasoning

This helps identify **internally inconsistent outputs**.

---

# Human-Readable Decision Report

Instead of raw JSON, the system produces a readable report:
```
MAGI DECISION REPORT

Scenario outcome: B
Decision mode: unanimous
Agreement score: 1.00
Weighted support: B=235

Why this option won
	•	Melchior: moderate risk and reward balances uncertainty
	•	Balthasar: avoids concentrated human harm
	•	Casper: improves long-term capability

Agent perspectives
...
```
This makes the system easier to inspect and reason about.

---

# Project Structure
```
src/magi
│
├── agents
│   ├── base_agent.py
│   ├── melchior.py
│   ├── balthasar.py
│   └── casper.py
│
├── models
│   ├── decision_result.py
│   └── final_decision.py
│
├── voting
│   ├── comparator.py
│   └── report_formatter.py
│
└── llm_client.py
```
Test scripts live in:
```
tests/
```
---

# Running a Scenario

Example:
```
PYTHONPATH=src python tests/test_comparator.py
```
This will:

1. run the scenario through all agents
2. compare their decisions
3. generate a readable MAGI decision report

---

# Requirements

Python 3.10+

Recommended environment:
```
conda create -n magi python=3.12
conda activate magi
pip install -r requirements.txt
```
---

# Current Status

This is an **experimental prototype**.

The system currently supports:

- structured agent outputs
- multi-agent comparison
- weighted voting
- consistency checks
- human-readable reporting

Future directions may include:

- multi-round agent debate
- dynamic weighting of agents
- scenario datasets
- evaluation metrics for reasoning diversity

---

# Inspiration

Inspired by the **Magi System** from *Neon Genesis Evangelion*, which separates decision-making into three perspectives.

This project explores a similar idea using modern LLMs.

---

# License

MIT
