# Implement Ticket (TDD)

Implement ticket **$ARGUMENTS** following strict TDD methodology with specialized subagents.

You MUST use the **Agent tool** to invoke each subagent by name. Do not attempt to do the subagent's work in the main context.

---

## Phase 1: Planning

Use the **Agent tool** to invoke the `ticket-planner` subagent with this prompt:

```
Analyze and plan the implementation of ticket $ARGUMENTS. Read the ticket from docs/tickets/ (glob for $ARGUMENTS-*.md), check docs/infra-gaps.md for gaps related to ticket $ARGUMENTS, and scan existing code in backend/app/ and backend/tests/. Produce the full structured implementation plan in the format defined in your system prompt.
```

When the planner returns the plan, present it to the user.

**STOP HERE.** Ask the user: "Do you approve this plan? (yes / suggest changes)". Do NOT proceed until the user approves.

---

## Phase 2: Setup

After approval, in the **main context** (no subagent):

1. Create and checkout branch: `feature/ticket-$ARGUMENTS-<slug>` (derive slug from ticket title, lowercase, hyphenated)
2. Resolve infrastructure gaps from the plan:
   - Add missing env vars to `.env.example`, `.env`, `docker-compose.yml`
   - Add missing Python deps with `uv add <package>`
   - Add/update Docker services if needed
3. If infra gaps were resolved, commit: `chore(ticket-$ARGUMENTS): resolve infrastructure gaps`

---

## Phase 3: TDD Implementation

Use the **Agent tool** to invoke the `tdd-implementer` subagent with this prompt:

```
Execute the following approved implementation plan. Work layer by layer (domain → model+migration → repository → service → schema → router), implementing all layers first. Then write endpoint integration tests at the end. Do NOT write unit tests for individual layers — only endpoint tests that exercise the full stack.

Here is the approved plan:

[PASTE THE FULL APPROVED PLAN HERE]
```

After the implementer finishes, make **granular conventional commits** in the main context:
- `feat(ticket-$ARGUMENTS): add <entity> domain layer` (domain entities + repository interface)
- `feat(ticket-$ARGUMENTS): add database migration` (models + alembic migration)
- `feat(ticket-$ARGUMENTS): add <entity> repository` (repository implementation)
- `feat(ticket-$ARGUMENTS): add <entity> service layer` (service implementation)
- `feat(ticket-$ARGUMENTS): add <entity> API endpoints` (schemas + router)
- `test(ticket-$ARGUMENTS): add endpoint integration tests` (all tests in a single commit)

Use `git add` per-file or per-directory to split changes into logical commits.

---

## Phase 4: Verification

Use the **Agent tool** to invoke the `code-review-verifier` subagent with this prompt:

```
Verify the implementation of ticket $ARGUMENTS. Run the full verification pipeline: tests with coverage, ruff linting, acceptance criteria check against the ticket in docs/tickets/, and convention compliance. Produce the structured verification report.
```

If the reviewer reports issues:
- **Missing endpoint test coverage**: use the `tdd-implementer` subagent to add endpoint tests
- **Lint issues**: fix in main context, commit: `style(ticket-$ARGUMENTS): fix linting issues`
- **Failing tests**: use the `tdd-implementer` subagent to fix
- **Re-verify** after fixes by invoking `code-review-verifier` again

Once verification passes:
- Mark resolved infra gaps as done in `docs/infra-gaps.md`
- Commit: `docs(ticket-$ARGUMENTS): mark infra gaps as resolved`

---

## Phase 5: PR

In the **main context** (no subagent):

1. Push the branch: `git push -u origin feature/ticket-$ARGUMENTS-<slug>`
2. Create PR to `main` using `gh pr create` with this format:

**Title:** `feat(ticket-$ARGUMENTS): <ticket title>`

**Body:**
```
## Summary
<brief description of what was implemented>

## Changes
- List of key changes by layer

## Test Coverage
- X tests added
- Coverage: XX% on new files

## Acceptance Criteria
- [x] criteria 1 (from ticket)
- [x] criteria 2
- ...
```

---

## Orchestration Summary

| Phase | Actor | Subagent |
|-------|-------|----------|
| 1. Plan | Agent tool | `ticket-planner` |
| Approval | **User** | — |
| 2. Setup | Main context | — |
| 3. TDD | Agent tool | `tdd-implementer` |
| 3→4. Commits | Main context | — |
| 4. Verify | Agent tool | `code-review-verifier` |
| 4. Fix (if needed) | Agent tool | `tdd-implementer` |
| 5. PR | Main context | — |

## Critical Rules

- Only write endpoint integration tests — NO unit tests for domain, repository, or service layers
- NEVER commit code that doesn't pass tests
- Follow ALL conventions from CLAUDE.md without exception
- Use `uv` for Python deps, never pip
- All SQLAlchemy code must be async
- Always use the Agent tool to invoke subagents — do not inline their work
