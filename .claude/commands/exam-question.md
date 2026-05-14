---
description: Generates a CCA Foundations exam practice question
argument-hint: domain number (1-5) and topic, e.g. "1 stop_reason"
context: fork
---

Generate one CCA Foundations certification exam practice question.

Domain and topic: $ARGUMENTS

Parse the arguments as: first token = domain number (1-5), remaining = topic.

Domain reference:
- Domain 1 — Agentic loop control flow (stop_reason, tool execution, hooks, iteration)
- Domain 2 — Tool design (descriptions, NOT FOR clauses, error structure, MCP)
- Domain 3 — Claude Code configuration (CLAUDE.md hierarchy, rules, slash commands)
- Domain 4 — Prompt engineering (explicit criteria, few-shot, structured output, batches)
- Domain 5 — Context management (CaseFacts, lost-in-middle, escalation, numerical precision)

Output format — use this exact structure:

**Domain [N] — [Domain name]**
**Topic: [topic]**

**Scenario:**
[2-4 sentences describing a realistic production situation involving an insurance claims agent or developer workflow]

**Question:**
[One clear question asking what is correct, what would break, or what decision to make]

A) [option]
B) [option]
C) [option]
D) [option]

**Answer:** [letter]

**Why correct:** [one sentence]

**Why A is wrong:** [one sentence]
**Why B is wrong:** [one sentence]
**Why C is wrong:** [one sentence]
**Why D is wrong:** [one sentence]

Requirements:
- Wrong answers must be plausible misconceptions, not obviously wrong
- Difficulty: architect-level judgment, not definition recall
- Do not ask me any questions — generate the question immediately