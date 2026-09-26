#!/usr/bin/env python3
"""Builds seanredenbaugh.com into ./dist from content/, templates/ and static/.

    pip install -r requirements.txt
    python3 build.py            # build into dist/
    python3 build.py --serve    # build, then preview at http://localhost:8000

Adding things later:
  * a poem          -> new file in content/poems/<url-slug>.html
  * a sonnet, book, photo -> edit the matching file in content/pages/
  * tagline, menu, email -> content/site.yml
Every file in content/poems starts with a small header
(title, date, ...) between --- lines, then the HTML body.
"""
import datetime as dt
import html
import re
import shutil
import sys
from collections import OrderedDict
from pathlib import Path
from xml.sax.saxutils import escape

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
DIST = ROOT / "dist"
CACHE = ROOT / ".thumbcache"

_settings = yaml.safe_load((CONTENT / "site.yml").read_text())
SITE = {
    "name": _settings["name"],
    "url": "https://www.seanredenbaugh.com",
    "tagline": _settings["tagline"],
    "footer_lines": [l for l in _settings["footer_line"].strip().splitlines() if l.strip()],
    "description": _settings["description"],
    "email": _settings["email"],
    "year": dt.date.today().year,
}


def _menu(items):
    return [{"label": i["label"], "href": i["link"], **({"children": _menu(i["children"])} if i.get("children") else {})} for i in items]


NAV = _menu(_settings["menu"])


# ------------------------------------------------------------------ content
def load_doc(path):
    raw = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    meta = yaml.safe_load(m.group(1)) if m else {}
    body = m.group(2) if m else raw
    meta["slug"] = path.stem
    meta["body"] = body.strip()
    meta["date"] = dt.date.fromisoformat(str(meta["date"]))
    meta["url"] = f"/{path.stem}/"
    return meta


def load_yaml(name):
    return yaml.safe_load((CONTENT / "pages" / name).read_text())


def plain(h, n=None):
    t = re.sub(r"<[^>]+>", " ", h or "")
    t = html.unescape(re.sub(r"\s+", " ", t)).strip()
    if n and len(t) > n:
        t = t[:n].rsplit(" ", 1)[0].rstrip(",.;:—–-") + "…"
    return t


poems = sorted((load_doc(p) for p in (CONTENT / "poems").glob("*.html")), key=lambda d: (d["date"], d["title"]), reverse=True)

for d in poems:
    first = re.split(r"<br\s*/?>|</p>", d["body"])[0]
    d["first_line"] = plain(first)


def by_year(items):
    groups = OrderedDict()
    for it in items:
        groups.setdefault(it["date"].year, []).append(it)
    return groups


# ------------------------------------------------------------------ images
def thumb(src, width=900):
    """Return a resized WebP copy of an uploaded image (made once, cached)."""
    if not src or not src.startswith("/wp-content/uploads/") or src.lower().endswith((".pdf", ".svg", ".gif")):
        return src
    orig = STATIC / src.lstrip("/")
    if not orig.exists():
        return src
    rel = Path(src.lstrip("/")).with_suffix("")
    out_rel = Path("thumbs") / f"{rel}-{width}.webp"
    cached = CACHE / out_rel
    if not cached.exists() or cached.stat().st_mtime < orig.stat().st_mtime:
        cached.parent.mkdir(parents=True, exist_ok=True)
        im = ImageOps.exif_transpose(Image.open(orig))
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.save(cached, "WEBP", quality=80, method=6)
    dest = DIST / out_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(cached, dest)
    return "/" + out_rel.as_posix()


def img_size(src):
    try:
        with Image.open(STATIC / src.lstrip("/")) as im:
            return ImageOps.exif_transpose(im).size
    except Exception:
        return (4, 3)


def responsive_images(body):
    """Point <img> tags in post bodies at resized copies and add width/height."""
    def rep(m):
        tag = m.group(0)
        s = re.search(r'src="([^"]+)"', tag)
        if not s or not s.group(1).startswith("/wp-content/uploads/"):
            return tag
        src = s.group(1)
        w, h = img_size(src)
        new = tag.replace(f'src="{src}"', f'src="{thumb(src, 1200)}" width="{w}" height="{h}"')
        return new
    return re.sub(r"<img\b[^>]*>", rep, body)


# ------------------------------------------------------------------ render
env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
import hashlib


def asset(path):
    """/css/site.css -> /css/site.css?v=<fingerprint>, so browsers and the CDN fetch it again after an edit."""
    h = hashlib.md5((STATIC / path.lstrip("/")).read_bytes()).hexdigest()[:10]
    return f"{path}?v={h}"


env.globals.update(site=SITE, nav=NAV, thumb=thumb, img_size=img_size, asset=asset)
env.filters["longdate"] = lambda d: f"{d:%B} {d.day}, {d.year}"
env.filters["plain"] = plain


def verse_lines(body):
    """Wrap each line of a poem so a line too long for a phone wraps with a hanging indent."""
    def para(m):
        lines = re.split(r"<br\s*/?>\s*", m.group(1))
        return "<p>" + "".join(f'<span class="vl">{l.strip()}</span>' for l in lines if l.strip()) + "</p>"
    return re.sub(r"<p>(.*?)</p>", para, body, flags=re.S)


env.filters["verse"] = verse_lines


def external_links(page):
    """Open links to other websites in a new tab."""
    def rep(m):
        tag = m.group(0)
        href = re.search(r'href="([^"]*)"', tag).group(1)
        if not re.match(r"https?://", href) or re.match(r"https?://(www\.)?seanredenbaugh\.com", href) or "target=" in tag:
            return tag
        tag = re.sub(r'\srel="[^"]*"', "", tag)
        return tag[:-1] + ' target="_blank" rel="noopener">'
    return re.sub(r"<a\b[^>]*\bhref=\"[^\"]*\"[^>]*>", rep, page)


def render(template, url, **ctx):
    ctx.setdefault("url", url)
    out = external_links(env.get_template(template).render(**ctx))
    path = DIST / url.lstrip("/")
    if url.endswith("/"):
        path = path / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(out)
    pages_built.append(url)


def build():
    global pages_built
    pages_built = []
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC, DIST)

    books = load_yaml("books.yml")["books"]
    sonnets = load_yaml("sonnets.yml")
    sonnets["sonnets"].sort(key=lambda s: s["number"], reverse=True)
    photography = load_yaml("photography.yml")
    for q in photography["quotes"]:
        q["text_len"] = len(q["text"])
    about = load_yaml("about.yml")

    render("home.html", "/", books=books,
           poem=poems[0], poem_pool=[p for p in poems if 8 <= p["body"].count("<br") + p["body"].count("<p>") <= 24][:60],
           photos=photography["photos"], poem_count=len(poems))
    render("books.html", "/my-books/", books=books, title="Books",
           description="Novels, poetry and photography by Sean Redenbaugh: 1000 Shades of Red, Salima Falls, Sunlight Parted and Distant Lands of Solitude.")
    render("sonnets.html", "/sonnets/", data=sonnets, title="Sonnets",
           description="Sonnets in iambic pentameter by Sean Redenbaugh.")
    render("poetry.html", "/other-poetry/", groups=by_year(poems), count=len(poems), title="Poetry",
           description=f"{len(poems)} poems by Sean Redenbaugh, written between {poems[-1]['date'].year} and {poems[0]['date'].year}.")
    render("scripts.html", "/scripts/", title="Scripts",
           description="Screenplays by Sean Redenbaugh, including the feature-film adaptation of Sunlight Parted.")
    render("photography.html", "/photography/", data=photography, title="Photography",
           description="Nature photography by Sean Redenbaugh — sunrises, water, light and the quiet corners of Indiana and beyond.")
    render("about.html", "/about/", data=about, title="About",
           description="About Sean Redenbaugh — writer, poet, photographer and Indiana University grad.")
    render("contact.html", "/contact/", title="Contact",
           description="Get in touch with Sean Redenbaugh about books and writing.")

    for i, d in enumerate(poems):
        render("poem.html", d["url"], post=d, title=d["title"], description=plain(d["body"], 160),
               newer=poems[i - 1] if i > 0 else None, older=poems[i + 1] if i + 1 < len(poems) else None)

    render("404.html", "/404.html", title="Page not found")
    write_feed()
    write_sitemap()
    print(f"Built {len(pages_built)} pages into {DIST.relative_to(ROOT)}/")


def write_feed():
    items = []
    for d in poems[:30]:
        items.append(
            f"<item><title>{escape(d['title'])}</title><link>{SITE['url']}{d['url']}</link>"
            f"<guid>{SITE['url']}{d['url']}</guid>"
            f"<pubDate>{dt.datetime.combine(d['date'], dt.time(12)).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>"
            f"<description>{escape(plain(d['body'], 400))}</description></item>"
        )
    (DIST / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f"<title>{SITE['name']}</title><link>{SITE['url']}/</link><description>{escape(SITE['description'])}</description>"
        + "".join(items) + "</channel></rss>"
    )


def write_sitemap():
    urls = [u for u in pages_built if u.endswith("/")]
    body = "".join(f"<url><loc>{SITE['url']}{u}</loc></url>" for u in urls)
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + body + "</urlset>"
    )


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
        print("Preview at http://localhost:8000  (Ctrl+C to stop)")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()
