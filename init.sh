#!/usr/bin/env bash
# init.sh — Environment verification and initialization for Tailr
#
# Run at the BEGINNING of a session and before declaring any task `DONE`.
# If it fails, the session must not proceed.
#
# Expected output: clear exit codes and blocks marked with [OK]/[WARN]/[FAIL].

set -u
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$1"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$1"; }
fail()  { printf "${RED}[FAIL]${NC}  %s\n" "$1"; }

EXIT_CODE=0

# Detect python command (python3 on Linux/macOS, python on Windows)
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  fail "python3/python is not installed"
  exit 1
fi

echo "── 1. Verifying Python environment ─────────────────────"

ok "$PY -> $($PY --version)"

PY_VERSION_OK=$($PY -c 'import sys; print(int(sys.version_info >= (3, 11)))')
if [ "$PY_VERSION_OK" != "1" ]; then
  fail "Python >= 3.11 is required (docgen service)"
  exit 1
fi
ok "Compatible Python version (>= 3.11)"

if [ -f "services/docgen/requirements.txt" ]; then
  ok "services/docgen/requirements.txt exists"
else
  fail "Missing services/docgen/requirements.txt"
  EXIT_CODE=1
fi

echo ""
echo "── 2. Verifying Node.js environment ────────────────────"

if ! command -v node >/dev/null 2>&1; then
  fail "node is not installed"
  EXIT_CODE=1
else
  ok "node -> $(node --version)"
fi

if ! command -v pnpm >/dev/null 2>&1; then
  fail "pnpm is not installed"
  EXIT_CODE=1
else
  ok "pnpm -> $(pnpm --version)"
fi

if [ -d "node_modules" ]; then
  ok "node_modules/ exists"
else
  warn "node_modules/ not found — run: pnpm install"
fi

if [ -f "package.json" ]; then
  ok "package.json exists"
else
  fail "Missing package.json"
  EXIT_CODE=1
fi

echo ""
echo "── 3. Verifying base harness files ─────────────────────"

for f in AGENTS.md feature_list.json progress/history.md \
         docs/architecture.md docs/conventions.md docs/verification.md \
         docs/PRD.md docs/technical_requirements.md docs/app_flow.md docs/backend_schema.md \
         README.md LICENSE; do
  if [ ! -f "$f" ]; then
    fail "Missing base file: $f"
    EXIT_CODE=1
  else
    ok "Exists $f"
  fi
done

# TASKS.md is the reference plan; accept it at the root or under docs/.
if [ -f "TASKS.md" ] || [ -f "docs/TASKS.md" ]; then
  ok "Exists TASKS.md (reference plan)"
else
  warn "TASKS.md not found at root or docs/ — the reference plan is missing"
fi

for f in agents/leader.md agents/implementer.md agents/reviewer.md; do
  if [ ! -f "$f" ]; then
    warn "Missing agent file: $f"
  else
    ok "Exists $f"
  fi
done

echo ""
echo "── 4. Ensuring progress/current.md ─────────────────────"

if [ ! -f "progress/current.md" ]; then
  cat > progress/current.md <<'EOF'
# Current session

> Live log. Blank this back to the template at session close.

## Feature

- `Feature in progress:` (none)
- `Started at:` (not started)
- `Plan:` (none)

## Notes

_(append as you work)_
EOF
  warn "Created progress/current.md from template"
else
  ok "progress/current.md exists"
fi

echo ""
echo "── 5. Validating feature_list.json ─────────────────────"

$PY - <<'PY'
import json
import sys

VALID = {"pending", "in_progress", "review", "done", "blocked"}
ACTIVE = {"in_progress", "review"}

try:
    data = json.load(open("feature_list.json", encoding="utf-8"))
    features = data["features"]

    active = [f for f in features if f.get("status") in ACTIVE]
    if len(active) > 1:
        keys = ", ".join(f.get("key", f.get("id")) for f in active)
        print(f"[FAIL]  {len(active)} features are in_progress/review (maximum 1): {keys}")
        sys.exit(1)

    for f in features:
        if f.get("status") not in VALID:
            print(f"[FAIL]  Invalid status in feature {f.get('key', f.get('id'))}: {f.get('status')}")
            sys.exit(1)
        if "acceptance" not in f or not f["acceptance"]:
            print(f"[FAIL]  Feature {f.get('key', f.get('id'))} has no acceptance criteria")
            sys.exit(1)

    print(f"[OK]    feature_list.json is valid ({len(features)} features)")
    for status in ("pending", "in_progress", "review", "done", "blocked"):
        n = sum(1 for f in features if f.get("status") == status)
        print(f"[OK]      {status}: {n}")
except Exception as e:
    print(f"[FAIL]  Invalid feature_list.json: {e}")
    sys.exit(1)
PY

if [ $? -ne 0 ]; then EXIT_CODE=1; fi

echo ""
echo "── 6. Running docgen tests (Python) ────────────────────"

if [ -d "services/docgen/tests" ]; then
  if (cd services/docgen && $PY -m pytest -q); then
    ok "All docgen tests pass"
  else
    fail "docgen tests are failing"
    EXIT_CODE=1
  fi
else
  warn "services/docgen/tests/ does not exist yet"
fi

echo ""
echo "── 7. Running frontend checks ──────────────────────────"

# A gate whose script does not exist yet (early project) is a warning, not a failure.
has_script() {
  node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts['$1'] ? 0 : 1)" 2>/dev/null
}

gate() {
  # gate <script-name> <human label>
  if ! has_script "$1"; then
    warn "package.json has no '$1' script yet — skipped"
    return 0
  fi
  if pnpm "$1" >/dev/null 2>&1; then
    ok "pnpm $1 passes ($2)"
  else
    fail "pnpm $1 fails ($2)"
    EXIT_CODE=1
  fi
}

if [ -d "node_modules" ]; then
  gate lint "ESLint"
  gate typecheck "TypeScript"
  gate build "production build"
  gate test "unit + contract tests"
  gate test:i18n "es/en locale parity"
  gate test:pipeline "pipeline smoke test"
else
  warn "Skipped frontend checks (node_modules/ missing)"
fi

echo ""
echo "── 8. Summary ──────────────────────────────────────────"

if [ $EXIT_CODE -eq 0 ]; then
  ok "Environment ready. You can start working."
else
  fail "Environment is NOT ready. Resolve the errors before proceeding."
fi

exit $EXIT_CODE
