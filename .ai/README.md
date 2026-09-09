# Local AI development workflow

This directory is the Git-tracked source of truth for local development issues.
Repository-wide engineering constraints remain in [`../AGENTS.md`](../AGENTS.md).

## Layout

- [`issues.md`](issues.md) is the issue index and records the sole active work unit.
- `issues/AI-NNNN-<slug>.md` contains one issue per file.
- `specs/AI-NNNN-<slug>.md` exists only for a phased issue and links back to it.

Create `issues/` and `specs/` when their first files are needed; empty directory
placeholders are intentionally not tracked.

## IDs and issue types

Use monotonically increasing IDs (`AI-0001`, `AI-0002`, ...). Never reuse an ID,
including after cancellation or deletion.

Classify every issue when it is recorded:

- `single`: one coherent outcome that can be implemented and verified without an
  intermediate measurement, training result, resource handoff, or user decision.
- `phased`: later work depends on an earlier measured result or decision, or the
  issue has multiple independently verifiable delivery stages. Code size alone
  does not make an issue phased.

A `single` issue keeps its scope and acceptance criteria in the issue file. A
`phased` issue must have a bidirectionally linked file under `specs/` whose phases
each define scope, non-scope, required inputs, deliverables, acceptance criteria,
verification, and dependencies.

If a `single` issue turns out to require phases, stop development and ask the user
to approve reclassification. Do not silently expand its scope.

## Status

Issue statuses are:

- `backlog`: recorded but not fully triaged.
- `needs-input`: waiting for user information or resources.
- `ready`: scoped and eligible for a read-only preflight; not authorized.
- `in-progress`: explicitly authorized and being developed.
- `blocked`: development cannot continue without an external change or input.
- `paused`: deliberately suspended by the user.
- `done`: all issue acceptance criteria are verified.
- `cancelled`: explicitly cancelled.

Phases use `pending`, `needs-input`, `ready`, `in-progress`, `blocked`, or `done`.
At most one issue and, for a phased issue, one phase may be `in-progress`.

## Required workflow

### 1. Record

Recording or editing backlog metadata is not development authorization. When the
user asks to record a requirement:

1. Inspect the relevant repository context without modifying product code.
2. Allocate the next ID and classify the issue as `single` or `phased`.
3. Create the issue file and add it to `issues.md`.
4. For a phased issue, create the spec and link issue and spec to each other.

An issue file records at least:

```markdown
# AI-NNNN: Title

- Type: single | phased
- Status: backlog
- Priority: P0 | P1 | P2 | P3
- Created: YYYY-MM-DD
- Spec: none | relative link

## Problem
## Desired behavior
## Non-goals
## Acceptance criteria
## Constraints
## Required resources
## Open questions
## References and evidence
## Dependencies
## Development record
```

### 2. Preflight

Before every development authorization, perform a read-only preflight for the
exact issue and, when phased, the exact next phase. Report:

- understood scope and non-scope;
- resources the user must provide, explicitly saying `none` when there are none;
- decisions or ambiguities still requiring confirmation;
- assumptions, affected areas, verification plan, and material risks;
- use of GPU, long training, external services, or real hardware.

If the user says "开始开发" or "start development" before a current preflight
exists, run the preflight first and wait. The first request does not bypass this
confirmation.

### 3. Authorize

Authorization must identify the issue and, for phased work, one phase, for
example `开始开发 AI-0002 P1`. It applies only to the preflighted scope. It
expires when that work unit finishes or its scope materially changes.

After authorization, set the work unit to `in-progress` and set `Active
Development` in `issues.md`. Never develop two issues concurrently. Other issues
may still be recorded, but not implemented.

### 4. Develop and verify

Make the smallest change that satisfies the authorized acceptance criteria. Do
not include adjacent cleanup or another issue. Preserve pre-existing user changes.
Use the verification required by `AGENTS.md`, escalating from focused tests to the
full CPU suite and, only when relevant and authorized, physics checks, the 64-env
five-iteration smoke test, long training, rollout evaluation, and official ONNX
export/inference.

Stop and return to preflight if a new resource, material decision, scope expansion,
worktree conflict, or invalidated spec assumption appears.

### 5. Finish one work unit

For a `single` issue, mark it `done` only after all acceptance criteria have been
verified. For a `phased` issue, complete only the authorized phase, record its
actual results, leave the issue open, and do not begin the next phase. Every phase
requires a fresh preflight and authorization.

Clear `Active Development` after completion, pause, cancellation, or a blocking
handoff. Switching issues requires an explicit user instruction.

Development records must distinguish checks actually run from checks not run.
Being present in this Git-tracked directory does not authorize creating a commit;
commit only when the user requests it.

## Phased spec format

```markdown
# AI-NNNN Spec: Title

- Issue: relative link
- Status: active
- Current phase: P1

## Goal
## Non-goals
## Constraints and invariants
## Overall approach

## Phases

### P1: Name

- Status: pending
- Scope:
- Non-scope:
- Deliverables:
- Required inputs:
- Acceptance criteria:
- Verification:
- Dependencies:

## Cross-phase risks
## Final acceptance criteria
## Decisions and measured results
```

## Concise reports

Registration:

```text
已登记 AI-NNNN：<标题>
类型：single | phased；状态：<状态>
Spec：无 | <路径>；尚未开始开发。
```

Preflight:

```text
预检：AI-NNNN / Pn
本次范围：<一句话>
需要你提供：无 | <资源>
待确认：无 | <问题>
验证：<检查>
风险：无 | <主要风险>
确认无误后，请回复：开始开发 AI-NNNN Pn
```

Completion:

```text
AI-NNNN [/ Pn] 已完成
结果：<一句话>
已验证：<检查>
未验证：无 | <原因>
下一阶段：无 | Pn（未授权、未开始）
```

Blocked:

```text
AI-NNNN [/ Pn] 已暂停
阻塞：<具体原因>
需要你提供/确认：<资源或决策>
未进入后续阶段。
```
