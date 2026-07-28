# Napkin Runbook

## Curation Rules

- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Execution & Validation (Highest Priority)

1. **[2026-07-22] Build and matrix operate only on committed `HEAD`**
   Do instead: commit a clean candidate before running `scripts/run_ci_matrix.ps1` or the distribution builder.
2. **[2026-07-22] Required release gate spans Python 3.11-3.14**
   Do instead: run lock, `pip check`, Ruff, Black, mypy, pytest, healthcheck, Docker matrix and ZIP verification before promotion.
3. **[2026-07-22] Tests must remain deterministic and offline**
   Do instead: mock Yahoo/market data and use temporary SQLite paths; keep broker access absent.
4. **[2026-07-22] A successful PR still needs post-merge CI**
   Do instead: wait for the four-version push workflow on `develop` after merging a work PR.
5. **[2026-07-28] Rebase promotion can split `main` and `develop` ancestry**
   Do instead: after `develop -> main`, verify `main` is an ancestor of `develop`; before another promotion, use the documented backed-up realignment procedure with explicit approval if ancestry diverged.

## Shell & Command Reliability

1. **[2026-07-22] User requires PowerShell executables**
   Do instead: provide and run PowerShell-compatible commands, never Bash-only snippets.
2. **[2026-07-22] Sandbox may fail with `CryptUnprotectData`**
   Do instead: retry the same scoped PowerShell command with approved escalation; do not reinterpret it as a project failure.
3. **[2026-07-22] Git and GitHub CLI may be missing from escalated `PATH`**
   Do instead: use `C:\Program Files\Git\cmd\git.exe`, `C:\Program Files\GitHub CLI\gh.exe`, and prepend Git cmd to the child `PATH` for `gh`.
4. **[2026-07-22] Native `apply_patch` can inherit the DPAPI failure**
   Do instead: validate and apply a UTF-8 unified diff through `git apply --check` and `git apply` only when the patch tool is unavailable.
5. **[2026-07-22] `sqlite3.Connection` context manager does not close**
   Do instead: wrap connections with `contextlib.closing(...), connection` to avoid Windows locks and `ResourceWarning`.

## Domain Behavior Guardrails

1. **[2026-07-22] Product is paper-only**
   Do instead: keep all orders local and simulated; require a separate approved design for any broker or live mode.
2. **[2026-07-22] Risk data must use aligned consecutive returns**
   Do instead: drop incomplete observations and fail with insufficient history; never forward-fill prices or invent zero returns.
3. **[2026-07-22] Paper mutations are atomic and fail closed**
   Do instead: use `BEGIN IMMEDIATE`, require affected rows/order IDs, and roll back cash, positions, orders and snapshots together.
4. **[2026-07-22] Hidden Streamlit tabs must stay lazy**
   Do instead: preserve `on_change="rerun"`, guard all 11 tabs with `tab.open`, and keep the regression test.
5. **[2026-07-22] Version has one canonical source**
   Do instead: change `pyproject.toml`; let installed metadata feed package, configuration, UI and healthcheck.

## User Directives

1. **[2026-07-22] Never advance irreversible release state implicitly**
   Do instead: ask explicitly before merging `main`, creating a tag, publishing a release or deploying.
2. **[2026-07-22] Reduce loops and token consumption**
   Do instead: read `PROJECT_MEMORY.md`, verify only dynamic deltas, and report changes rather than repeating the full audit.
3. **[2026-07-22] Preserve recoverability**
   Do instead: use branches, PRs and revertable commits; do not delete legacy or user files as cleanup.
