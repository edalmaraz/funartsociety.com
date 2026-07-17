"""Static QA gate for the Fun Art Society site.

Run: python verify_site.py   (exit 0 = ship, exit 1 = blocked)

Checks every deployable page for structural basics, verifies all internal
links resolve, forbids root-absolute URLs (breaks under github.io subpath),
cross-checks brands.json against generated pages, and scans for strings
that must never appear on the public site.
"""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIP_DIRS = {".git", "docs", "__pycache__", ".github"}
TEXT_EXT = {".html", ".css", ".svg", ".txt", ".json", ".xml"}

# Never on the public site. 'agent' exempted in robots.txt (User-agent:).
FORBIDDEN = [
    "myrig", "paperclip", "nexus", "authelia", "agent", "paused",
    "localhost", "127.0.0.1", "conductor", "warden", "heartbeat",
    "edalmaraz@", "users.noreply",
]
ROBOTS_EXEMPT = {"agent"}

EXPECTED_CNAME = "funartsociety.com"


class PageScan(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.h1_count = 0
        self.meta_description = ""
        self.has_viewport = False
        self.lang = ""
        self.refs: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        a = dict(attrs)
        if tag == "html":
            self.lang = (a.get("lang") or "").strip()
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta":
            name = (a.get("name") or "").lower()
            if name == "description":
                self.meta_description = (a.get("content") or "").strip()
            elif name == "viewport":
                self.has_viewport = True
        for attr in ("href", "src"):
            if a.get(attr):
                self.refs.append(a[attr])

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False


def deployable_files() -> list[Path]:
    out = []
    for p in ROOT.rglob("*"):
        if p.is_dir() or any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix in TEXT_EXT or p.name == "CNAME":
            if p.suffix == ".py":
                continue
            out.append(p)
    return out


def check_link(page: Path, ref: str, errors: list[str]) -> None:
    ref = ref.split("#", 1)[0].split("?", 1)[0]
    if not ref or ref.startswith(("http://", "https://", "mailto:", "data:")):
        return
    if ref.startswith("/"):
        errors.append(f"{page.relative_to(ROOT)}: root-absolute URL '{ref}' "
                      "(breaks under github.io project subpath — use relative)")
        return
    target = (page.parent / ref).resolve()
    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        errors.append(f"{page.relative_to(ROOT)}: broken link '{ref}'")


def main() -> int:
    errors: list[str] = []
    pages = [p for p in deployable_files() if p.suffix == ".html"]
    if not pages:
        errors.append("no HTML pages found — site not built")

    for page in pages:
        scan = PageScan()
        scan.feed(page.read_text(encoding="utf-8"))
        rel = page.relative_to(ROOT)
        if not scan.title.strip():
            errors.append(f"{rel}: missing <title>")
        if scan.h1_count != 1:
            errors.append(f"{rel}: expected exactly one <h1>, found {scan.h1_count}")
        if not scan.meta_description:
            errors.append(f"{rel}: missing meta description")
        if not scan.has_viewport:
            errors.append(f"{rel}: missing viewport meta")
        if scan.lang != "en":
            errors.append(f"{rel}: <html lang> is '{scan.lang}', want 'en'")
        for ref in scan.refs:
            check_link(page, ref, errors)

    # brands.json <-> pages <-> index cross-check
    brands_file = ROOT / "brands.json"
    if brands_file.exists():
        brands = json.loads(brands_file.read_text(encoding="utf-8"))["brands"]
        index = ROOT / "index.html"
        index_html = index.read_text(encoding="utf-8") if index.exists() else ""
        for b in brands:
            key = b["key"]
            if not (ROOT / "brands" / key / "index.html").exists():
                errors.append(f"brands.json: no generated page for '{key}'")
            if f"brands/{key}/" not in index_html:
                errors.append(f"index.html: does not link brand '{key}'")
        page_keys = {p.parent.name for p in (ROOT / "brands").glob("*/index.html")} \
            if (ROOT / "brands").exists() else set()
        for orphan in page_keys - {b["key"] for b in brands}:
            errors.append(f"brands/{orphan}/: page has no brands.json entry")
    else:
        errors.append("brands.json missing")

    # forbidden strings
    for f in deployable_files():
        low = f.read_text(encoding="utf-8", errors="replace").lower()
        for tok in FORBIDDEN:
            if f.name == "robots.txt" and tok in ROBOTS_EXEMPT:
                continue
            if tok in low:
                errors.append(f"{f.relative_to(ROOT)}: forbidden string '{tok}'")

    cname = ROOT / "CNAME"
    if cname.exists() and cname.read_text(encoding="utf-8").strip() != EXPECTED_CNAME:
        errors.append(f"CNAME: contents != '{EXPECTED_CNAME}'")

    if errors:
        print(f"GATE: FAIL ({len(errors)})")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"GATE: PASS ({len(pages)} pages, all checks green)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
