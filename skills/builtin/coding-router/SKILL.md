---
name: coding-router
description: Route coding tasks between local tools and external coding CLI with safety checks
is_builtin: true
---

# Coding Router Skill

## Purpose

This skill helps decide whether to:
1. Solve coding tasks directly with local tools, or
2. Delegate to the external coding CLI via `run_external_coder`.

## Decision Rules

Prefer **local tools** when:
- The change is small and file-scoped.
- You already have enough context.
- Fast iteration with direct edits is best.

Prefer **external coder** when:
- The request is broad, multi-file, or architecture-level.
- The user explicitly asks to use Gemini CLI / Codex.
- You need specialized coding-agent behavior.

## Workflow

1. Briefly explain your plan.
2. Gather minimal context (read/search files).
3. Decide local vs delegated execution.
4. If delegated, call `run_external_coder` with a precise `task` and optional `context`.
5. Validate results (tests/lint/build if relevant).
6. Summarize what changed, risks, and next steps.

## Safety

- Respect current approval policy and confirmation flow.
- Never expose secrets in task/context payloads.
- Keep delegated tasks scoped to the current workspace.

## Delegation Prompt Quality

When calling `run_external_coder`, include:
- Goal and constraints
- Relevant files/paths
- Acceptance criteria
- Required validation commands

Example task structure:
- Objective: Fix failing tests in module X
- Constraints: Keep public API unchanged
- Validation: `pytest tests/test_x.py -q`
