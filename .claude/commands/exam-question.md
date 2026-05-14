---
description: Generates a CCA exam practice question from current file
argument-hint: domain number (1-5) and topic, e.g. "1 stop_reason"
context: fork
---

Generate a CCA Foundations exam practice question.

Domain and topic: $ARGUMENTS

Requirements:
- Scenario-based question set in an insurance or software context
- One correct answer and exactly three plausible distractors
- Wrong answers must be common misconceptions, not obviously wrong
- After the question, provide: correct answer letter, why it is correct,
  and why each distractor is wrong
- Difficulty: architect-level judgment, not definition recall

Base the question on concepts demonstrated in this codebase where possible.