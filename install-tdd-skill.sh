#!/usr/bin/env bash
set -euo pipefail

# install-tdd-skill.sh
# Run from the root of a repo. Installs the TDD skill for:
#   - Windsurf: .windsurf/skills/tdd/
#   - Codex:    .agents/skills/tdd/
#
# Also creates/updates AGENTS.md to make strict TDD the default workflow.

SKILL_REPO="https://github.com/mattpocock/skills.git"
SKILL_SUBDIR="tdd"

ROOT="$(pwd)"
if command -v git >/dev/null 2>&1 && git rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT="$(git rev-parse --show-toplevel)"
fi

WS_DEST="$ROOT/.windsurf/skills/tdd"
CODEX_DEST="$ROOT/.agents/skills/tdd"
AGENTS_FILE="$ROOT/AGENTS.md"

TS="$(date +%Y%m%d%H%M%S)"
TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

say() { printf "%s\n" "$*"; }

need_cmd() {
  local c="$1"
  command -v "$c" >/dev/null 2>&1 || {
    echo "Error: required command not found: $c" >&2
    exit 1
  }
}

backup_if_exists() {
  local path="$1"
  if [[ -e "$path" ]]; then
    local bak="${path}.bak-${TS}"
    say "Backing up existing: $path -> $bak"
    mv "$path" "$bak"
  fi
}

sync_dir() {
  local src="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"
  backup_if_exists "$dest"
  mkdir -p "$dest"

  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$src/" "$dest/"
  else
    # macOS always has cp; use it if rsync isn't available.
    cp -R "$src/." "$dest/"
  fi
}

# Normalizes a one-line frontmatter into the standard:
# ---
# name: ...
# description: ...
# ---
normalize_skill_md() {
  local skill_md="$1"
  [[ -f "$skill_md" ]] || return 0

  # Use python for robust parsing/rewriting.
  python3 - <<'PY' "$skill_md"
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
txt = p.read_text(encoding="utf-8")

# Detect the "one-line" frontmatter used by this particular skill.
m = re.match(r"^\s*---\s*name:\s*([^\s]+)\s*description:\s*(.*?)\s*---\s*", txt, re.S)
if not m:
    # Already looks fine (or at least not the one-line pattern).
    sys.exit(0)

name = m.group(1).strip()
desc = m.group(2).strip()
# Collapse internal whitespace to keep description single-line YAML-safe.
desc = re.sub(r"\s+", " ", desc).strip()

rest = txt[m.end():]
new = f"---\nname: {name}\ndescription: {desc}\n---\n{rest.lstrip()}"
p.write_text(new, encoding="utf-8")
PY
}

# Make description broad so both tools will pick it for essentially any code-change task.
set_broad_description() {
  local skill_md="$1"
  [[ -f "$skill_md" ]] || return 0

  python3 - <<'PY' "$skill_md"
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
txt = p.read_text(encoding="utf-8")

broad = ("Enforce strict red-green-refactor TDD for any production code change "
         "(features, bug fixes, refactors). Prefer integration-style tests through "
         "public interfaces; avoid mocking internals unless necessary at boundaries.")

def repl(m):
    return f"{m.group(1)}description: {broad}\n"

# Replace description only within the first YAML frontmatter block.
# Assumes a normalized frontmatter exists at top of file.
txt2 = re.sub(r"(?s)\A(---\n.*?\n)(description:\s*.*?\n)", lambda m: repl(m), txt, count=1)
# If the above didn't match due to formatting differences, try a simpler line-based replace.
if txt2 == txt:
    txt2 = re.sub(r"(?m)^(description:\s*).*$", lambda m: m.group(1)+broad, txt, count=1)

p.write_text(txt2, encoding="utf-8")
PY
}

write_openai_yaml() {
  local dest="$1"
  mkdir -p "$dest/agents"
  cat >"$dest/agents/openai.yaml" <<'YAML'
interface:
  display_name: "TDD"
  short_description: "Strict red-green-refactor workflow"
  default_prompt: |
    Use strict TDD (red → green → refactor). Work in vertical slices:
    - Write ONE failing test for ONE behavior (verify it fails for the right reason).
    - Implement the minimum code to pass.
    - Refactor only when tests are green.
    Prefer integration-style tests through public interfaces; avoid mocking internals unless needed at boundaries.
policy:
  allow_implicit_invocation: true
YAML
}

install_skill() {
  local dest="$1"
  local src_root="$2"

  sync_dir "$src_root/$SKILL_SUBDIR" "$dest"
  normalize_skill_md "$dest/SKILL.md"
  set_broad_description "$dest/SKILL.md"
  write_openai_yaml "$dest"
}

update_agents_md() {
  local file="$1"
  local block="$TMP/agents_block.md"

  cat >"$block" <<'EOF'
<!-- BEGIN TDD DEFAULT (managed by install-tdd-skill.sh) -->
## Default workflow: strict TDD (red → green → refactor)

When implementing, fixing, or refactoring **production code** in this repository:

- **Follow the `tdd` skill as the governing procedure.**
  - If skills are available, prefer invoking it (`@tdd` in Windsurf / `$tdd` in Codex) when doing code changes.
  - If multiple skills apply, `tdd` takes precedence for any task that changes runtime behavior.
- Work in **vertical slices**: one failing test → minimal code to pass → repeat.
- Prefer **integration-style tests** through **public interfaces**; avoid mocking internals unless strictly necessary at boundaries.
- Do **not** refactor while tests are failing; get back to green first.
- Run the relevant tests after each small step; stop immediately on failures and fix before continuing.

<!-- END TDD DEFAULT (managed by install-tdd-skill.sh) -->
EOF

  if [[ ! -f "$file" ]]; then
    cp "$block" "$file"
    return 0
  fi

  # Replace existing managed block if present; otherwise append.
  if grep -Fq "<!-- BEGIN TDD DEFAULT (managed by install-tdd-skill.sh) -->" "$file"; then
    awk -v blockfile="$block" '
      BEGIN {inblock=0}
      $0=="<!-- BEGIN TDD DEFAULT (managed by install-tdd-skill.sh) -->" {
        while ((getline line < blockfile) > 0) print line
        close(blockfile)
        inblock=1
        next
      }
      $0=="<!-- END TDD DEFAULT (managed by install-tdd-skill.sh) -->" {
        inblock=0
        next
      }
      inblock==0 { print }
    ' "$file" >"$file.tmp" && mv "$file.tmp" "$file"
  else
    printf "\n" >>"$file"
    cat "$block" >>"$file"
    printf "\n" >>"$file"
  fi
}

main() {
  need_cmd mktemp
  need_cmd python3

  say "Repo root: $ROOT"
  say "Fetching skill source from: $SKILL_REPO"

  SRC="$TMP/skills"
  if command -v git >/dev/null 2>&1; then
    git clone --depth 1 --single-branch "$SKILL_REPO" "$SRC" >/dev/null
  else
    need_cmd curl
    need_cmd tar
    curl -fsSL "https://codeload.github.com/mattpocock/skills/tar.gz/refs/heads/main" \
      | tar -xz -C "$TMP"
    SRC="$(find "$TMP" -maxdepth 1 -type d -name "skills-*" | head -n 1)"
    [[ -n "$SRC" ]] || { echo "Error: could not unpack skills archive" >&2; exit 1; }
  fi

  [[ -d "$SRC/$SKILL_SUBDIR" ]] || { echo "Error: $SKILL_SUBDIR not found in fetched repo" >&2; exit 1; }

  say "Installing Windsurf skill -> $WS_DEST"
  install_skill "$WS_DEST" "$SRC"

  say "Installing Codex skill -> $CODEX_DEST"
  install_skill "$CODEX_DEST" "$SRC"

  say "Updating project instructions -> $AGENTS_FILE"
  update_agents_md "$AGENTS_FILE"

  say ""
  say "Done."
  say "Next steps:"
  say "  - Commit these to your repo if you want teammates to inherit defaults:"
  say "      .windsurf/skills/tdd/"
  say "      .agents/skills/tdd/"
  say "      AGENTS.md"
  say "  - If the skill doesn't appear immediately in an app, restart the app/session."
}

main "$@"
