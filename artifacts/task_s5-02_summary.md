# Task Summary: S5-02 — Add Path-Only Content Invariant Check

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-02

## Summary of Work
Built a deterministic path-only content invariant checker at
`scripts/s5_02_path_invariant.py`. The script reads the baseline SHA-256 manifest
(produced by S5-01) and a current manifest generated from the filesystem, maps
every old file path to its expected Sprint 5 target path, and reports violations
when content changes fall outside the explicit allowlist.

The checker distinguishes between:
- **Violations:** content changes in non-allowlisted files, collisions (two old
  files mapping to the same target), and missing source files.
- **Warnings:** files present in the current tree that weren't in the baseline
  (new Sprint 5 artifacts, documentation assets, etc.).

Currently reports **0 violations and 9 warnings** (all warnings are benign new
Sprint 5 artifacts and documentation files). This serves as the pre-move
baseline — after each move task (S5-04 through S5-11), rerunning this checker
will flag any content changes that exceed the refactoring scope.

## Files Created
- [scripts/s5_02_path_invariant.py](scripts/s5_02_path_invariant.py) — invariant checker script
- [artifacts/s5-02-invariant-report.txt](artifacts/s5-02-invariant-report.txt) — current report output

## Testing
- **Status:** Verified (0 violations)
- **Execution Command:** `uv run python scripts/s5_02_path_invariant.py --baseline artifacts/s5-01-baseline-manifest.sha256 --current . --output artifacts/s5-02-invariant-report.txt`

## Additional Notes
- The checker maps paths per Sprint 5's three directory moves: `agent_app/` →
  `apps/agent_app/`, `mcp_server/` → `mcp_facade/`, `chat_ui/` → `apps/chat_ui/`.
- Content-change allowlist covers: import path updates, module command changes in
  YAML, source_code_path fields, working-directory references, test fixture paths,
  and documentation links.
- Build artifacts (dist/, node_modules/, playwright-report/, etc.) are excluded
  from the MISSING check.
- Run this checker after every move task (S5-04 through S5-11) to verify scope
  compliance.
