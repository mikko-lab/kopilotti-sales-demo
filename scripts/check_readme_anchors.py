"""Regression check: fail if README anchors that external documents link to disappear.

docs/kopilotti-sales-overview-{fi,en}.md and the published A4 PDFs both link to
https://github.com/mikko-lab/kopilotti-sales-demo#current-scope. Since the
Finnish README swap, that fragment is not GitHub's auto-generated heading slug
(GitHub would slug "# Tuotannon tila" as #tuotannon-tila), so README.md carries
an explicit `<a id="current-scope"></a>` anchor instead. This script fails
loudly if that anchor - or README.en.md's own "Current scope" heading, which
its internal #current-scope link depends on - goes missing again.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHECKS = [
    (
        ROOT / "README.md",
        r'<a\s+id="current-scope"\s*>\s*</a>',
        'README.md is missing the explicit <a id="current-scope"></a> anchor. '
        "docs/kopilotti-sales-overview-{fi,en}.md and the published A4 PDFs link "
        "to https://github.com/mikko-lab/kopilotti-sales-demo#current-scope; "
        "without this anchor that link silently lands at the top of the page.",
    ),
    (
        ROOT / "README.en.md",
        r"^##\s+Current scope\s*$",
        'README.en.md is missing its own "## Current scope" heading. '
        "README.en.md's internal [Current scope](#current-scope) link depends "
        "on GitHub's auto-generated slug for this exact heading text.",
    ),
]


def main():
    failures = []
    for path, pattern, message in CHECKS:
        if not path.exists():
            failures.append(f"{path.name}: file not found")
            continue
        text = path.read_text(encoding="utf-8")
        if not re.search(pattern, text, re.MULTILINE):
            failures.append(f"{path.name}: {message}")

    if failures:
        print("README anchor check FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("README anchor check OK: current-scope anchors present in both READMEs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
