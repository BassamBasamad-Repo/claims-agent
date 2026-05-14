---
description: Diagnoses agentic loop failures from terminal output
argument-hint: paste the terminal output showing the failure
context: fork
---

Diagnose this agentic loop failure:

$ARGUMENTS

Analyse the output and identify:

1. Which iteration failed and what stop_reason was returned
2. Which tool was called and what input it received
3. Whether the failure is in: tool execution, hook firing, 
   context management, or loop control flow
4. Whether the error is transient (retry) or structural (fix required)

Then provide:
- Root cause in one sentence
- The specific line in loop.py or hooks.py most likely responsible  
- The minimal code change to fix it
- A test case that would catch this failure in future

Be specific — reference actual function names and line numbers 
from the codebase.