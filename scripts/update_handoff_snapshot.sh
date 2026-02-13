#!/usr/bin/env bash
set -euo pipefail

HANDOFF_PATH="todo/NEXT_MACHINE_HANDOFF.md"
PYTEST_PASSED=""

usage() {
  cat <<'EOF'
Usage:
  scripts/update_handoff_snapshot.sh [--pytest-passed N] [--file PATH]

Options:
  --pytest-passed N  Update the pytest validation line to "(N passed)".
  --file PATH        Override handoff file path (default: todo/NEXT_MACHINE_HANDOFF.md).
  --help             Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pytest-passed)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --pytest-passed" >&2
        exit 1
      fi
      PYTEST_PASSED="$2"
      shift 2
      ;;
    --file)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --file" >&2
        exit 1
      fi
      HANDOFF_PATH="$2"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$HANDOFF_PATH" ]]; then
  echo "Handoff file not found: $HANDOFF_PATH" >&2
  exit 1
fi

DATE_STR="$(date +%Y-%m-%d)"
BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
HEAD_HASH="$(git rev-parse HEAD)"
LAST_COMMIT="$(git show -s --format='%h %ci - %s' HEAD)"

if [[ -n "$(git status --short)" ]]; then
  WORKTREE_STATE="dirty"
else
  WORKTREE_STATE="clean"
fi

TMP_FILE="$(mktemp)"

awk \
  -v date_str="$DATE_STR" \
  -v branch_name="$BRANCH_NAME" \
  -v head_hash="$HEAD_HASH" \
  -v last_commit="$LAST_COMMIT" \
  -v worktree_state="$WORKTREE_STATE" \
  -v pytest_passed="$PYTEST_PASSED" \
  '
{
  if ($0 ~ /^- Date:/) {
    print "- Date: `" date_str "`"
    next
  }
  if ($0 ~ /^- Branch:/) {
    print "- Branch: `" branch_name "`"
    next
  }
  if ($0 ~ /^- HEAD:/) {
    print "- HEAD: `" head_hash "`"
    next
  }
  if ($0 ~ /^- Last commit:/) {
    print "- Last commit: `" last_commit "`"
    next
  }
  if ($0 ~ /^- Working tree at handoff creation:/) {
    print "- Working tree at handoff creation: " worktree_state
    next
  }
  if (pytest_passed != "" && $0 ~ /`PYTHONPATH=src \.\/\.venv313\/bin\/pytest` passes/) {
    print "  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`" pytest_passed " passed`)"
    next
  }
  print
}
' "$HANDOFF_PATH" > "$TMP_FILE"

mv "$TMP_FILE" "$HANDOFF_PATH"
echo "Updated snapshot fields in $HANDOFF_PATH"
