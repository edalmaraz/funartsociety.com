"""Deterministic brand-page generator: brands.json -> brands/<key>/index.html.

Club Edition templates. Re-runnable; pages are fully overwritten each run.
Future tooling adds products by replacing the <!-- products:<key> --> block.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,'
    'SOFT,WONK@0,9..144,300..900,0..100,0..1;1,9..144,300..900,0..100,0..1&display=swap" '
    'rel="stylesheet">'
)

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} — Fun Art Society</title>
<meta name="description" content="{name}, {no_attr} of the Fun Art Society: {tagline_attr}">
{fonts}
<link rel="stylesheet" href="../../assets/site.css">
<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">
<style>:root {{ --a: {accent}; }}</style>
</head>
<body>
<header class="top">
  <a class="wordmark" href="../../">Fun Art Society</a>
  <span class="label mastnote">{room} · Studio {no}</span>
  <nav class="label"><a href="../../#studios">Studios</a> <a href="../../#about">About</a></nav>
</header>
<main>
  <section class="brand-hero">
    <svg class="mark" viewBox="0 0 56 56" fill="none" stroke="{accent}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" aria-hidden="true">{mark}</svg>
    <div class="no">{no} — {room}</div>
    <h1>{name}</h1>
    <p class="tagline">{tagline}</p>
  </section>
  <section class="panel">
    <h2>What we make</h2>
    <p>{makes}</p>
  </section>
  <section class="panel" id="shop">
    <h2>The counter</h2>
    <!-- products:{key} -->
    <p class="status"><span class="dot" aria-hidden="true"></span>{status}</p>
    {counter}
    <!-- /products:{key} -->
  </section>
  <section class="panel">
    <h2>Elsewhere in the society</h2>
    <p class="siblings">{siblings}</p>
  </section>
</main>
<footer>
  <span class="label">Est. 2026</span>
  <span class="label">{name} is Studio {no} of <a href="../../">Fun Art Society</a></span>
  <span class="label">funartsociety.com</span>
</footer>
</body>
</html>
"""


CARD = """      <li class="card{featured}" style="--a:{accent}">
        <div class="inner">
          <svg class="mark" viewBox="0 0 56 56" fill="none" stroke="{accent}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" aria-hidden="true">{mark}</svg>
          <div>
            <div class="no">{no} — {room}{open_note}</div>
            <h3><a class="enterless" href="brands/{key}/" style="color:inherit;text-decoration:none">{name}</a></h3>
            <div class="tag">{tagline}</div>
            <p>{makes}</p>
            <a class="enter" href="brands/{key}/">Enter {room_short}</a>
          </div>
        </div>
      </li>"""


def inject_index(brands: list) -> None:
    index = ROOT / "index.html"
    src = index.read_text(encoding="utf-8")
    start, end = "<!-- studios:start -->", "<!-- studios:end -->"
    if start not in src or end not in src:
        raise SystemExit("index.html is missing the studios markers")
    cards = "\n".join(
        CARD.format(
            featured=" featured" if b.get("featured") else "",
            accent=b["accent"],
            mark=b["mark"],
            no=b["_no"],
            room=html.escape(b["room"]),
            room_short=html.escape(b["room"].split()[-1].lower()),
            key=b["key"],
            name=html.escape(b["name"]),
            tagline=html.escape(b["tagline"]),
            makes=html.escape(b["makes"]),
            open_note=' · <span style="color:var(--a)">Open now</span>' if b.get("live") else "",
        )
        for b in brands
    )
    head = src.split(start)[0] + start
    tail = end + src.split(end)[1]
    index.write_text(head + "\n" + cards + "\n      " + tail, encoding="utf-8", newline="\n")
    print("injected index.html studio cards")


def build() -> int:
    brands = json.loads((ROOT / "brands.json").read_text(encoding="utf-8"))["brands"]
    for i, b in enumerate(brands, start=1):
        b["_no"] = f"№ {i:02d}"
    inject_index(brands)
    for b in brands:
        siblings = " · ".join(
            f'<a href="../{o["key"]}/">{html.escape(o["name"])}</a>'
            for o in brands if o["key"] != b["key"]
        )
        if b.get("store"):
            counter = (
                f'<p>The shelves are stocked and the fire is lit.</p>'
                f'<p><a class="enter" href="{b["store"]}">Browse the store on Gumroad</a></p>'
            )
        else:
            counter = ("<p>Our goods are sold through Gumroad — simple checkout, "
                       "instant downloads, small batches at fair prices.</p>")
        page = TEMPLATE.format(
            counter=counter,
            key=b["key"],
            name=html.escape(b["name"]),
            room=html.escape(b["room"]),
            no=b["_no"],
            no_attr=html.escape(f"Studio {b['_no']}", quote=True),
            tagline=html.escape(b["tagline"]),
            tagline_attr=html.escape(b["tagline"], quote=True),
            makes=html.escape(b["makes"]),
            status=html.escape(b["status"]),
            accent=b["accent"],
            mark=b["mark"],
            siblings=siblings,
            fonts=FONTS,
        )
        out = ROOT / "brands" / b["key"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8", newline="\n")
        print(f"wrote {out.relative_to(ROOT)}")
    return len(brands)


if __name__ == "__main__":
    print(f"{build()} brand pages generated")
