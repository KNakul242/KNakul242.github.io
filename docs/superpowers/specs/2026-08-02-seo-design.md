# SEO for KNakul242.github.io

## Goal

Make the site crawlable, indexable, and well-presented in search results and
social shares — "good enough SEO" for a personal writing site, without
adding a build step, a dependency footprint, or any process this repo
doesn't already have a reason to carry.

Domain: `https://knakul242.github.io/` (no CNAME present; default GitHub
Pages domain).

## Decomposition (first principles)

SEO for a static, no-JS, four-page site reduces to three independent
layers. Each layer has its own concrete deliverable and can be verified
independently of the others.

1. **Crawl layer** — can Google find and fetch every page?
   - `robots.txt` (allow all, point to sitemap)
   - `sitemap.xml` (lists all 4 pages with `lastmod`)
2. **Index layer** — can Google tell what each page is and treat it as the
   canonical version?
   - Unique `<meta name="description">` per page (none currently exist)
   - `<link rel="canonical">` per page
   - Existing `lang="en"`, single-`h1`-per-page structure — already correct,
     no changes needed
3. **Rich-result / social layer** — how the page looks in a search result or
   when a link is shared.
   - Open Graph (`og:title`, `og:description`, `og:image`, `og:type`,
     `og:url`) + Twitter Card tags, per page
   - JSON-LD structured data:
     - `index.html`: `Person` (name, url, sameAs: GitHub/LinkedIn/Twitter,
       jobTitle) + `WebSite` (name, url) — no `SearchAction`, the site has
       no search feature
     - Each article: `BlogPosting` (headline, description, author →
       Person, datePublished, url)

A 4th piece — Search Console verification and sitemap submission — needs
your Google account, not code. Out of scope for this branch; the two
manual steps are listed at the end of this doc.

## Second-order consideration: maintainability

This site has no templating; every HTML file is self-contained by
convention (CSS is duplicated per file rather than shared). This work
follows that same convention — meta/OG/JSON-LD blocks are duplicated per
page rather than introducing an include/build system, which would trade
today's problem for a bigger one later.

The one new process artifact, the validation script, loops over `*.html`
generically so it keeps working unmodified when a 4th article is added —
matching the existing "copy the `<li>` block" pattern already documented
in `index.html` for adding articles.

## Occam's razor: explicitly out of scope

AMP, PWA manifest/service worker, per-article OG images (one site-wide
image was chosen instead), npm/Node build tooling, JS analytics (a
separate, already-discussed topic).

## Testing approach

No test framework exists in this repo, and there's no logic to unit-test —
this is markup. The proportionate translation of TDD here:
`tests/validate_seo.py`, a dependency-free Python 3 script (stdlib only:
`html.parser`, `xml.etree.ElementTree`, `json`, `re`) that asserts:

- Every `*.html` file has a non-empty `<meta name="description">`
- Every `*.html` file has a `<link rel="canonical">` with an absolute
  `https://knakul242.github.io/...` URL
- Every `*.html` file has `og:title`, `og:description`, `og:image`,
  `og:url`, `og:type`, and `twitter:card` tags
- Every `*.html` file has at least one `<script type="application/ld+json">`
  block, and each such block is valid JSON
- `index.html`'s JSON-LD includes a `Person` and a `WebSite` type
- Each article's JSON-LD is `BlogPosting` and includes `headline`,
  `datePublished`, and `author`
- `robots.txt` exists and contains a `Sitemap:` line
- `sitemap.xml` is well-formed XML and contains a `<url>` entry for every
  `*.html` file in the repo root
- The OG image file referenced by `og:image` exists on disk

Written first, this fails against the current pages (red). Markup is then
added until every check passes (green). The script exits non-zero on any
failure and prints which page/check failed, so it stays useful as a
regression check after this branch merges.

## Deliverables

- `robots.txt` (new)
- `sitemap.xml` (new)
- `og-image.png` (new) — site-wide social preview card: the same red "N"
  monogram used for the favicon, at 1254×1254, supplied directly rather
  than generated. Square, not the "ideal" 1.91:1 OG ratio, but the mark is
  centered with generous padding, so a platform's landscape crop won't
  clip it. `og:image:width`/`og:image:height` meta tags will reflect the
  real 1254×1254 dimensions rather than assuming 1200×630.
- `<head>` additions to all four HTML files: meta description, canonical,
  OG tags, Twitter Card tags, JSON-LD
- `tests/validate_seo.py` (new)

### datePublished source (real, not invented)

Sourced from each article's first commit in git history:

| Page | datePublished |
|---|---|
| `hollow-market.html` | 2026-03-22 |
| `thinking-frameworks.html` | 2026-04-03 |
| `counting-argument.html` | 2026-04-13 |

## Workflow

All work happens on `feature/seo` (already created). The branch is pushed
to `origin` as work lands, so it's backed up and reviewable on GitHub —
`main` is not touched and nothing goes live until you review and approve
a merge.

## After this branch merges (manual, outside this repo)

1. Add the site to Google Search Console, verify ownership (Search Console
   gives a verification method — typically a meta tag or DNS record — at
   that point, which can be added as a quick follow-up commit).
2. Submit `sitemap.xml`'s URL to Search Console so Google is pointed at it
   directly rather than waiting to discover it.
