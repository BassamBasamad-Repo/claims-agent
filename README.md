# AlShifa Claims Resolution Agent

A production-grade insurance claims resolution agent built as part of 
preparation for the **Claude Certified Architect – Foundations (CCA)** 
certification.

## Purpose

This project demonstrates all five CCA exam domains through a working 
agentic application. It is not connected to any real insurance system — 
all data is fictional and created for learning purposes.

## What this project demonstrates

| Domain | Concept | Where to find it |
|---|---|---|
| D1 — Agentic Architecture | stop_reason loop control | `src/agent/loop.py` |
| D1 — Agentic Architecture | PreToolUse hook enforcement | `src/agent/hooks.py` |
| D1 — Agentic Architecture | Multi-tool iteration | `src/agent/loop.py` |
| D2 — Tool Design & MCP | Tool descriptions with NOT FOR clauses | `src/tools/*.py` |
| D2 — Tool Design & MCP | Structured error responses | `src/tools/*.py` |
| D2 — Tool Design & MCP | Read vs write tool separation | `src/tools/` |
| D3 — Claude Code | CLAUDE.md hierarchy | `CLAUDE.md`, `src/tools/CLAUDE.md` |
| D3 — Claude Code | Path-scoped rules | `.claude/rules/` |
| D3 — Claude Code | Custom slash commands | `.claude/commands/` |
| D5 — Context Management | Case facts block | `src/agent/session.py` |
| D5 — Context Management | CaseFacts updated per tool call | `src/agent/loop.py` |

## Architecture

claims-agent/
├── CLAUDE.md                    # Project-level Claude Code config
├── src/
│   ├── agent/
│   │   ├── loop.py              # Agentic loop — stop_reason control flow
│   │   ├── hooks.py             # PreToolUse + PostToolUse enforcement
│   │   └── session.py           # CaseFacts — persistent context block
│   ├── tools/
│   │   ├── CLAUDE.md            # Directory-level tool rules
│   │   ├── get_member.py        # Read tool — member profile lookup
│   │   ├── lookup_claim.py      # Read tool — claim history and status
│   │   ├── process_approval.py  # Write tool — claim approval (hook applies)
│   │   └── escalate_to_adjuster.py  # Write tool — human escalation
│   └── data/
│       ├── members.json         # Mock member records
│       ├── claims.json          # Mock claim records
│       └── escalations.json     # Escalation log (created at runtime)
├── tests/
│   ├── test_loop.py
│   ├── test_hooks.py
│   └── test_escalation.py
└── .claude/
├── rules/                   # Path-scoped Claude Code rules
│   ├── agent.md             # Rules for src/agent/.py
│   ├── tools.md             # Rules for src/tools/.py
│   └── tests.md             # Rules for tests/*.py
└── commands/
└── review-agent.md      # /review-agent slash command


## Setup

```bash
# Clone the repo
git clone https://github.com/your-username/claims-agent.git
cd claims-agent

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your Anthropic API key
```

## Running the agent

```bash
python -m src.agent.loop
```

## Running the compliance review

Open Claude Code and run:

/review-agent src/agent/loop.py

## Key design decisions

**Why PreToolUse hook instead of system prompt for threshold enforcement?**
System prompt instructions are probabilistic — the model follows them most 
of the time. A PreToolUse hook is deterministic — it fires on every call 
regardless of model reasoning. Financial thresholds must be enforced by 
code, not prompts.

**Why four tools instead of one?**
A single generic tool with an ambiguous description causes model misrouting 
on similar queries. Four clearly bounded tools with NOT FOR clauses give the 
model unambiguous selection criteria.

**Why separate read and write tools?**
Write tools require hook validation and carry irreversibility risk. Keeping 
them in separate files makes the boundary explicit and ensures hooks are 
never accidentally omitted on write operations.

## CCA exam domains covered

- Domain 1 (27%): Agentic loop, multi-agent patterns, hooks
- Domain 2 (18%): Tool design, MCP integration, error handling  
- Domain 3 (20%): Claude Code configuration, rules, slash commands
- Domain 5 (15%): Context management, case facts, escalation criteria

*Domain 4 (Prompt Engineering & Structured Output) is covered in App 4 
of this certification project series.*

## Disclaimer

This project is built for personal CCA certification preparation only.
All data is fictional. No real insurance data, APIs, or systems are used.