# AGENTS

## Scope

This file defines repository-specific working instructions for `compat-sentinel`.

## Agent requests: review vs edit

- When the user asks to review, verify, analyze, assess, report, or check,
  respond with read-only analysis only.
- Do not change files or implement fixes unless the user explicitly asks for
  edits, fixes, implementation, or an update.
- If analysis surfaces a problem, describe it and wait for direction rather
  than patching the tree unprompted.

## Start here

- `README.md` is the public contract: `sentinel(name, /, *, repr=None)`,
  matching PEP 661.
- On Python 3.15 and later, `compat_sentinel.sentinel` is `builtins.sentinel`.
  Earlier versions use `src/compat_sentinel/_sentinel.py`.
- Pickle identity comes from importing `__module__` and looking up `__name__`.
  There is no sentinel registry.

## Roll-build method

- When the user asks for a phased rollout using the roll-build method, start
  from a clean git tree and tag that point before implementation begins.
- Use the requested start tag name when one is given. If none is given, ask or
  use a clearly scoped phase-start tag name.
- An unqualified `roll-build` means: run all phases for that plan in sequence,
  committing and tagging each completed phase, and continue into the next phase
  without stopping unless the guardrails below require a pause.
- Run the roll-build in the current owning checkout and current branch. Do not
  create git worktrees, sibling checkouts, or parallel rollout branches unless
  the user explicitly asks for them in that request.
- Do not split phases or adjacent roll-build requests into parallel branches.
  If one roll-build has already produced commits, the next roll-build starts on
  top of those commits after they are integrated into the current branch.
- If the current branch is not the intended integration branch, stop and ask
  before creating or switching branches. Do not invent a branch/worktree strategy
  from the tag prefix.
- Implement one phase at a time.
- After a phase is complete, only commit and tag it if:
  - the phase goal is actually met
  - focused verification passes
  - the remaining ambiguities are minor and non-blocking
- If there are no more phases, or if confidence drops because of material
  ambiguity or instability, stop and wait instead of forcing the next phase.
- If work starts cycling on the same persistent bug or bug family, stop, report
  the cycle clearly, and ask for direction.

## When to push back on roll-build

- Push back when the next phase has too many unresolved ambiguities to produce a
  trustworthy checkpoint.
- Push back when the requested phase is too large or too coupled to complete
  safely as one checkpoint.
- Push back when implementation reveals facts that materially break the current
  design or plan assumptions.
- Push back when the resulting checkpoint would be misleadingly partial,
  unstable, or hard to recover from.

## Test-led semantics guardrail

- Do not change public semantics merely to make a test pass without updating the
  design/docs.
- If a red test implies a real semantic change rather than a bug fix or missing
  coverage, stop and update the design/docs before implementing the change.
- It is acceptable to tighten tests, fix assumptions, or fix correctness bugs
  that clearly match the current design intent.
- It is not acceptable to quietly redefine semantics to satisfy a convenient
  test expectation.

## Test commands

- Focused tests: `uv run --with pytest pytest <test-path> -q`
- Full suite: `uv run --with pytest pytest -q`

<!-- gearu:agents:start -->
## Releases

- This repository uses [Gearu](https://owebeeone.github.io/gearu/) for release
  preparation.
- Read `RELEASE.md` before planning or performing a release.
- `gearu plan VERSION` and `gearu plan --bump LEVEL` are read-only. Do not run
  `gearu release`, push a release tag, or create a GitHub Release unless the
  user explicitly requests it.
- Never move or reuse a release tag. Correct released content with a new version.
- Never publish directly to PyPI, crates.io, or npm from a local checkout.
  Registry publication belongs in the repository's release workflow.
<!-- gearu:agents:end -->
