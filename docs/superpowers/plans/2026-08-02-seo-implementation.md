# SEO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all four pages of KNakul242.github.io crawlable, indexable, and correctly previewed on social shares, verified by a dependency-free validation script that fails today and passes when this plan is complete.

**Architecture:** Each of the four static HTML files gets an identical-shaped block of `<head>` additions (meta description, canonical, Open Graph, Twitter Card, JSON-LD), following the site's existing convention of duplicating markup per file rather than sharing templates. `robots.txt` and `sitemap.xml` are added at the repo root. A single Python stdlib script (`tests/validate_seo.py`) asserts all of the above and is written first, so it fails (red) before any markup exists and passes (green) once every task is done.

**Tech Stack:** Plain HTML/CSS (no change to existing stack), Python 3 stdlib only for the validation script (no pip installs, no `requirements.txt`).

## Global Constraints

- Domain for all absolute URLs: `https://knakul242.github.io` (no CNAME; default GitHub Pages domain)
- No build tooling, no npm/Node, no new dependencies of any kind
- Validation script uses Python stdlib only (`html.parser`, `xml.etree.ElementTree`, `json`, `re`, `glob`, `os`, `sys`)
- All work happens on branch `feature/seo` (already created and pushed to `origin`); do not merge or push to `main`
- Meta/OG/Twitter descriptions must reuse the existing `.article-desc` copy from `index.html` verbatim — do not invent new marketing copy
- `og-image.png` already exists at the repo root (1254×1254) — reference it, do not regenerate it
- `datePublished` values are fixed, sourced from git history, and must be used exactly as given below

| Page | datePublished |
|---|---|
| `hollow-market.html` | `2026-03-22` |
| `thinking-frameworks.html` | `2026-04-03` |
| `counting-argument.html` | `2026-04-13` |

---

## Task 1: Write the SEO validation script (red baseline)

**Files:**
- Create: `tests/validate_seo.py`

**Interfaces:**
- Produces: a CLI script invoked as `python3 tests/validate_seo.py`, exit code `0` on full pass, `1` on any failure, printing a human-readable failure report to stdout. `ARTICLE_DATES` dict (keys: `hollow-market.html`, `thinking-frameworks.html`, `counting-argument.html`) is the canonical source later tasks' JSON-LD `datePublished` values are checked against.

- [ ] **Step 1: Write the validation script**

Create `tests/` directory and write `tests/validate_seo.py`:

```python
#!/usr/bin/env python3
"""SEO validation for KNakul242.github.io. Stdlib only, no dependencies."""
import glob
import json
import os
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://knakul242.github.io"

ARTICLE_DATES = {
    "hollow-market.html": "2026-03-22",
    "thinking-frameworks.html": "2026-04-03",
    "counting-argument.html": "2026-04-13",
}


class HeadCollector(HTMLParser):
    """Collects <meta>, <link>, and <script type=application/ld+json> tags."""

    def __init__(self):
        super().__init__()
        self.metas = []
        self.links = []
        self.ld_json_blocks = []
        self._in_ld_json = False
        self._ld_json_buffer = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            self.metas.append(attrs)
        elif tag == "link":
            self.links.append(attrs)
        elif tag == "script" and attrs.get("type") == "application/ld+json":
            self._in_ld_json = True
            self._ld_json_buffer = ""

    def handle_data(self, data):
        if self._in_ld_json:
            self._ld_json_buffer += data

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld_json:
            self.ld_json_blocks.append(self._ld_json_buffer)
            self._in_ld_json = False


def parse_html(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    collector = HeadCollector()
    collector.feed(content)
    return collector


def get_meta(collector, key, key_attr="name"):
    for m in collector.metas:
        if m.get(key_attr) == key:
            return m.get("content")
    return None


def expected_url_for(filename):
    if filename == "index.html":
        return f"{DOMAIN}/"
    return f"{DOMAIN}/{filename}"


def check_page(path):
    """Returns list of failure strings for a single HTML page. Empty = pass."""
    filename = os.path.basename(path)
    failures = []
    collector = parse_html(path)

    description = get_meta(collector, "description")
    if not description or not description.strip():
        failures.append("missing or empty <meta name='description'>")

    canonical = next(
        (l.get("href") for l in collector.links if l.get("rel") == "canonical"),
        None,
    )
    expected_canonical = expected_url_for(filename)
    if not canonical:
        failures.append("missing <link rel='canonical'>")
    elif canonical != expected_canonical:
        failures.append(
            f"canonical is '{canonical}', expected '{expected_canonical}'"
        )

    for og_key in ["og:title", "og:description", "og:image", "og:url", "og:type"]:
        if not get_meta(collector, og_key, "property"):
            failures.append(f"missing meta property='{og_key}'")

    if not get_meta(collector, "twitter:card"):
        failures.append("missing meta name='twitter:card'")

    if not collector.ld_json_blocks:
        failures.append("missing <script type='application/ld+json'> block")
    else:
        parsed_blocks = []
        for i, block in enumerate(collector.ld_json_blocks):
            try:
                parsed_blocks.append(json.loads(block))
            except json.JSONDecodeError as e:
                failures.append(f"JSON-LD block {i} is not valid JSON: {e}")

        types_present = set()
        for block in parsed_blocks:
            items = block if isinstance(block, list) else [block]
            for item in items:
                if isinstance(item, dict) and "@type" in item:
                    types_present.add(item["@type"])

        if filename == "index.html":
            if "Person" not in types_present:
                failures.append("index.html JSON-LD missing @type 'Person'")
            if "WebSite" not in types_present:
                failures.append("index.html JSON-LD missing @type 'WebSite'")
        elif filename in ARTICLE_DATES:
            if "BlogPosting" not in types_present:
                failures.append(f"{filename} JSON-LD missing @type 'BlogPosting'")
            else:
                for block in parsed_blocks:
                    items = block if isinstance(block, list) else [block]
                    for item in items:
                        if not (
                            isinstance(item, dict)
                            and item.get("@type") == "BlogPosting"
                        ):
                            continue
                        for field in ["headline", "datePublished", "author"]:
                            if field not in item:
                                failures.append(
                                    f"{filename} BlogPosting missing '{field}'"
                                )
                        expected_date = ARTICLE_DATES[filename]
                        date_published = item.get("datePublished")
                        if date_published and not date_published.startswith(
                            expected_date
                        ):
                            failures.append(
                                f"{filename} datePublished '{date_published}' "
                                f"does not start with expected '{expected_date}'"
                            )

    og_image = get_meta(collector, "og:image", "property")
    if og_image:
        image_filename = og_image.rsplit("/", 1)[-1]
        image_path = os.path.join(REPO_ROOT, image_filename)
        if not os.path.isfile(image_path):
            failures.append(
                f"og:image '{og_image}' does not exist on disk at {image_path}"
            )

    return failures


def check_robots_txt():
    path = os.path.join(REPO_ROOT, "robots.txt")
    if not os.path.isfile(path):
        return ["robots.txt does not exist"]
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "Sitemap:" not in content:
        return ["robots.txt missing 'Sitemap:' line"]
    return []


def check_sitemap_xml(html_files):
    path = os.path.join(REPO_ROOT, "sitemap.xml")
    if not os.path.isfile(path):
        return ["sitemap.xml does not exist"]
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        return [f"sitemap.xml is not well-formed XML: {e}"]

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = {loc.text.strip() for loc in tree.getroot().findall(".//sm:loc", ns)}
    if not urls:
        urls = {loc.text.strip() for loc in tree.getroot().findall(".//loc")}

    failures = []
    for html_file in html_files:
        filename = os.path.basename(html_file)
        expected_url = expected_url_for(filename)
        if expected_url not in urls:
            failures.append(f"sitemap.xml missing entry for {expected_url}")
    return failures


def main():
    html_files = sorted(glob.glob(os.path.join(REPO_ROOT, "*.html")))
    all_failures = {}

    for path in html_files:
        failures = check_page(path)
        if failures:
            all_failures[os.path.basename(path)] = failures

    robots_failures = check_robots_txt()
    if robots_failures:
        all_failures["robots.txt"] = robots_failures

    sitemap_failures = check_sitemap_xml(html_files)
    if sitemap_failures:
        all_failures["sitemap.xml"] = sitemap_failures

    if all_failures:
        print("SEO VALIDATION FAILED\n")
        for source, failures in all_failures.items():
            print(f"{source}:")
            for f in failures:
                print(f"  - {f}")
        total = sum(len(v) for v in all_failures.values())
        print(f"\n{total} check(s) failed across {len(all_failures)} file(s).")
        return 1

    print(
        f"SEO VALIDATION PASSED — {len(html_files)} pages, "
        "robots.txt, sitemap.xml all OK."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it and confirm it fails (red)**

Run: `python3 tests/validate_seo.py`

Expected: exit code `1`. Output lists failures for `index.html`, `hollow-market.html`, `thinking-frameworks.html`, `counting-argument.html` (missing description/canonical/OG/twitter/JSON-LD for each), plus `robots.txt` and `sitemap.xml` both reported as not existing.

- [ ] **Step 3: Commit and push**

```bash
git add tests/validate_seo.py
git commit -m "Add SEO validation script (red baseline)"
git push origin feature/seo
```

---

## Task 2: Crawl layer — robots.txt and sitemap.xml

**Files:**
- Create: `robots.txt`
- Create: `sitemap.xml`

**Interfaces:**
- Consumes: `expected_url_for()` convention from Task 1 — `index.html` maps to `https://knakul242.github.io/` (root, no filename), all other pages map to `https://knakul242.github.io/<filename>`.

- [ ] **Step 1: Create `robots.txt`**

```
User-agent: *
Allow: /

Sitemap: https://knakul242.github.io/sitemap.xml
```

- [ ] **Step 2: Create `sitemap.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://knakul242.github.io/</loc>
    <lastmod>2026-08-02</lastmod>
  </url>
  <url>
    <loc>https://knakul242.github.io/hollow-market.html</loc>
    <lastmod>2026-08-02</lastmod>
  </url>
  <url>
    <loc>https://knakul242.github.io/thinking-frameworks.html</loc>
    <lastmod>2026-08-02</lastmod>
  </url>
  <url>
    <loc>https://knakul242.github.io/counting-argument.html</loc>
    <lastmod>2026-08-02</lastmod>
  </url>
</urlset>
```

- [ ] **Step 3: Run the validator, confirm robots.txt/sitemap.xml failures are gone**

Run: `python3 tests/validate_seo.py`

Expected: exit code `1` still (page-level failures remain — that's correct, those are fixed in later tasks). The output must **no longer contain** a `robots.txt:` or `sitemap.xml:` section.

- [ ] **Step 4: Commit and push**

```bash
git add robots.txt sitemap.xml
git commit -m "Add robots.txt and sitemap.xml"
git push origin feature/seo
```

---

## Task 3: index.html SEO markup

**Files:**
- Modify: `index.html` (insert new lines immediately after the `<title>Nakul Khandelwal</title>` line, before the existing `<link rel="icon" ...>` line)

**Interfaces:**
- Consumes: `og-image.png` (already committed at repo root, 1254×1254) as the image asset; reuses the existing `.deck` copy `"A public notebook on machine learning, complexity, and the first principles beneath hard problems."` as the description text.

- [ ] **Step 1: Insert the SEO block into `index.html`**

Insert this block right after the `<title>` line (before the favicon `<link>`):

```html
<meta name="description" content="A public notebook on machine learning, complexity, and the first principles beneath hard problems.">
<link rel="canonical" href="https://knakul242.github.io/">
<meta property="og:type" content="website">
<meta property="og:title" content="Nakul Khandelwal">
<meta property="og:description" content="A public notebook on machine learning, complexity, and the first principles beneath hard problems.">
<meta property="og:url" content="https://knakul242.github.io/">
<meta property="og:image" content="https://knakul242.github.io/og-image.png">
<meta property="og:image:width" content="1254">
<meta property="og:image:height" content="1254">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Nakul Khandelwal">
<meta name="twitter:description" content="A public notebook on machine learning, complexity, and the first principles beneath hard problems.">
<meta name="twitter:image" content="https://knakul242.github.io/og-image.png">
<script type="application/ld+json">
[
  {
    "@context": "https://schema.org",
    "@type": "Person",
    "name": "Nakul Khandelwal",
    "url": "https://knakul242.github.io/",
    "jobTitle": "Data Scientist",
    "sameAs": [
      "https://github.com/KNakul242",
      "https://www.linkedin.com/in/nakul-khandelwal-1b87a5245",
      "https://x.com/Nakul_02"
    ]
  },
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "Nakul Khandelwal",
    "url": "https://knakul242.github.io/"
  }
]
</script>
```

- [ ] **Step 2: Run the validator, confirm index.html failures are gone**

Run: `python3 tests/validate_seo.py`

Expected: exit code `1` still (the three article pages remain unfixed). The output must **no longer contain** an `index.html:` section.

- [ ] **Step 3: Commit and push**

```bash
git add index.html
git commit -m "Add SEO meta/OG/JSON-LD tags to index.html"
git push origin feature/seo
```

---

## Task 4: hollow-market.html SEO markup

**Files:**
- Modify: `hollow-market.html` (insert immediately after `<title>The Hollow Market</title>`, before the favicon `<link>`)

**Interfaces:**
- Consumes: `ARTICLE_DATES["hollow-market.html"] == "2026-03-22"` from Task 1; reuses existing `.article-desc` copy from `index.html`: `"AI will not destroy the economy through malice. It will do something quieter — remove the tension that makes the economy worth having."`

- [ ] **Step 1: Insert the SEO block into `hollow-market.html`**

```html
<meta name="description" content="AI will not destroy the economy through malice. It will do something quieter — remove the tension that makes the economy worth having.">
<link rel="canonical" href="https://knakul242.github.io/hollow-market.html">
<meta property="og:type" content="article">
<meta property="og:title" content="The Hollow Market">
<meta property="og:description" content="AI will not destroy the economy through malice. It will do something quieter — remove the tension that makes the economy worth having.">
<meta property="og:url" content="https://knakul242.github.io/hollow-market.html">
<meta property="og:image" content="https://knakul242.github.io/og-image.png">
<meta property="og:image:width" content="1254">
<meta property="og:image:height" content="1254">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="The Hollow Market">
<meta name="twitter:description" content="AI will not destroy the economy through malice. It will do something quieter — remove the tension that makes the economy worth having.">
<meta name="twitter:image" content="https://knakul242.github.io/og-image.png">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "The Hollow Market",
  "description": "AI will not destroy the economy through malice. It will do something quieter — remove the tension that makes the economy worth having.",
  "datePublished": "2026-03-22",
  "author": {
    "@type": "Person",
    "name": "Nakul Khandelwal",
    "url": "https://knakul242.github.io/"
  },
  "url": "https://knakul242.github.io/hollow-market.html"
}
</script>
```

- [ ] **Step 2: Run the validator, confirm hollow-market.html failures are gone**

Run: `python3 tests/validate_seo.py`

Expected: exit code `1` still (two article pages remain unfixed). Output must **no longer contain** a `hollow-market.html:` section.

- [ ] **Step 3: Commit and push**

```bash
git add hollow-market.html
git commit -m "Add SEO meta/OG/JSON-LD tags to hollow-market.html"
git push origin feature/seo
```

---

## Task 5: thinking-frameworks.html SEO markup

**Files:**
- Modify: `thinking-frameworks.html` (insert immediately after `<title>The Hidden Mechanics of Thinking</title>`, before the favicon `<link>`)

**Interfaces:**
- Consumes: `ARTICLE_DATES["thinking-frameworks.html"] == "2026-04-03"` from Task 1; reuses existing `.article-desc` copy: `"Bayesian, Frequentist, Evidential, Causal — four frameworks in a century-long argument. They were never competing. They were answering different questions."`

- [ ] **Step 1: Insert the SEO block into `thinking-frameworks.html`**

```html
<meta name="description" content="Bayesian, Frequentist, Evidential, Causal — four frameworks in a century-long argument. They were never competing. They were answering different questions.">
<link rel="canonical" href="https://knakul242.github.io/thinking-frameworks.html">
<meta property="og:type" content="article">
<meta property="og:title" content="The Hidden Mechanics of Thinking">
<meta property="og:description" content="Bayesian, Frequentist, Evidential, Causal — four frameworks in a century-long argument. They were never competing. They were answering different questions.">
<meta property="og:url" content="https://knakul242.github.io/thinking-frameworks.html">
<meta property="og:image" content="https://knakul242.github.io/og-image.png">
<meta property="og:image:width" content="1254">
<meta property="og:image:height" content="1254">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="The Hidden Mechanics of Thinking">
<meta name="twitter:description" content="Bayesian, Frequentist, Evidential, Causal — four frameworks in a century-long argument. They were never competing. They were answering different questions.">
<meta name="twitter:image" content="https://knakul242.github.io/og-image.png">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "The Hidden Mechanics of Thinking",
  "description": "Bayesian, Frequentist, Evidential, Causal — four frameworks in a century-long argument. They were never competing. They were answering different questions.",
  "datePublished": "2026-04-03",
  "author": {
    "@type": "Person",
    "name": "Nakul Khandelwal",
    "url": "https://knakul242.github.io/"
  },
  "url": "https://knakul242.github.io/thinking-frameworks.html"
}
</script>
```

- [ ] **Step 2: Run the validator, confirm thinking-frameworks.html failures are gone**

Run: `python3 tests/validate_seo.py`

Expected: exit code `1` still (one article page remains unfixed). Output must **no longer contain** a `thinking-frameworks.html:` section.

- [ ] **Step 3: Commit and push**

```bash
git add thinking-frameworks.html
git commit -m "Add SEO meta/OG/JSON-LD tags to thinking-frameworks.html"
git push origin feature/seo
```

---

## Task 6: counting-argument.html SEO markup

**Files:**
- Modify: `counting-argument.html` (insert immediately after `<title>The Counting Argument</title>`, before the favicon `<link>`)

**Interfaces:**
- Consumes: `ARTICLE_DATES["counting-argument.html"] == "2026-04-13"` from Task 1; reuses existing `.article-desc` copy: `"Temperature is the most primitive quantity in physics — the one you felt before you could think. Pull its definition hard enough and it unravels into something stranger: a statement about probability, and then about time itself."`

- [ ] **Step 1: Insert the SEO block into `counting-argument.html`**

```html
<meta name="description" content="Temperature is the most primitive quantity in physics — the one you felt before you could think. Pull its definition hard enough and it unravels into something stranger: a statement about probability, and then about time itself.">
<link rel="canonical" href="https://knakul242.github.io/counting-argument.html">
<meta property="og:type" content="article">
<meta property="og:title" content="The Counting Argument">
<meta property="og:description" content="Temperature is the most primitive quantity in physics — the one you felt before you could think. Pull its definition hard enough and it unravels into something stranger: a statement about probability, and then about time itself.">
<meta property="og:url" content="https://knakul242.github.io/counting-argument.html">
<meta property="og:image" content="https://knakul242.github.io/og-image.png">
<meta property="og:image:width" content="1254">
<meta property="og:image:height" content="1254">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="The Counting Argument">
<meta name="twitter:description" content="Temperature is the most primitive quantity in physics — the one you felt before you could think. Pull its definition hard enough and it unravels into something stranger: a statement about probability, and then about time itself.">
<meta name="twitter:image" content="https://knakul242.github.io/og-image.png">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "The Counting Argument",
  "description": "Temperature is the most primitive quantity in physics — the one you felt before you could think. Pull its definition hard enough and it unravels into something stranger: a statement about probability, and then about time itself.",
  "datePublished": "2026-04-13",
  "author": {
    "@type": "Person",
    "name": "Nakul Khandelwal",
    "url": "https://knakul242.github.io/"
  },
  "url": "https://knakul242.github.io/counting-argument.html"
}
</script>
```

- [ ] **Step 2: Run the validator, confirm counting-argument.html failures are gone**

Run: `python3 tests/validate_seo.py`

Expected: exit code `1` still if any file is unfixed — but this is the last page, so at this point all page-level, robots.txt, and sitemap.xml checks should be satisfied.

- [ ] **Step 3: Commit and push**

```bash
git add counting-argument.html
git commit -m "Add SEO meta/OG/JSON-LD tags to counting-argument.html"
git push origin feature/seo
```

---

## Task 7: Full validation (green) and wrap-up

**Files:** none (verification only — no changes expected)

**Interfaces:** none

- [ ] **Step 1: Run the full validator**

Run: `python3 tests/validate_seo.py`

Expected: exit code `0`, output exactly:
```
SEO VALIDATION PASSED — 4 pages, robots.txt, sitemap.xml all OK.
```

- [ ] **Step 2: Confirm working tree is clean**

Run: `git status`

Expected: `nothing to commit, working tree clean` (aside from the pre-existing untracked `.DS_Store`, which is not part of this work).

- [ ] **Step 3: Confirm `feature/seo` is fully pushed**

Run: `git log origin/feature/seo..feature/seo --oneline`

Expected: empty output (no local commits ahead of `origin/feature/seo`).

This task ends the plan. Merging `feature/seo` into `main` is a separate, explicit decision for the repo owner — do not merge or push to `main` as part of this plan.
