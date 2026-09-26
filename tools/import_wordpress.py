#!/usr/bin/env python3
"""One-time importer: turns the WordPress export (content.json + wp-content/uploads)
into the plain content files this site is built from.

Usage: python3 tools/import_wordpress.py /path/to/export
The export folder must contain content.json and wp-content/uploads/.
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, NavigableString
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
EXPORT = Path(sys.argv[1] if len(sys.argv) > 1 else "export")
SRC_UPLOADS = EXPORT / "wp-content" / "uploads"
OUT_CONTENT = ROOT / "content"
OUT_UPLOADS = ROOT / "static" / "wp-content" / "uploads"

data = json.loads((EXPORT / "content.json").read_text())
pages = data["pages"]
used_images = set()
missing_images = set()


# ---------------------------------------------------------------- helpers
def resolve_image(src):
    """Map any WordPress image URL (resized, CDN, broken) to an original file we have."""
    if not src:
        return None
    src = html.unescape(src)
    src = re.sub(r"^https?://i\d\.wp\.com/(www\.)?seanredenbaugh\.com/?", "/", src)
    src = re.sub(r"^https?://(www\.)?seanredenbaugh\.com", "", src)
    src = src.split("?")[0]
    if not src.startswith("/wp-content/uploads/"):
        return src  # external image, leave alone
    rel = src[len("/wp-content/uploads/"):]
    candidates = [re.sub(r"-\d+x\d+(\.\w+)$", r"\1", rel), rel]
    for c in candidates:
        if (SRC_UPLOADS / c).exists():
            used_images.add(c)
            return "/wp-content/uploads/" + c
    missing_images.add(src)
    return None


def fix_images(soup):
    for img in soup.find_all("img"):
        new = resolve_image(img.get("src"))
        if new is None:
            img.decompose()
            continue
        img["src"] = new
        img["loading"] = "lazy"
        if not img.get("alt"):
            img["alt"] = ""
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if "wp-content/uploads" in h:
            new = resolve_image(h)
            if new:
                a["href"] = new
        a["href"] = re.sub(r"^https?://(www\.)?seanredenbaugh\.com", "", a["href"]) or "/"
    for f in soup.find_all("iframe"):
        m = re.search(r"youtube(?:-nocookie)?\.com/embed/([\w-]{6,})", f.get("src", ""))
        if m:
            f.replace_with(BeautifulSoup(f'<div class="yt" data-id="{m.group(1)}"></div>', "html.parser"))
    return soup


def clean_fragment(h):
    # drop the theme's post footer (category, author box, related posts)
    h = re.split(r"\n?Category:&nbsp;|<h3>Related posts</h3>", h)[0]
    h = h.replace("https://i0.wp.com/www.seanredenbaugh.comwp-content", "/wp-content")
    soup = fix_images(BeautifulSoup(h, "html.parser"))
    for p in soup.find_all("p"):
        if not p.get_text(strip=True) and not p.find(["img", "iframe", "div"]):
            p.decompose()
    out = str(soup)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def write_doc(path, meta, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000)
    path.write_text(f"---\n{fm}---\n{body.strip()}\n")


def text(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


# ---------------------------------------------------------------- posts
for p in data["posts"]:
    is_poem = "Poems" in p["cats"]
    body = clean_fragment(p["html"])
    if is_poem:
        # poems were wrapped in blockquote + <em>; store them as plain verse
        soup = BeautifulSoup(body, "html.parser")
        bq = soup.find("blockquote")
        if bq:
            bq.unwrap()
        for em in soup.find_all("em"):
            em.unwrap()
        body = str(soup).strip()
    meta = {
        "title": html.unescape(p["title"]),
        "date": p["date"][:10],
        "type": "poem" if is_poem else "journal",
    }
    if not is_poem:
        tags = [c for c in p["cats"] if c[0].isupper() and c != "Uncategorized"]
        if tags:
            meta["tags"] = tags[:3]
        img = resolve_image(p.get("image"))
        if img:
            meta["image"] = img
    write_doc(OUT_CONTENT / ("poems" if is_poem else "journal") / f"{p['slug']}.html", meta, body)


# ---------------------------------------------------------------- sonnets
soup = BeautifulSoup(pages["sonnets"], "html.parser")
intro = [str(p) for p in soup.find_all("p", recursive=False)[:2]]
sonnets, cur = [], None
for el in soup.children:
    if isinstance(el, NavigableString) or el.name != "p":
        continue
    a = el.find("a")
    if a and text(a).startswith("#"):
        m = re.match(r"#(\d+)\s*-\s*(.*)", text(a))
        cur = {"number": int(m.group(1)), "title": m.group(2).rstrip(". ").rstrip("…") + "…", "lines": [], "date": ""}
        sonnets.append(cur)
        continue
    if cur is None:
        continue
    t = text(el)
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", t):
        cur["date"] = t
        continue
    for em in el.find_all(["em", "i"]):
        em.unwrap()
    lines = [re.sub(r"\s+", " ", BeautifulSoup(x, "html.parser").get_text()).strip() for x in re.split(r"<br\s*/?>", el.decode_contents())]
    cur["lines"] += [l for l in lines if l]
(OUT_CONTENT / "pages").mkdir(parents=True, exist_ok=True)
yaml.safe_dump(
    {"intro": [BeautifulSoup(i, "html.parser").get_text() for i in intro], "image": resolve_image("/wp-content/uploads/2014/07/pen.jpg"), "sonnets": sonnets},
    (OUT_CONTENT / "pages" / "sonnets.yml").open("w"), allow_unicode=True, sort_keys=False, width=1000,
)


# ---------------------------------------------------------------- galleries
def gallery(page_html):
    s = BeautifulSoup(page_html, "html.parser")
    items = []
    for fig in s.find_all("figure"):
        a = fig.find("a")
        img = fig.find("img")
        full = resolve_image(a["href"] if a and a.get("href", "").startswith("/wp-content") else (img and img.get("src")))
        if not full:
            continue
        cap = fig.find("figcaption")
        title = text(cap) if cap else ""
        items.append({"src": full, "title": title})
    return items


photo_soup = BeautifulSoup(pages["photography"], "html.parser")
photos = gallery(pages["photography"])
photo_items = []
for it in photos:
    if "behindcamera" in it["src"]:
        continue
    m = re.match(r"(\d+)\s*\((.*)\)", it["title"])
    photo_items.append({"src": it["src"], "number": m.group(1) if m else "", "title": m.group(2) if m else it["title"]})
quotes = []
for q in photo_soup.find_all("q"):
    ps = [text(p) for p in q.find_all("p")]
    quotes.append({"text": ps[0].strip("“”\""), "by": ps[1].lstrip("–- ").strip() if len(ps) > 1 else ""})
yaml.safe_dump(
    {
        "intro": text(photo_soup.find("p")),
        "portrait": resolve_image("/wp-content/uploads/2014/07/behindcamera.jpg"),
        "quotes": quotes,
        "photos": photo_items,
    },
    (OUT_CONTENT / "pages" / "photography.yml").open("w"), allow_unicode=True, sort_keys=False, width=1000,
)

for name in ["web-design", "graphic-design"]:
    yaml.safe_dump({"items": [i["src"] for i in gallery(pages[name])]},
                   (OUT_CONTENT / "pages" / f"{name}.yml").open("w"), allow_unicode=True, sort_keys=False, width=1000)


# ---------------------------------------------------------------- books
mb = pages["my-books"]
chunks = re.split(r'<h3><a href="#info-details">\s*Info &amp; Details\s*</a></h3>', mb)
head_soup = BeautifulSoup(chunks[0], "html.parser")
cover_imgs = [resolve_image(i["src"]) for i in head_soup.find_all("img")]


def section(chunk, anchor):
    parts = re.split(r'<h3><a href="#([\w-]+)">.*?</a></h3>', chunk, flags=re.S)
    out = {}
    out["_info"] = parts[0]
    for i in range(1, len(parts) - 1, 2):
        out[parts[i]] = parts[i + 1]
    return out.get(anchor, "")


def info_table(chunk):
    s = BeautifulSoup(re.split(r"<h3>", chunk)[0], "html.parser")
    return [[text(td) for td in tr.find_all("td")] for tr in s.find_all("tr")]


def paras(h):
    s = BeautifulSoup(h, "html.parser")
    for t in s.find_all("table"):
        t.decompose()
    out = []
    for p in s.find_all("p"):
        t = re.sub(r"\s+", " ", p.get_text(" ")).strip()
        t = re.sub(r"([.?!…])(?=[A-Z“])", r"\1 ", t)  # the old theme glued sentences together
        if t:
            out.append(t)
    return out


def poems_table(h):
    s = BeautifulSoup(h, "html.parser")
    res = []
    for td in s.find_all("td"):
        title = td.contents[0].strip() if isinstance(td.contents[0], NavigableString) else ""
        stanzas = []
        for p in td.find_all("p"):
            lines = [BeautifulSoup(x, "html.parser").get_text().strip() for x in re.split(r"<br\s*/?>", p.decode_contents())]
            lines = [l for l in lines if l]
            if lines:
                stanzas.append(lines)
        if not stanzas:
            lines = [BeautifulSoup(x, "html.parser").get_text().strip() for x in re.split(r"<br\s*/?>", td.decode_contents())]
            stanzas = [[l for l in lines if l]]
        res.append({"title": title, "stanzas": stanzas})
    return res


books_meta = [
    {"slug": "1000-shades-of-red", "title": "1000 Shades of Red", "kind": "Literary Fiction Novel", "year": 2025, "price": "$18.99", "tagline": "Perfection once, perfection forever"},
    {"slug": "salima-falls", "title": "Salima Falls", "kind": "Literary Fiction Novel", "year": 2017, "price": "$15.00", "tagline": "You just have to have faith that the universe knows what it's doing."},
    {"slug": "sunlight-parted", "title": "Sunlight Parted", "kind": "Literary Fiction Novel", "year": 2015, "price": "$12.00", "tagline": "Let me live in chase… of that perfection I have dared in dreams"},
    {"slug": "distant-lands-of-solitude", "title": "Distant Lands of Solitude", "kind": "Poetry & Photography Collection", "year": 2006, "tagline": "The photographs and writings of Sean Redenbaugh"},
]
praise = {
    "sunlight-parted": {"text": "Sunlight Parted is an amazing love story without being sappy or too saccharin, it draws the reader in with high emotional stakes and an incredibly interesting take on life and death. I found it so meaningful, I got teary at the end! Books don’t usually affect me so directly, but this packs a heck of an emotional punch. Bravo!", "by": "Cara Lockwood", "role": "USA Today best-selling author of 10 books, professional editor"},
    "distant-lands-of-solitude": {"text": "These photographs and verses are a welcoming chance and reminder to slow down and appreciate the small things that give meaning and purpose to life. Whether it is a drop of water collecting on a fallen leaf, or a couplet capturing the complexities of beauty, this book definitely gives us all something to enjoy and reflect on.", "by": "Karl Mayer", "role": "Book collector & avid reader"},
}
books = []
for i, meta in enumerate(books_meta):
    ch = chunks[i + 1]
    b = dict(meta)
    b["cover"] = cover_imgs[i]
    b["details"] = info_table(ch)
    b["synopsis"] = paras(section(ch, "story-synopsis"))
    if section(ch, "writing-excerpt"):
        b["excerpt"] = paras(section(ch, "writing-excerpt"))
    if section(ch, "sample-poems"):
        b["sample_poems"] = poems_table(section(ch, "sample-poems"))
        qs = BeautifulSoup(section(ch, "sample-quotes"), "html.parser")
        b["sample_quotes"] = [[l.strip().strip("“”") for l in re.split(r"<br\s*/?>", td.decode_contents())] for td in qs.find_all("td")]
        b["sample_quotes"] = [[BeautifulSoup(l, "html.parser").get_text().strip().strip("“”") for l in q] for q in b["sample_quotes"]]
    if meta["slug"] in praise:
        b["praise"] = praise[meta["slug"]]
    books.append(b)
yaml.safe_dump({"books": books}, (OUT_CONTENT / "pages" / "books.yml").open("w"), allow_unicode=True, sort_keys=False, width=1000)


# ---------------------------------------------------------------- about
ab = BeautifulSoup(pages["about"], "html.parser")
about = {"portrait": resolve_image(ab.find("img")["src"])}
q = ab.find("q")
qp = [text(p) for p in q.find_all("p")]
about["quote"] = {"text": qp[0].strip("“”"), "by": qp[1].lstrip("– ")}
q.decompose()
intro, sections, cur = [], [], None
for el in ab.children:
    if isinstance(el, NavigableString):
        continue
    if el.name == "h3":
        cur = {"title": text(el), "html": ""}
        sections.append(cur)
    elif el.name in ("p", "table"):
        for a in el.find_all("a"):
            a.unwrap()
        s = str(el)
        s = s.replace("(www.mavrei.com.", '(<a href="https://www.mavrei.com">www.mavrei.com</a>).')
        if cur is None:
            intro.append(s)
        else:
            cur["html"] += s + "\n"
about["intro"] = intro
about["sections"] = sections
yaml.safe_dump(about, (OUT_CONTENT / "pages" / "about.yml").open("w"), allow_unicode=True, sort_keys=False, width=1000)


# ---------------------------------------------------------------- home essay
hs = BeautifulSoup(pages["home"], "html.parser")
bq = hs.find("blockquote")
essay = [str(p).replace("\n", " ") for p in bq.find_next_siblings("p")][:4]
yt = [re.search(r"embed/([\w-]+)", f["src"]).group(1) for f in hs.find_all("iframe")]
yaml.safe_dump(
    {
        "prompt": {"text": text(bq.find("p")).strip("“” "), "by": "Unknown"},
        "essay": [re.sub(r"\s+", " ", e.replace("<p>", "").replace("</p>", "")).strip() for e in essay],
        "songs": yt,
    },
    (OUT_CONTENT / "pages" / "home.yml").open("w"), allow_unicode=True, sort_keys=False, width=1000,
)


# ---------------------------------------------------------------- extra images used by templates
for extra in [
    "/wp-content/uploads/2014/07/slide_sunlightparted.jpg",
    "/wp-content/uploads/SalimaFalls_slide.jpg",
    "/wp-content/uploads/2014/07/slide_distantlands1.jpg",
    "/wp-content/uploads/SunlightParted-SeanRedenbaugh.pdf",
    "/wp-content/uploads/2014/08/sean-small.jpg",
    "/wp-content/uploads/2014/07/Sean.jpg",
]:
    resolve_image(extra)


# ---------------------------------------------------------------- copy + optimise images
MAX = 2400
copied = 0
for rel in sorted(used_images):
    src, dst = SRC_UPLOADS / rel, OUT_UPLOADS / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() in (".jpg", ".jpeg"):
        try:
            im = Image.open(src)
            if max(im.size) > MAX or src.stat().st_size > 900_000:
                im = im.convert("RGB")
                im.thumbnail((MAX, MAX))
                im.save(dst, "JPEG", quality=84, optimize=True, progressive=True)
                copied += 1
                continue
        except Exception:
            pass
    shutil.copy2(src, dst)
    copied += 1

print(f"posts: {len(data['posts'])}, sonnets: {len(sonnets)}, photos: {len(photo_items)}, books: {len(books)}")
print(f"images copied: {copied}")
if missing_images:
    print("missing images (skipped):")
    for m in sorted(missing_images):
        print("  ", m)
