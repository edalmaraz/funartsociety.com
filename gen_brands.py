"""Deterministic brand-page generator: brands.json -> brands/<key>/index.html.

Re-runnable; pages are fully overwritten each run. Future tooling adds
products by replacing the <!-- products:<key> --> marker block.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} — Fun Art Society</title>
<meta name="description" content="{name}: {tagline_attr} A Fun Art Society studio.">
<link rel="stylesheet" href="../../assets/site.css">
<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">
<style>:root {{ --accent: {accent}; }}</style>
</head>
<body>
<header class="top">
  <a class="wordmark" href="../../">🎨 Fun Art Society</a>
  <nav><a href="../../#brands">Studios</a> <a href="../../#about">About</a></nav>
</header>
<main>
  <section class="brand-hero">
    <span class="glyph" aria-hidden="true">{glyph}</span>
    <h1>{name}</h1>
    <p class="tagline">{tagline}</p>
  </section>
  <section class="panel">
    <h2>What we make</h2>
    <p>{makes}</p>
  </section>
  <section class="panel" id="shop">
    <h2>Shop</h2>
    <!-- products:{key} -->
    <p class="status"><span class="dot" aria-hidden="true"></span>{status}</p>
    <p class="muted">Our goods will be sold through Gumroad — simple checkout, instant downloads.</p>
    <!-- /products:{key} -->
  </section>
  <section class="panel">
    <h2>More from the society</h2>
    <p class="siblings">{siblings}</p>
  </section>
</main>
<footer>
  <p>{name} is a studio of <a href="../../">Fun Art Society</a>.</p>
</footer>
</body>
</html>
"""


def build() -> int:
    brands = json.loads((ROOT / "brands.json").read_text(encoding="utf-8"))["brands"]
    for b in brands:
        siblings = " · ".join(
            f'<a href="../{o["key"]}/">{o["glyph"]} {html.escape(o["name"])}</a>'
            for o in brands if o["key"] != b["key"]
        )
        page = TEMPLATE.format(
            key=b["key"],
            name=html.escape(b["name"]),
            tagline=html.escape(b["tagline"]),
            tagline_attr=html.escape(b["tagline"], quote=True),
            makes=html.escape(b["makes"]),
            status=html.escape(b["status"]),
            glyph=b["glyph"],
            accent=b["accent"],
            siblings=siblings,
        )
        out = ROOT / "brands" / b["key"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8", newline="\n")
        print(f"wrote {out.relative_to(ROOT)}")
    return len(brands)


if __name__ == "__main__":
    print(f"{build()} brand pages generated")
