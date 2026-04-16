#!/usr/bin/env python3
"""Generate the JV-mastermind-cohort static HTML from full per-person reports.

Uses the design/CSS provided by the user (inlined here verbatim) and injects
NON-TRUNCATED content from the 15 Exa reports. The only transformation is
stripping Exa's `[label](url)` citation suffixes so cell text is readable —
the URLs are preserved separately where they matter (website, LinkedIn,
booking, socials). Phone / email / booking / full Exa notes are all kept.
"""
from __future__ import annotations
from pathlib import Path
import html as html_lib
import re

REPORTS_DIR = Path("/Users/josephtepe/exa-research/reports/jv-partners-20260416")
OUT_DIR     = Path("/Users/josephtepe/jv-mastermind-site/site")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Order: 13 resolved first, 2 unresolved (Robert, Tiffany) last.
PEOPLE = [
    ("aaron-clippinger",    "Aaron Clippinger",    "619-843-9989"),
    ("andrea-reindl",       "Andrea Reindl",       "+1-403-837-4663"),
    ("francisco-gonzalez",  "Francisco Gonzalez",  "310-922-0178"),
    ("izabela-hamilton",    "Izabela Hamilton",    "619-882-5010"),
    ("jessica-zoraida",     "Jessica Zoraida",     "619-940-7599"),
    ("justin-james",        "Justin James",        "602-492-1277"),
    ("kachina-gosselin",    "Kachina Gosselin",    "940-220-3399"),
    ("michele-lambert",     "Michele Lambert",     "480-457-0986"),
    ("mike-hill",           "Mike Hill",           "406-291-6454"),
    ("miro-heyink",         "Miro Heyink",         "816-216-8317"),
    ("naya-shakoor",        "Naya Shakoor",        "+44 7462 675808"),
    ("shameca-tankerson",   "Shameca Tankerson",   "951-581-9450"),
    ("sheevaun-moran",      "Sheevaun Moran",      "(not provided)"),
    ("robert-soares",       "Robert Soares",       "415-601-5847"),
    ("tiffany-gale",        "Tiffany Gale",        "201-522-7033"),
]


# --------- parsing helpers ---------

def extract_section(text: str, heading: str) -> str:
    """Handle both markdown (### 1. Identity) and plain (1. Identity)."""
    pat = re.compile(
        rf"^#{{0,4}}\s*\d+\.\s*{re.escape(heading)}.*?$(.*?)(?=^#{{0,4}}\s*\d+\.\s+[A-Z]|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pat.search(text)
    return m.group(1).strip() if m else ""


def top_bullets(section_text: str) -> list[tuple[str, str]]:
    """Parse top-level bullets. Returns [(label, value_html)] preserving links."""
    # Match top-level bullets (line starts with "- " and NOT indented nested bullet).
    bullets: list[tuple[str, str]] = []
    for raw in re.findall(r"^-\s+(.+?)(?=^-\s+|\Z)", section_text, re.MULTILINE | re.DOTALL):
        raw = raw.rstrip()
        # Split on first ": "
        if ":" in raw.split("\n", 1)[0]:
            label, _, rest = raw.partition(":")
            bullets.append((label.strip(), rest.strip()))
        else:
            bullets.append(("", raw.strip()))
    return bullets


def bullet(text: str, *labels: str) -> str:
    """Find first top-level bullet matching any of the labels; return value string."""
    for line in re.finditer(r"^-\s+([^:\n]+?):\s*(.+?)(?=\n-\s|\Z)", text, re.MULTILINE | re.DOTALL):
        line_label = line.group(1).strip().lower()
        for label in labels:
            if label.lower() in line_label:
                return line.group(2).strip()
    return ""


# --------- formatting helpers ---------

CITATION_RE = re.compile(r"\s*\[([^\]]+)\]\((https?://[^)]+)\)")


def strip_citations(s: str) -> str:
    """Remove trailing markdown `[label](url)` citation clusters."""
    s = CITATION_RE.sub("", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s.rstrip(".,;:").rstrip()


def first_url(s: str) -> str:
    """Extract first raw URL from a string."""
    if not s:
        return ""
    m = re.search(r"https?://[^\s)>\]\"']+", s)
    return m.group(0).rstrip(".,;:") if m else ""


def as_link(url: str, text: str | None = None) -> str:
    if not url:
        return "&mdash;"
    display = text if text else _short_url_label(url)
    return f'<a href="{html_lib.escape(url, quote=True)}" title="{html_lib.escape(url, quote=True)}">{html_lib.escape(display)}</a>'


def _short_url_label(url: str) -> str:
    """Turn https://www.rankbell.com/1-on-1-consultation-call into rankbell.com/1-on-1-consultation-call."""
    m = re.match(r"https?://(?:www\.)?([^/]+)(/.*)?", url)
    if not m:
        return url
    host = m.group(1)
    path = m.group(2) or ""
    if len(path) > 28:
        path = path[:25] + "…"
    return host + path


def escape_cell(s: str) -> str:
    """Escape for HTML but preserve reasonable inline URL rendering."""
    if not s or s.strip() == "":
        return "&mdash;"
    return html_lib.escape(s)


def to_markdown_bullets_html(section_text: str) -> str:
    """Render a section's top-level bullets as an HTML <ul>. Keeps nested bullets inline."""
    if not section_text.strip():
        return ""
    items = []
    for label, value in top_bullets(section_text):
        value_clean = strip_citations(value)
        if not value_clean:
            continue
        if label:
            items.append(
                f'<li><strong>{html_lib.escape(label)}:</strong> {html_lib.escape(value_clean)}</li>'
            )
        else:
            items.append(f"<li>{html_lib.escape(value_clean)}</li>")
    if not items:
        return ""
    return "<ul>" + "".join(items) + "</ul>"


# --------- per-person extraction ---------

def extract_person(slug: str, name: str, phone: str) -> dict:
    path = REPORTS_DIR / f"{slug}-report.md"
    text = path.read_text() if path.exists() else ""

    sec_identity = extract_section(text, "Identity")
    sec_online   = extract_section(text, "Online Presence")
    sec_business = extract_section(text, "Business / Brand") or extract_section(text, "Business")
    sec_audience = extract_section(text, "Audience & Reach") or extract_section(text, "Audience")
    sec_jv       = extract_section(text, "JV Partnership Signals") or extract_section(text, "JV")
    sec_contact  = extract_section(text, "Contactability")
    sec_fit      = extract_section(text, "JV Fit Assessment") or extract_section(text, "JV Fit")
    sec_conf     = extract_section(text, "Confidence & Gaps") or extract_section(text, "Confidence")

    # Top-line scalars (for comparison tables — full non-truncated text).
    role       = strip_citations(bullet(sec_identity, "Current primary role", "Current role", "Role"))
    location   = strip_citations(bullet(sec_identity, "Location"))
    bio        = strip_citations(bullet(sec_identity, "Short bio"))
    brand      = strip_citations(bullet(sec_business, "Company / brand name", "Company/brand name", "Brand"))
    category   = strip_citations(bullet(sec_business, "Business category", "Category"))
    niche      = strip_citations(bullet(sec_business, "Core niche and ideal audience", "Core niche", "Niche"))
    offers     = strip_citations(bullet(sec_business, "Signature programs", "offers"))
    email_list = strip_citations(bullet(sec_audience, "Email list size", "Email list"))
    top_socials= strip_citations(bullet(sec_audience, "Social follower", "Follower counts"))
    media      = strip_citations(bullet(sec_audience, "Notable media", "Media"))
    jv_page    = strip_citations(bullet(sec_jv, "JV / affiliate / partner page", "Public JV", "JV page"))
    promotes   = strip_citations(bullet(sec_jv, "Promotion of others", "Promote others"))
    summits    = strip_citations(bullet(sec_jv, "Hosted/joined virtual summits", "Summits"))
    willingness= strip_citations(bullet(sec_fit, "Likely willingness"))
    red_flags  = strip_citations(bullet(sec_fit, "Red flags"))
    confidence = strip_citations(bullet(sec_conf, "Overall confidence"))
    gaps       = strip_citations(bullet(sec_conf, "could not be verified", "could not verify"))
    best_next  = strip_citations(bullet(sec_conf, "Most useful next step", "next step"))

    # URLs
    website   = first_url(bullet(sec_online, "Primary website", "Website"))
    linkedin  = first_url(bullet(sec_online, "LinkedIn URL", "LinkedIn"))
    instagram = first_url(bullet(sec_online, "Instagram"))
    youtube   = first_url(bullet(sec_online, "YouTube"))
    facebook  = first_url(bullet(sec_online, "Facebook"))
    twitter   = first_url(bullet(sec_online, "X / Twitter", "Twitter", "X/Twitter"))
    tiktok    = first_url(bullet(sec_online, "TikTok"))
    podcast_text = strip_citations(bullet(sec_online, "Podcast(s) hosted", "Podcast(s) they host", "Podcast"))

    email        = strip_citations(bullet(sec_contact, "Public email", "Email"))
    booking_url  = first_url(bullet(sec_contact, "Booking", "Scheduling"))
    contact_form = first_url(bullet(sec_contact, "Contact form"))
    best_channel = strip_citations(bullet(sec_contact, "Best inbound"))

    return {
        "slug": slug, "name": name, "phone": phone,
        "role": role, "location": location, "bio": bio,
        "brand": brand, "category": category, "niche": niche, "offers": offers,
        "email_list": email_list, "top_socials": top_socials, "media": media,
        "jv_page": jv_page, "promotes": promotes, "summits": summits,
        "willingness": willingness, "red_flags": red_flags,
        "confidence": confidence, "gaps": gaps, "best_next": best_next,
        "website": website, "linkedin": linkedin,
        "instagram": instagram, "youtube": youtube, "facebook": facebook,
        "twitter": twitter, "tiktok": tiktok,
        "podcast_text": podcast_text,
        "email": email, "booking_url": booking_url, "contact_form": contact_form,
        "best_channel": best_channel,
        # Full rendered sections for the detail cards:
        "_identity_html": to_markdown_bullets_html(sec_identity),
        "_online_html":   to_markdown_bullets_html(sec_online),
        "_business_html": to_markdown_bullets_html(sec_business),
        "_audience_html": to_markdown_bullets_html(sec_audience),
        "_jv_html":       to_markdown_bullets_html(sec_jv),
        "_contact_html":  to_markdown_bullets_html(sec_contact),
        "_fit_html":      to_markdown_bullets_html(sec_fit),
        "_conf_html":     to_markdown_bullets_html(sec_conf),
    }


# --------- build people data ---------
people = [extract_person(slug, name, phone) for slug, name, phone in PEOPLE]


# --------- render tables ---------

def tc(s: str) -> str:
    return escape_cell(s)


def socials_inline(p: dict) -> str:
    pairs = [
        ("IG", p["instagram"]), ("YT", p["youtube"]), ("TT", p["tiktok"]),
        ("FB", p["facebook"]), ("X", p["twitter"]),
    ]
    rendered = [f'<a href="{html_lib.escape(u, quote=True)}">{label}</a>'
                for label, u in pairs if u]
    return " · ".join(rendered) if rendered else "&mdash;"


# Section 1: At-a-glance
glance_rows = []
for i, p in enumerate(people, 1):
    glance_rows.append(f"""<tr>
<td class="col-num">{i}</td>
<td class="col-name"><a href="#{p['slug']}"><strong>{tc(p['name'])}</strong></a></td>
<td>{tc(p['brand'])}</td>
<td>{tc(p['role'])}</td>
<td>{tc(p['location'])}</td>
<td>{tc(p['category'])}</td>
<td>{tc(p['email'])}</td>
<td class="col-yesno">{'yes' if p['booking_url'] else '&mdash;'}</td>
<td>{tc(p['confidence'])}</td>
</tr>""")

# Section 2: Online presence
online_rows = []
for p in people:
    online_rows.append(f"""<tr>
<td class="col-name"><a href="#{p['slug']}"><strong>{tc(p['name'])}</strong></a></td>
<td class="col-url">{as_link(p['website'])}</td>
<td class="col-url">{as_link(p['linkedin'])}</td>
<td>{tc(p['podcast_text'])}</td>
<td class="col-social">{socials_inline(p)}</td>
</tr>""")

# Section 3: Audience & reach
audience_rows = []
for p in people:
    audience_rows.append(f"""<tr>
<td class="col-name"><a href="#{p['slug']}"><strong>{tc(p['name'])}</strong></a></td>
<td>{tc(p['email_list'])}</td>
<td>{tc(p['top_socials'])}</td>
<td>{tc(p['media'])}</td>
</tr>""")

# Section 4: JV signals
jv_rows = []
for p in people:
    jv_rows.append(f"""<tr>
<td class="col-name"><a href="#{p['slug']}"><strong>{tc(p['name'])}</strong></a></td>
<td>{tc(p['jv_page'])}</td>
<td>{tc(p['promotes'])}</td>
<td>{tc(p['summits'])}</td>
<td>{tc(p['willingness'])}</td>
</tr>""")

# Section 5: Contactability
contact_rows = []
for p in people:
    contact_rows.append(f"""<tr>
<td class="col-name"><a href="#{p['slug']}"><strong>{tc(p['name'])}</strong></a></td>
<td class="col-social">{tc(p['phone'])}</td>
<td>{tc(p['email'])}</td>
<td class="col-url">{as_link(p['booking_url'])}</td>
<td>{tc(p['best_channel'])}</td>
</tr>""")


# --------- render per-person cards ---------
def card(p: dict) -> str:
    sections = [
        ("Identity",                     p["_identity_html"]),
        ("Online presence",              p["_online_html"]),
        ("Business / brand",             p["_business_html"]),
        ("Audience &amp; reach",         p["_audience_html"]),
        ("JV partnership signals",       p["_jv_html"]),
        ("Contactability",               p["_contact_html"]),
        ("JV fit assessment",            p["_fit_html"]),
        ("Confidence &amp; gaps",        p["_conf_html"]),
    ]
    body = "".join(
        f'<p><strong>{lbl}</strong></p>{content}' for lbl, content in sections if content
    )
    return f"""<article class="person-card" id="{p['slug']}">
<h3><a class="anchor-link" href="#{p['slug']}" aria-hidden="true">#</a>{html_lib.escape(p['name'])}</h3>
<p><strong>Phone:</strong> {html_lib.escape(p['phone'])}</p>
{body}
</article>"""


cards_html = "\n".join(card(p) for p in people)


# --------- TOC people list ---------
toc_people = "\n".join(
    f'<li><a href="#{p["slug"]}">{html_lib.escape(p["name"])}</a></li>' for p in people
)


# --------- final HTML (user's exact CSS + shell, with full data injected) ---------
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>JV Partner Enrichment — Mastermind Cohort</title>
<meta name="description" content="JV MatchMaker enrichment output for 15 pre-vetted mastermind partners.">
<style>
  :root {{
    --bg: #f8fafc; --surface: #ffffff;
    --ink: #1e293b; --ink-soft: #64748b; --ink-strong: #0f172a;
    --brand: #1e40af; --brand-soft: #eff6ff; --brand-ink: #2563eb;
    --border: #e2e8f0; --hover: #eff6ff;
    --dark: #0f172a; --dark-2: #1e3a8a; --accent: #93c5fd;
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; scroll-padding-top: 72px; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: var(--ink); background: var(--bg);
    line-height: 1.55; font-size: 15px;
  }}
  a {{ color: var(--brand-ink); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  .topnav {{
    position: sticky; top: 0; z-index: 10;
    background: rgba(255,255,255,0.92);
    backdrop-filter: saturate(180%) blur(8px);
    border-bottom: 1px solid var(--border);
  }}
  .topnav-inner {{
    max-width: 1200px; margin: 0 auto;
    padding: 12px 24px;
    display: flex; align-items: center; gap: 24px; flex-wrap: wrap;
  }}
  .brand-mark {{ font-weight: 700; color: var(--ink-strong); letter-spacing: -0.2px; }}
  .brand-mark span {{ color: var(--brand); }}
  .topnav nav {{ display: flex; gap: 18px; flex-wrap: wrap; font-size: 13px; }}
  .topnav nav a {{ color: var(--ink-soft); font-weight: 500; }}
  .topnav nav a:hover {{ color: var(--brand); text-decoration: none; }}

  .hero {{
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #1e40af 100%);
    color: #f8fafc;
    padding: 72px 24px 88px;
  }}
  .hero-inner {{ max-width: 1200px; margin: 0 auto; }}
  .hero .eyebrow {{
    font-size: 12px; letter-spacing: 3px; text-transform: uppercase;
    color: var(--accent); font-weight: 600; margin-bottom: 14px;
  }}
  .hero h1 {{
    font-size: clamp(32px, 5vw, 52px);
    font-weight: 800; letter-spacing: -0.5px;
    margin: 0 0 12px 0; line-height: 1.05;
  }}
  .hero .subtitle {{
    font-size: clamp(16px, 2vw, 20px);
    color: #cbd5e1; font-weight: 300; margin-bottom: 32px;
  }}
  .meta-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 18px 28px;
    padding: 22px 0;
    border-top: 1px solid rgba(148,163,184,0.3);
    border-bottom: 1px solid rgba(148,163,184,0.3);
  }}
  .meta-grid > div {{ font-size: 14px; }}
  .meta-grid strong {{
    display: block; color: var(--accent);
    font-size: 11px; letter-spacing: 1.5px;
    text-transform: uppercase; margin-bottom: 4px; font-weight: 600;
  }}
  .meta-grid span {{ color: #e2e8f0; }}

  main {{ max-width: 1200px; margin: 0 auto; padding: 48px 24px 80px; }}

  .toc-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 24px 28px;
    margin-bottom: 40px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
  }}
  .toc-card > h2 {{
    font-size: 13px; letter-spacing: 2px; text-transform: uppercase;
    color: var(--brand); margin: 0 0 14px 0;
    padding: 0; background: none; border: none;
  }}
  .toc-sections, .toc-people-list {{
    padding-left: 20px; margin: 0;
    display: grid; gap: 6px 18px;
  }}
  .toc-sections {{
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    margin-bottom: 18px;
  }}
  .toc-people-list {{
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    padding-top: 14px; margin-top: 14px;
    border-top: 1px solid var(--border);
  }}
  .toc-sections li, .toc-people-list li {{ font-size: 14px; }}
  .toc-subtitle {{
    font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
    color: var(--ink-soft); font-weight: 600; margin: 18px 0 0;
  }}

  main > h1 {{
    font-size: 28px; color: var(--ink-strong);
    margin: 0 0 6px 0; font-weight: 700; letter-spacing: -0.3px;
  }}
  main > p:first-of-type {{
    color: var(--ink-soft); font-size: 14px;
    margin: 0 0 28px 0; padding-bottom: 16px;
    border-bottom: 2px solid var(--brand);
  }}
  main hr {{ display: none; }}

  main h2 {{
    font-size: 20px; color: var(--brand);
    margin: 40px 0 14px 0;
    padding: 10px 16px;
    background: linear-gradient(90deg, var(--brand-soft) 0%, transparent 100%);
    border-left: 4px solid var(--brand);
    border-radius: 3px;
    font-weight: 700;
    scroll-margin-top: 80px;
  }}

  .table-wrap {{
    overflow-x: auto;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 24px;
    box-shadow: 0 1px 2px rgba(15,23,42,0.03);
    -webkit-overflow-scrolling: touch;
  }}
  table {{
    width: 100%;
    min-width: 1100px;
    border-collapse: collapse;
    font-size: 13px;
    table-layout: auto;
  }}
  th {{
    background: var(--dark); color: #f8fafc;
    text-align: left; padding: 10px 14px;
    font-weight: 600; font-size: 12px;
    white-space: nowrap;
  }}
  td {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
    overflow-wrap: anywhere;
    hyphens: none;
  }}
  td.col-name {{ white-space: nowrap; min-width: 150px; }}
  td.col-num  {{ white-space: nowrap; width: 32px; text-align: right; color: var(--ink-soft); }}
  td.col-url  {{ min-width: 180px; max-width: 260px; }}
  td.col-url a {{ overflow-wrap: anywhere; }}
  td.col-social {{ white-space: nowrap; }}
  td.col-yesno {{ white-space: nowrap; text-align: center; }}
  tbody tr:nth-child(even) {{ background: #f8fafc; }}
  tbody tr:hover {{ background: var(--hover); }}
  td strong {{ color: var(--brand); font-weight: 700; }}

  .cards-header {{
    font-size: 28px !important; color: var(--ink-strong) !important;
    margin: 56px 0 24px !important;
    padding: 0 0 12px 0 !important;
    background: none !important; border: none !important;
    border-bottom: 3px solid var(--brand) !important;
    border-radius: 0 !important;
    font-weight: 700; letter-spacing: -0.3px;
  }}
  .person-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 5px solid var(--brand);
    border-radius: 6px;
    padding: 24px 28px;
    margin-bottom: 28px;
    box-shadow: 0 1px 2px rgba(15,23,42,0.03);
    scroll-margin-top: 80px;
    transition: box-shadow 0.15s ease;
  }}
  .person-card:hover {{ box-shadow: 0 4px 12px rgba(15,23,42,0.08); }}
  .person-card h3 {{
    font-size: 22px; color: var(--ink-strong);
    margin: 0 0 14px 0; padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
    font-weight: 700;
    display: flex; align-items: baseline;
  }}
  .anchor-link {{
    color: var(--border); text-decoration: none;
    margin-right: 10px; font-weight: 400; font-size: 18px;
    opacity: 0; transition: opacity 0.15s ease, color 0.15s ease;
  }}
  .person-card:hover .anchor-link {{ opacity: 1; }}
  .anchor-link:hover {{ color: var(--brand); text-decoration: none; }}

  .person-card p {{ margin: 8px 0; font-size: 14px; }}
  .person-card p strong {{ color: var(--brand); }}
  .person-card ul {{ margin: 6px 0 12px 0; padding-left: 22px; font-size: 14px; }}
  .person-card ul li {{ margin-bottom: 4px; }}
  .person-card ul li strong {{ color: var(--ink-strong); }}
  .person-card p > strong:only-child {{
    display: block;
    text-transform: uppercase; font-size: 11px;
    letter-spacing: 1.5px; color: var(--ink-soft);
    font-weight: 700;
    margin-top: 18px;
  }}

  .back-to-top {{
    position: fixed; bottom: 24px; right: 24px;
    background: var(--brand); color: white;
    width: 44px; height: 44px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    text-decoration: none; font-size: 20px;
    box-shadow: 0 4px 12px rgba(30,64,175,0.3);
    opacity: 0; pointer-events: none;
    transition: opacity 0.2s ease;
    z-index: 20;
  }}
  .back-to-top.visible {{ opacity: 1; pointer-events: auto; }}
  .back-to-top:hover {{ background: var(--dark-2); text-decoration: none; }}

  footer {{
    max-width: 1200px; margin: 0 auto;
    padding: 32px 24px; color: var(--ink-soft);
    font-size: 13px; text-align: center;
    border-top: 1px solid var(--border);
  }}

  @media print {{
    .topnav, .back-to-top {{ display: none; }}
    .hero {{ background: #1e40af !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .person-card {{ page-break-inside: avoid; }}
    body {{ font-size: 10pt; }}
  }}

  @media (max-width: 640px) {{
    .hero {{ padding: 48px 20px 60px; }}
    main {{ padding: 32px 16px 60px; }}
    .person-card {{ padding: 18px 20px; }}
    .topnav nav {{ font-size: 12px; gap: 12px; }}
  }}
</style>
</head>
<body id="top">

<div class="topnav">
  <div class="topnav-inner">
    <div class="brand-mark">JV<span>·</span>MatchMaker</div>
    <nav>
      <a href="#at-a-glance-comparison">At a glance</a>
      <a href="#online-presence">Online</a>
      <a href="#audience-reach">Audience</a>
      <a href="#jv-partnership-signals">JV signals</a>
      <a href="#contactability">Contact</a>
      <a href="#per-person-detail-cards">Detail cards</a>
    </nav>
  </div>
</div>

<header class="hero">
  <div class="hero-inner">
    <div class="eyebrow">JV MatchMaker · Enrichment Output</div>
    <h1>JV Partner Enrichment</h1>
    <div class="subtitle">Mastermind cohort · 15 pre-vetted partners</div>
    <div class="meta-grid">
      <div><strong>Batch</strong><span>jv-partners-20260416</span></div>
      <div><strong>Context</strong><span>All 15 are mastermind members (pre-vetted, warm)</span></div>
      <div><strong>Generated</strong><span>April 16, 2026</span></div>
    </div>
  </div>
</header>

<main>
  <section class="toc-card">
    <h2>Contents</h2>
    <ol class="toc-sections">
      <li><a href="#at-a-glance-comparison">At-a-glance comparison</a></li>
      <li><a href="#online-presence">Online presence</a></li>
      <li><a href="#audience-reach">Audience &amp; reach</a></li>
      <li><a href="#jv-partnership-signals">JV partnership signals</a></li>
      <li><a href="#contactability">Contactability</a></li>
      <li><a href="#per-person-detail-cards">Per-person detail cards</a></li>
    </ol>
    <div class="toc-subtitle">Partners profiled</div>
    <ol class="toc-people-list">
{toc_people}
    </ol>
  </section>

  <h1>JV Partner Enrichment — Enriched Table</h1>
  <p><strong>Batch:</strong> jv-partners-20260416 · <strong>Context:</strong> All 15 are mastermind members (pre-vetted, warm). Full non-truncated content.</p>

  <h2 id="at-a-glance-comparison">At-a-glance comparison</h2>
  <div class="table-wrap"><table>
    <thead><tr>
      <th>#</th><th>Name</th><th>Brand</th><th>Role</th><th>Location</th>
      <th>Primary offer/category</th><th>Email</th><th>Booking</th><th>Confidence</th>
    </tr></thead>
    <tbody>
{"".join(glance_rows)}
    </tbody>
  </table></div>

  <h2 id="online-presence">Online presence</h2>
  <div class="table-wrap"><table>
    <thead><tr>
      <th>Name</th><th>Website</th><th>LinkedIn</th><th>Podcast</th><th>Top socials</th>
    </tr></thead>
    <tbody>
{"".join(online_rows)}
    </tbody>
  </table></div>

  <h2 id="audience-reach">Audience &amp; reach</h2>
  <div class="table-wrap"><table>
    <thead><tr>
      <th>Name</th><th>Email list</th><th>Top socials (followers)</th><th>Notable media</th>
    </tr></thead>
    <tbody>
{"".join(audience_rows)}
    </tbody>
  </table></div>

  <h2 id="jv-partnership-signals">JV partnership signals</h2>
  <div class="table-wrap"><table>
    <thead><tr>
      <th>Name</th><th>Affiliate/JV page</th><th>Promotes others</th><th>Summits/bundles</th><th>Willingness</th>
    </tr></thead>
    <tbody>
{"".join(jv_rows)}
    </tbody>
  </table></div>

  <h2 id="contactability">Contactability</h2>
  <div class="table-wrap"><table>
    <thead><tr>
      <th>Name</th><th>Phone</th><th>Email</th><th>Booking link</th><th>Best inbound</th>
    </tr></thead>
    <tbody>
{"".join(contact_rows)}
    </tbody>
  </table></div>

  <h2 class="cards-header" id="per-person-detail-cards">Per-person detail cards</h2>
{cards_html}
</main>

<a href="#top" class="back-to-top" aria-label="Back to top">↑</a>

<footer>
  JV MatchMaker · Generated April 16, 2026
</footer>

<script>
  var btt = document.querySelector('.back-to-top');
  window.addEventListener('scroll', function() {{
    if (window.scrollY > 600) btt.classList.add('visible');
    else btt.classList.remove('visible');
  }});
</script>

</body>
</html>
"""

(OUT_DIR / "index.html").write_text(HTML)
# Convenience: a .nojekyll file for GitHub Pages to serve as-is.
(OUT_DIR / ".nojekyll").write_text("")
print(f"wrote {OUT_DIR / 'index.html'}  ({len(HTML):,} bytes)")
