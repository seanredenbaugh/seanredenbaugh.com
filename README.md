# seanredenbaugh.com

The website of Sean Redenbaugh — books, poetry, sonnets, scripts, photography, design, and the journal.
It's a plain static site (HTML, CSS, a little JavaScript, and one PHP file for the contact form), built by
a small Python script and hosted on Hostinger. No WordPress, no database, no plugins to update.

## How it works

```
content/            what the site says
  journal/          one file per journal post   -> /<file-name>/
  poems/            one file per poem           -> /<file-name>/
  pages/            books, sonnets, photography, design galleries, about, home page text (YAML)
templates/          the page layouts (Jinja2 HTML)
static/             copied as-is: css, js, fonts, images (wp-content/uploads), contact.php, .htaccess
build.py            turns all of the above into dist/
tools/              the one-time WordPress importer (kept for reference)
.github/workflows/  builds and uploads to Hostinger on every push to main
```

## Making changes

**Tagline, menu, footer lines, phone and email** all live in one file: `content/site.yml`.
On github.com, open it, click the pencil icon, change the text, and click **Commit changes**.
The site updates itself in a few minutes.

**Add a journal post** — create `content/journal/my-new-post.html`:

```html
---
title: My New Post
date: '2026-10-01'
type: journal
image: /wp-content/uploads/my-photo.jpg     # optional, shown at the top and in lists
---
<p>First paragraph.</p>
<p>Second paragraph.</p>
```

Put new images in `static/wp-content/uploads/`. The build makes small, fast copies automatically.

**Add a poem** — same idea in `content/poems/`, with `type: poem`. Separate stanzas with `<p>…</p>`
and lines with `<br>`.

**Add a sonnet, book, or photo** — edit `content/pages/sonnets.yml`, `books.yml`, or `photography.yml`.
Each entry follows the pattern of the ones already there.

Commit and push to `main` — GitHub builds the site and uploads it to Hostinger in about two minutes.
You can edit files right on github.com (pencil icon) if you don't want to use git locally.

**Preview on your computer (optional):**

```sh
pip3 install -r requirements.txt
python3 build.py --serve        # then open http://localhost:8000
```

## One-time setup on Hostinger

1. **Add the website** in hPanel (Websites → Add website → choose "Empty PHP/HTML website") for
   `seanredenbaugh.com`.
2. **Get FTP details** in hPanel → Files → FTP Accounts: the FTP host (IP or `ftp.seanredenbaugh.com`),
   username and password.
3. **Add three secrets to this GitHub repo** (Settings → Secrets and variables → Actions → New repository secret):
   `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD`.
4. **Run the first deploy**: GitHub → Actions → "Build and deploy" → Run workflow.
   (Hostinger's FTP account already opens inside `public_html`, so the workflow uploads to `./`.)
5. **Check it** with Hostinger's temporary preview link before pointing the domain.

## Moving the domain off Bluehost

The old WordPress site is on Bluehost. Once the new site looks right on Hostinger's preview link:

1. **Email first.** If any email addresses use `@seanredenbaugh.com`, note Bluehost's MX records before
   changing anything (Sean's mail is on Yahoo, so there may be none).
2. **Point the domain at Hostinger**: either change the nameservers at your registrar to the ones hPanel shows
   (`ns1.dns-parking.com` / `ns2.dns-parking.com` are typical), or keep DNS where it is and change the
   `A` record for `@` and `www` to the IP hPanel shows.
3. Wait for DNS to update (minutes to a few hours), then turn on **SSL** in hPanel → Security → SSL.
4. Test the contact form. It sends from `website@seanredenbaugh.com` to `seanredenbaugh@yahoo.com`.
   If messages don't arrive, check Yahoo's spam folder, and create that mailbox in hPanel → Emails.
5. Keep the Bluehost account for a couple of weeks as a backup, then cancel it.

Old WordPress addresses keep working: every page and post kept its URL, and shop, cart, category,
date-archive and feed links redirect to the right new page (see `static/.htaccess`).

## Notes

- Fonts (Bodoni Moda and EB Garamond) are served from this site, not Google.
- The old site told search engines not to index it (`noindex`). This one allows indexing and has a
  sitemap at `/sitemap.xml`. To hide it from search engines again, change `robots.txt` to `Disallow: /`.
- Book buttons link to Amazon and Barnes & Noble search results for each title. To link a specific
  product page instead, edit `templates/books.html`.
