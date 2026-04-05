"""
URL Preprocessing Branch
--------------------------
Steps  (matches diagram Image 3):
  1. Page scrape   – httpx (fast) with Playwright fallback (JS-heavy pages)
  2. Meta extract  – OG tags, schema.org, canonical
  3. Domain info   – WHOIS + age + risk heuristics
"""

from __future__ import annotations
import hashlib
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
import whois
from bs4 import BeautifulSoup

from models.feature_object import (
    DomainInfo,
    InputType,
    MetaExtract,
    NormalizedFeatureObject,
    PageScrape,
)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; MenacraftVerifier/1.0)"
    )
}
TIMEOUT = 10  # seconds


# ══════════════════════════════════════════════════════
# 1.  Page scrape
# ══════════════════════════════════════════════════════

async def scrape_page(url: str) -> tuple[int, str, str, str]:
    """
    Fetch page with httpx.
    Returns (status_code, final_url, html, raw_text).
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=TIMEOUT,
            headers=HEADERS,
        ) as client:
            resp      = await client.get(url)
            html      = resp.text
            final_url = str(resp.url)
            soup      = BeautifulSoup(html, "html.parser")

            # Remove scripts / styles before extracting visible text
            for tag in soup(["script", "style", "noscript", "head"]):
                tag.decompose()

            raw_text = " ".join(soup.get_text(separator=" ").split())
            return resp.status_code, final_url, html, raw_text

    except Exception as e:
        logger.warning(f"Page scrape failed for {url}: {e}")
        return 0, url, "", ""


# ══════════════════════════════════════════════════════
# 2.  Meta extract
# ══════════════════════════════════════════════════════

def extract_meta(html: str) -> MetaExtract:
    """
    Parse Open Graph tags, meta description, canonical URL,
    and schema.org @type values.
    """
    if not html:
        return MetaExtract()

    soup = BeautifulSoup(html, "html.parser")

    def og(prop: str) -> str | None:
        tag = soup.find("meta", property=f"og:{prop}")
        return tag.get("content") if tag else None

    def meta_name(name: str) -> str | None:
        tag = soup.find("meta", attrs={"name": name})
        return tag.get("content") if tag else None

    title = (
        og("title")
        or (soup.title.string.strip() if soup.title else None)
        or meta_name("title")
    )

    canonical = None
    link_tag  = soup.find("link", rel="canonical")
    if link_tag:
        canonical = link_tag.get("href")

    # schema.org @type
    schema_types: list[str] = []
    for tag in soup.find_all(attrs={"itemtype": True}):
        schema_types.append(tag["itemtype"])
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or ""
        for match in re.findall(r'"@type"\s*:\s*"([^"]+)"', text):
            schema_types.append(match)

    # Language from html tag
    html_tag = soup.find("html")
    language = html_tag.get("lang") if html_tag else None

    return MetaExtract(
        title         = title,
        description   = og("description") or meta_name("description"),
        og_image      = og("image"),
        og_type       = og("type"),
        canonical_url = canonical,
        language      = language,
        schema_types  = list(set(schema_types)),
    )


# ══════════════════════════════════════════════════════
# 3.  Domain info + risk heuristics
# ══════════════════════════════════════════════════════

# Domains known to be typosquatting / suspicious patterns
_SUSPICIOUS_PATTERNS = re.compile(
    r"(news-?[0-9]|breaking-?news|real-?news|truth-?[a-z]|"
    r"[0-9]{5,}|\.tk$|\.ml$|\.ga$|\.cf$|\.gq$)",
    re.I,
)

def get_domain_info(url: str) -> DomainInfo:
    """
    WHOIS lookup + age calculation + risk flags.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lstrip("www.") or url

    base = DomainInfo(domain=domain)

    try:
        w = whois.whois(domain)

        # Creation date can be list or single value
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]

        registrar = w.registrar
        country   = w.country if hasattr(w, "country") else None

        age_days: int | None = None
        is_new = False
        if creation:
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - creation).days
            is_new   = age_days < 90

        is_suspicious = bool(
            _SUSPICIOUS_PATTERNS.search(domain)
            or is_new
            or (registrar and "privacy" in registrar.lower())
        )

        return DomainInfo(
            domain        = domain,
            registrar     = str(registrar) if registrar else None,
            creation_date = creation.isoformat() if creation else None,
            age_days      = age_days,
            country       = str(country) if country else None,
            is_new_domain = is_new,
            is_suspicious = is_suspicious,
        )

    except Exception as e:
        logger.warning(f"WHOIS failed for {domain}: {e}")
        # Still run pattern check even if WHOIS fails
        return DomainInfo(
            domain        = domain,
            is_suspicious = bool(_SUSPICIOUS_PATTERNS.search(domain)),
        )


# ══════════════════════════════════════════════════════
# Pipeline entry point
# ══════════════════════════════════════════════════════

async def preprocess_url(url: str) -> NormalizedFeatureObject:
    """
    Full URL preprocessing pipeline.
    Returns a NormalizedFeatureObject ready for the agent committee.
    """
    errors: list[str] = []

    # ── Step 1: Scrape ──
    status_code, final_url, html, raw_text = await scrape_page(url)
    if status_code == 0:
        errors.append("Page scrape failed or timed out")

    # ── Step 2: Meta extract ──
    meta = extract_meta(html)

    # ── Step 3: Domain info ──
    domain_info = get_domain_info(url)

    # ── Count links and images in HTML ──
    soup        = BeautifulSoup(html, "html.parser") if html else None
    links_found = len(soup.find_all("a", href=True)) if soup else 0
    imgs_found  = len(soup.find_all("img"))           if soup else 0

    page_scrape = PageScrape(
        status_code  = status_code,
        final_url    = final_url,
        raw_text     = raw_text[:50_000],   # cap at 50k chars
        html_length  = len(html),
        links_found  = links_found,
        images_found = imgs_found,
        meta         = meta,
        domain_info  = domain_info,
    )

    # ── Dedup hash (SHA-256 of visible text) ──
    dedup_hash = hashlib.sha256(raw_text.encode()).hexdigest()

    # ── Quality gate ──
    quality_passed, quality_reason = _quality_gate(
        status_code, raw_text, domain_info
    )

    # ── Primary text: meta description + page text ──
    primary_text = " ".join(filter(None, [
        meta.title,
        meta.description,
        raw_text[:5000],
    ]))

    return NormalizedFeatureObject(
        input_type     = InputType.URL,
        source_ref     = url,
        text           = primary_text.strip(),
        language       = meta.language,
        url_data       = page_scrape,
        quality_passed = quality_passed,
        quality_reason = quality_reason,
        dedup_hash     = dedup_hash,
        errors         = errors,
    )


def _quality_gate(
    status_code: int,
    raw_text: str,
    domain_info: DomainInfo,
) -> tuple[bool, str]:
    if status_code == 0:
        return False, "Page unreachable"
    if status_code >= 400:
        return False, f"HTTP {status_code}"
    if len(raw_text.strip()) < 50:
        return False, "Page has no readable content"
    return True, "OK"