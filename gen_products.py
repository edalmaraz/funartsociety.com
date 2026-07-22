"""Deterministic product-layer generator: data/products.json -> the counters.

Stamps three things, all Club Edition:
  1. brand-page product grids, inside each <!-- products:<key> --> region
     (brands with an empty counter keep whatever gen_brands.py put there);
  2. one page per published product at products/<key>/<slug>/index.html;
  3. the catalogue at products/index.html.

data/products.json is exported from live store state; re-export it, then re-run
this after gen_brands.py (which resets the marker regions). Orphaned product
pages — pieces no longer in the data — are pruned. Fully re-runnable.
"""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,'
    'SOFT,WONK@0,9..144,300..900,0..100,0..1;1,9..144,300..900,0..100,0..1&display=swap" '
    'rel="stylesheet">'
)

GRID_CARD = """      <li class="pcard">
        <a class="pimg" href="{page}" tabindex="-1" aria-hidden="true"><img src="{img}" alt="" loading="lazy" width="{w}" height="{h}"></a>
        <div class="pbody">
          <h3 class="pname"><a href="{page}">{name}</a></h3>
          <div class="pprice">{price}</div>
          <div class="plinks"><a class="enter" href="{page}">View</a> <a class="enter" href="{buy}">Buy on Gumroad</a></div>
        </div>
      </li>"""

REGION = """
    <p class="status"><span class="dot" aria-hidden="true"></span>Open now — {count_note}.</p>
    <ul class="pgrid">
{cards}
    </ul>
    <p><a class="enter" href="https://{store}">Browse the full store on Gumroad</a></p>
    """

PRODUCT_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} — {brand} — Fun Art Society</title>
<meta name="description" content="{blurb_attr}">
{fonts}
<link rel="stylesheet" href="../../../assets/site.css">
<link rel="icon" href="../../../assets/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="../../../assets/apple-touch-icon.png">
<style>:root {{ --a: {accent}; }}</style>
</head>
<body>
<header class="top">
  <a class="wordmark" href="../../../"><img class="badge-inline" src="../../../assets/fas-badge.png" width="640" height="608" alt="">Fun Art Society</a>
  <span class="label mastnote">{room} · Studio {no}</span>
  <nav class="label"><a href="../../">Catalogue</a> <a href="../../../#studios">Studios</a></nav>
</header>
<main>
  <nav class="crumbs label" aria-label="Breadcrumb"><a href="../../../">The Society</a> · <a href="../../../brands/{key}/">{brand}</a> · <span aria-current="page">{name}</span></nav>
  <section class="product-hero panel">
    <img src="../../../{image}" alt="{name_attr} — preview" width="{w}" height="{h}">
  </section>
  <section class="product-body">
    <div class="no">{no} — {room}</div>
    <h1>{name}</h1>
    <p class="pprice-lg">{price}</p>
    <p class="pblurb">{blurb}</p>
    <p><a class="buy" href="{buy}">Buy on Gumroad — {price}</a></p>
    <p class="pmore"><a class="enter" href="../../../brands/{key}/">More from {brand}</a></p>
  </section>
</main>
<footer>
  <span class="label">Est. 2026</span>
  <span class="label">Creativity · Expression · Community</span>
  <span class="label">funartsociety.com</span>
</footer>
</body>
</html>
"""

CATALOG_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Catalogue — Fun Art Society</title>
<meta name="description" content="Every piece currently on the counters of the Fun Art Society — pixel art kits, planners, fine ebook editions, icons, puzzles, chiptunes, and more.">
{fonts}
<link rel="stylesheet" href="../assets/site.css">
<link rel="icon" href="../assets/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="../assets/apple-touch-icon.png">
</head>
<body>
<header class="top">
  <a class="wordmark" href="../"><img class="badge-inline" src="../assets/fas-badge.png" width="640" height="608" alt="">Fun Art Society</a>
  <span class="label mastnote">The Catalogue</span>
  <nav class="label"><a href="../#studios">Studios</a> <a href="../#about">About</a></nav>
</header>
<main>
  <section class="brand-hero">
    <div class="no">Goods in print</div>
    <h1>The Catalogue</h1>
    <p class="tagline">Every piece currently on the counters.</p>
  </section>
{sections}
</main>
<footer>
  <span class="label">Est. 2026</span>
  <span class="label">Creativity · Expression · Community</span>
  <span class="label">funartsociety.com</span>
</footer>
</body>
</html>
"""

CATALOG_SECTION = """  <section class="panel" style="--a:{accent}">
    <h2>{no} — {room} · <a href="../brands/{key}/">{brand}</a></h2>
    <ul class="cat-list">
{rows}
    </ul>
  </section>"""

CATALOG_ROW = ('      <li><span class="cat-name"><a href="{page}">{name}</a></span>'
               '<span class="cat-price">{price}</span>'
               '<a class="cat-buy enter" href="{buy}">Buy</a></li>')


def stamp_brand_page(key: str, brand: dict, co: dict) -> None:
    page = ROOT / "brands" / key / "index.html"
    src = page.read_text(encoding="utf-8")
    pat = re.compile(rf"(<!-- products:{key} -->)(.*?)(<!-- /products:{key} -->)", re.S)
    if not pat.search(src):
        raise SystemExit(f"brands/{key}/index.html: missing products markers")
    n = len(co["products"])
    cards = "\n".join(
        GRID_CARD.format(
            page=f"../../products/{key}/{p['slug']}/",
            img=f"../../{p['image']}",
            w=p["w"], h=p["h"],
            name=html.escape(p["name"]),
            price=html.escape(p["price"]),
            buy=p["url"],
        )
        for p in co["products"]
    )
    region = REGION.format(
        count_note=f"{n} piece on the counter" if n == 1 else f"{n} pieces on the counter",
        cards=cards,
        store=co["store"],
    )
    src = pat.sub(lambda m: m.group(1) + region + m.group(3), src, count=1)
    page.write_text(src, encoding="utf-8", newline="\n")
    print(f"stamped brands/{key}/index.html ({n} products)")


def write_product_pages(key: str, brand: dict, co: dict) -> int:
    for p in co["products"]:
        page = PRODUCT_PAGE.format(
            fonts=FONTS,
            key=key,
            name=html.escape(p["name"]),
            name_attr=html.escape(p["name"], quote=True),
            brand=html.escape(brand["name"]),
            room=html.escape(brand["room"]),
            no=brand["_no"],
            accent=brand["accent"],
            image=p["image"],
            w=p["w"], h=p["h"],
            price=html.escape(p["price"]),
            blurb=html.escape(p["blurb"]),
            blurb_attr=html.escape(p["blurb"], quote=True),
            buy=p["url"],
        )
        out = ROOT / "products" / key / p["slug"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8", newline="\n")
    return len(co["products"])


def write_catalog(brands: list, data: dict) -> None:
    sections = []
    for b in brands:
        co = data.get(b["key"])
        if not co or not co["products"]:
            continue
        rows = "\n".join(
            CATALOG_ROW.format(
                page=f"{b['key']}/{p['slug']}/",
                name=html.escape(p["name"]),
                price=html.escape(p["price"]),
                buy=p["url"],
            )
            for p in co["products"]
        )
        sections.append(CATALOG_SECTION.format(
            accent=b["accent"],
            no=b["_no"],
            room=html.escape(b["room"]),
            key=b["key"],
            brand=html.escape(b["name"]),
            rows=rows,
        ))
    out = ROOT / "products" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(CATALOG_PAGE.format(fonts=FONTS, sections="\n".join(sections)),
                   encoding="utf-8", newline="\n")
    print("wrote products/index.html")


def prune_orphans(data: dict) -> None:
    pdir = ROOT / "products"
    if not pdir.exists():
        return
    for kdir in sorted(d for d in pdir.iterdir() if d.is_dir()):
        keep = {p["slug"] for p in data.get(kdir.name, {}).get("products", [])}
        if not keep:
            shutil.rmtree(kdir)
            print(f"pruned products/{kdir.name}/ (no published products)")
            continue
        for sdir in sorted(d for d in kdir.iterdir() if d.is_dir()):
            if sdir.name not in keep:
                shutil.rmtree(sdir)
                print(f"pruned products/{kdir.name}/{sdir.name}/")


def build() -> int:
    brands = json.loads((ROOT / "brands.json").read_text(encoding="utf-8"))["brands"]
    for i, b in enumerate(brands, start=1):
        b["_no"] = f"№ {i:02d}"
    bykey = {b["key"]: b for b in brands}
    data = json.loads((ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    for key in data:
        if key not in bykey:
            raise SystemExit(f"data/products.json key '{key}' not in brands.json")

    total = 0
    for key, co in data.items():
        if not co["products"]:
            continue
        stamp_brand_page(key, bykey[key], co)
        total += write_product_pages(key, bykey[key], co)
    prune_orphans(data)
    write_catalog(brands, data)
    return total


if __name__ == "__main__":
    print(f"{build()} product pages generated")
