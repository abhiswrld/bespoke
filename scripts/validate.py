"""
Schema validator for bespoke master resumes.

Makes sure master/resume.yaml is well-formed before any downstream tool
(JD matcher, gap report, .tex emitter) tries to read it.
Fail fast, fail loud.

Usage:
    uv run --with pyyaml scripts/validate.py master/resume.yaml
"""

import sys
from pathlib import Path

import yaml

# Sections every master resume must define. Certifications is optional,
# so it's deliberately not in here.
REQUIRED_TOP_LEVEL = ["contact", "education", "skills", "projects", "experience"]


def validate(path: str) -> None:
    """Load a resume YAML file and exit non-zero if anything is wrong."""
    file = Path(path)
    if not file.exists():
        # sys.exit(str) prints to stderr and exits 1 — standard pattern
        # for "bad usage" in small CLI scripts.
        sys.exit(f"✗ file not found: {path}")

    # safe_load (vs. plain load) refuses to execute arbitrary Python tags,
    # which matters if we ever handle YAML we didn't write ourselves.
    try:
        data = yaml.safe_load(file.read_text())
    except yaml.YAMLError as exc:
        # A raw ScannerError dumps a 30-line traceback, which is useless
        # when the actual problem is a missing quote. PyYAML's own error
        # message already points at the offending line and column.
        sys.exit(f"✗ {path} is not valid YAML:\n  {exc}")

    errors = []

    # --- top-level structure -------------------------------------------------
    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"missing top-level key: {key}")

    # --- bullets -------------------------------------------------------------
    # Walk every bullet in projects + experience. Bullet ids will power the
    # diff-approval UI later, so duplicates or missing ids would silently
    # corrupt that — catch them here, at the source.
    ids: list[str | None] = []
    for section in ("projects", "experience"):
        for entry in data.get(section, []):
            # projects are labeled by `name`, experience by `role` —
            # this is just so error messages name the right entry.
            label = entry.get("name") or entry.get("role") or "?"
            bullets = entry.get("bullets", [])
            if not bullets:
                errors.append(f"{section}/{label}: has no bullets")
            for bullet in bullets:
                if not bullet.get("id"):
                    errors.append(f"{section}/{label}: bullet missing an id")
                if not bullet.get("text"):
                    errors.append(f"{section}/{label}: bullet missing text")
                ids.append(bullet.get("id"))

    # Keep only the ids that show up more than once.
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        errors.append(f"duplicate bullet ids: {duplicates}")

    # --- report ---------------------------------------------------------------
    if errors:
        print(f"✗ {path} has {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    n_projects = len(data.get("projects", []))
    n_experience = len(data.get("experience", []))
    print(f"✓ {path} is valid — {len(ids)} bullets "
          f"across {n_projects} projects and {n_experience} experiences")


if __name__ == "__main__":
    # Take the path as argv[1], fall back to the default so a bare
    # `validate.py` run just checks the real master file.
    validate(sys.argv[1] if len(sys.argv) > 1 else "master/resume.yaml")