#!/usr/bin/env python3
"""SEO validation for KNakul242.github.io. Stdlib only, no dependencies."""
import glob
import json
import os
import struct
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
        if not og_image.startswith(DOMAIN + "/"):
            failures.append(f"og:image '{og_image}' is not an absolute URL under {DOMAIN}")
        else:
            rel_path = og_image[len(DOMAIN) + 1:]
            image_path = os.path.join(REPO_ROOT, *rel_path.split("/"))
            if os.path.isfile(image_path):
                width_declared = get_meta(collector, "og:image:width", "property")
                height_declared = get_meta(collector, "og:image:height", "property")
                with open(image_path, "rb") as fh:
                    header = fh.read(24)
                if header[:8] == b"\x89PNG\r\n\x1a\n":
                    real_width, real_height = struct.unpack(">II", header[16:24])
                    if width_declared != str(real_width):
                        failures.append(
                            f"og:image:width is '{width_declared}', actual image is {real_width}px wide"
                        )
                    if height_declared != str(real_height):
                        failures.append(
                            f"og:image:height is '{height_declared}', actual image is {real_height}px tall"
                        )
            else:
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
    urls = {(loc.text or "").strip() for loc in tree.getroot().findall(".//sm:loc", ns)}
    if not urls:
        urls = {(loc.text or "").strip() for loc in tree.getroot().findall(".//loc")}

    failures = []
    for html_file in html_files:
        filename = os.path.basename(html_file)
        expected_url = expected_url_for(filename)
        if expected_url not in urls:
            failures.append(f"sitemap.xml missing entry for {expected_url}")
    return failures


def is_content_page(path):
    """Real site pages start with a proper <html> document; one-off files
    like Google's site-verification marker are plain text with an .html
    extension and should not be validated as pages."""
    with open(path, encoding="utf-8") as f:
        head = f.read(200)
    return "<html" in head.lower()


def main():
    html_files = sorted(
        p for p in glob.glob(os.path.join(REPO_ROOT, "*.html")) if is_content_page(p)
    )
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
