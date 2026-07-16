from __future__ import annotations

import base64
import html
import json
import mimetypes
import os
import re
import shutil
import sys
import unicodedata
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request, send_file
from rapidfuzz import fuzz, process

BASE_DIR = Path(__file__).resolve().parent

# Dados persistentes ficam fora da pasta da versão. Assim, versões novas podem
# ser instaladas lado a lado sem perder perfis, logos, cache, projetos ou saídas.
DOCUMENTS_DIR = Path.home() / "Documents"
DATA_ROOT = DOCUMENTS_DIR / "GENMB" / "Data"
LEGACY_DATA_ROOT = DOCUMENTS_DIR / "News Reconstruction Studio" / "Data"
PROFILES_DIR = DATA_ROOT / "Profiles"
BRAND_THEMES_DIR = DATA_ROOT / "BrandThemes"
LOGOS_DIR = DATA_ROOT / "Logos"
FONTS_DIR = DATA_ROOT / "Fonts"
TEMP_DIR = DATA_ROOT / "Temporary"
CACHE_DIR = DATA_ROOT / "Cache"
PROJECTS_DIR = DATA_ROOT / "Projects"
OUTPUT_DIR = DATA_ROOT / "Output"
for _dir in (DATA_ROOT, PROFILES_DIR, BRAND_THEMES_DIR, LOGOS_DIR, FONTS_DIR, TEMP_DIR, CACHE_DIR, PROJECTS_DIR, OUTPUT_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# Migração única e não destrutiva dos dados das versões anteriores.
if LEGACY_DATA_ROOT.exists() and not any(p.is_file() for p in DATA_ROOT.rglob("*")):
    for _name in ("Profiles", "BrandThemes", "Logos", "Cache", "Projects", "Output"):
        _src = LEGACY_DATA_ROOT / _name
        _dst = DATA_ROOT / _name
        if _src.exists():
            shutil.copytree(_src, _dst, dirs_exist_ok=True)

PROFILE_FILE = PROFILES_DIR / "stylus_profiles.json"
REGISTRY_FILE = PROFILES_DIR / "stylus_registry.json"
PREFERENCES_FILE = PROFILES_DIR / "stylus_preferences.json"
BRAND_FILE = BRAND_THEMES_DIR / "brand_profiles.json"
LATEST_BATCH_FILE = OUTPUT_DIR / "latest_batch.txt"

# Arquivos distribuídos com o programa servem apenas como defaults para a
# primeira execução. Depois disso, a cópia persistente em Documents prevalece.
BUNDLED_STYLUS_FILE = BASE_DIR / "stylus_backup.json"
BUNDLED_REGISTRY_FILE = BASE_DIR / "stylus_registry.json"
BUNDLED_BRAND_FILE = BASE_DIR / "brand_profiles.json"
for _src, _dst in ((BUNDLED_REGISTRY_FILE, REGISTRY_FILE), (BUNDLED_BRAND_FILE, BRAND_FILE)):
    if not _dst.exists() and _src.exists():
        shutil.copy2(_src, _dst)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
app.json.ensure_ascii = False


@dataclass
class EditorialImage:
    url: str
    caption: str = ""
    credit: str = ""
    width: int = 0
    height: int = 0


@dataclass
class VisualIdentity:
    vehicle: str = ""
    logo_url: str = ""
    header_bg: str = "#202124"
    header_fg: str = "#ffffff"
    title_font: str = "Arial, sans-serif"
    title_weight: str = "700"
    title_color: str = "#202124"
    body_font: str = "Arial, sans-serif"
    body_weight: str = "400"
    body_color: str = "#202124"
    body_bg: str = "#ffffff"
    accent: str = "#d71920"
    link_color: str = "#c40000"
    header_mode: str = "auto_capture"
    logo_scale: float = 0.64
    header_height_ratio: float = 0.095
    header_align: str = "left"
    divider_size: int = 5
    logo_filter: str = "none"


@dataclass
class Article:
    title: str
    subtitle: str
    author: str
    published: str
    image: str
    paragraphs: list[str]
    images: list[EditorialImage] = field(default_factory=list)




DEFAULT_BRANDS = {
    "vaticannews.va": {"name":"Vatican News","header_mode":"auto_capture","primary":"#a10000","secondary":"#ffffff","header_fg":"#ffffff","logo_scale":0.72,"header_height_ratio":0.10,"divider_size":0,"logo_filter":"none","title_font":"Arial, sans-serif","body_font":"Arial, sans-serif"},
    "cnnbrasil.com.br": {"name":"CNN Brasil","header_mode":"custom_theme","primary":"#c90016","secondary":"#ffffff","header_fg":"#ffffff","logo_scale":0.74,"header_height_ratio":0.105,"divider_size":0,"logo_filter":"brightness(0) invert(1)","title_font":"Arial, sans-serif","body_font":"Arial, sans-serif"},
    "ge.globo.com": {"name":"ge","header_mode":"custom_theme","primary":"#06aa48","secondary":"#ffffff","header_fg":"#ffffff","logo_scale":0.70,"header_height_ratio":0.105,"divider_size":0,"logo_filter":"brightness(0) invert(1)","title_font":"Arial, sans-serif","body_font":"Arial, sans-serif"},
    "g1.globo.com": {"name":"g1","header_mode":"custom_theme","primary":"#c4170c","secondary":"#ffffff","header_fg":"#ffffff","logo_scale":0.70,"header_height_ratio":0.105,"divider_size":0,"logo_filter":"brightness(0) invert(1)","title_font":"Arial, sans-serif","body_font":"Arial, sans-serif"},
    "osaopaulo.org.br": {"name":"O São Paulo","header_mode":"custom_theme","primary":"#ffffff","secondary":"#9d1b1b","header_fg":"#111111","logo_scale":0.72,"header_height_ratio":0.105,"divider_size":4,"logo_filter":"none","title_font":"Georgia, serif","body_font":"Georgia, serif"},
}

def load_brand_profiles() -> dict:
    profiles = dict(DEFAULT_BRANDS)
    if BRAND_FILE.exists():
        try:
            custom=json.loads(BRAND_FILE.read_text(encoding="utf-8"))
            for k,v in custom.items():
                base=dict(profiles.get(k,{})); base.update(v); profiles[k]=base
        except Exception:
            pass
    return profiles

def save_brand_profiles(data: dict) -> None:
    BRAND_FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

def brand_key_for_url(url: str) -> str:
    host=(urlparse(url).hostname or "").lower().removeprefix("www.")
    profiles=load_brand_profiles()
    if host in profiles: return host
    matches=[k for k in profiles if host==k or host.endswith("."+k)]
    return max(matches,key=len) if matches else host

def apply_brand_profile(identity: VisualIdentity, url: str) -> tuple[VisualIdentity, dict]:
    key=brand_key_for_url(url); profile=load_brand_profiles().get(key,{})
    if not profile: return identity,{"key":key,"name":identity.vehicle or key,"header_mode":"auto_capture"}
    identity.vehicle=profile.get("name") or identity.vehicle
    identity.header_mode=profile.get("header_mode","auto_capture")
    identity.logo_scale=float(profile.get("logo_scale",identity.logo_scale))
    identity.header_height_ratio=float(profile.get("header_height_ratio",identity.header_height_ratio))
    identity.header_align=profile.get("header_align","left")
    identity.divider_size=int(profile.get("divider_size",identity.divider_size))
    identity.logo_filter=profile.get("logo_filter",identity.logo_filter)
    if profile.get("logo_url"):
        identity.logo_url=profile["logo_url"]
    if identity.header_mode=="custom_theme":
        identity.header_bg=profile.get("primary",identity.header_bg)
        identity.header_fg=profile.get("header_fg",profile.get("secondary",identity.header_fg))
        identity.accent=profile.get("secondary",identity.accent)
    identity.title_font=profile.get("title_font",identity.title_font)
    identity.title_weight=str(profile.get("title_weight",identity.title_weight))
    identity.body_font=profile.get("body_font",identity.body_font)
    identity.body_weight=str(profile.get("body_weight",identity.body_weight))
    if profile.get("title_color"): identity.title_color=profile["title_color"]
    if profile.get("body_color"): identity.body_color=profile["body_color"]
    if profile.get("body_bg"): identity.body_bg=profile["body_bg"]
    return identity,{"key":key,**profile}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value, flags=re.UNICODE).strip()


def normalize_for_match(value: str) -> str:
    value = unicodedata.normalize("NFKC", clean_text(value)).casefold()
    value = value.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", " ", value).strip()


def domain_from_url(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")




def normalize_host(host: str) -> str:
    return (host or "").lower().strip().removeprefix("www.")


def _style_targets(section: dict) -> tuple[list[str], list[str], list[str]]:
    domains = [normalize_host(x) for x in section.get("domains", []) if x]
    prefixes = [str(x).strip() for x in section.get("urlPrefixes", []) if x]
    urls = [str(x).strip() for x in section.get("urls", []) if x]
    return domains, prefixes, urls


def _css_warnings(code: str) -> list[str]:
    warnings = []
    if re.search(r"^[a-zA-Z]{8,}body\s*[>{.#]", code.strip()):
        warnings.append("Possível texto acidental antes do primeiro seletor CSS.")
    if re.search(r"#[A-Za-z_-]*(?:post|node)-\d+", code):
        warnings.append("Contém seletores específicos de uma matéria e pode exigir generalização.")
    if len(re.findall(r"--[a-zA-Z0-9_-]+\s*:", code)) >= 5:
        warnings.append("Contém muitas variáveis CSS; algumas podem não alterar propriedades diretamente.")
    if re.search(r"\{\s*[.#][^{}]+\{", code):
        warnings.append("Possível CSS aninhado ou bloco estrutural inválido.")
    return warnings


def parse_stylus_export(payload: list | dict) -> tuple[list[dict], dict]:
    records = payload if isinstance(payload, list) else [payload]
    styles = [x for x in records if isinstance(x, dict) and (x.get("sections") or x.get("sourceCode")) and x.get("name")]
    entries = []
    skipped = []
    for style in styles:
        name = str(style.get("name", "")).strip()
        all_targets = []
        for sec in style.get("sections", []) or []:
            d,p,u = _style_targets(sec)
            all_targets.extend(("domain",x) for x in d)
            all_targets.extend(("prefix",x) for x in p)
            all_targets.extend(("url",x) for x in u)
        target_text = " ".join(v for _,v in all_targets).lower()
        if "instagram.com" in target_text or "instagram" in name.lower():
            skipped.append({"id": style.get("id"), "name": name, "reason": "Instagram adiado"})
            continue
        sections = []
        scoped_targets = []
        unscoped = []
        for sec in style.get("sections", []) or []:
            code = clean_stylus_css(str(sec.get("code", "")))
            domains,prefixes,urls = _style_targets(sec)
            if domains or prefixes or urls:
                scoped_targets.append((domains,prefixes,urls))
            if not code or code.strip() in {"/* Insert code here... */", "/* Insira o código aqui... */"}:
                continue
            if domains or prefixes or urls:
                sections.append({"code":code,"domains":domains,"url_prefixes":prefixes,"urls":urls})
            else:
                unscoped.append(code)
        # UserCSS exports often put the real CSS in an unscoped section after a placeholder scoped section.
        if unscoped and scoped_targets:
            domains,prefixes,urls = scoped_targets[0]
            for code in unscoped:
                sections.append({"code":code,"domains":domains,"url_prefixes":prefixes,"urls":urls,"inferred_scope":True})
        elif unscoped:
            skipped.append({"id": style.get("id"), "name": name, "reason": "CSS global sem alvo seguro"})
        if not sections:
            continue
        warnings=[]
        for sec in sections:
            warnings.extend(_css_warnings(sec["code"]))
        entries.append({
            "id": int(style.get("id", 0) or 0), "name": name, "enabled": bool(style.get("enabled", True)),
            "update_date": int(style.get("updateDate", 0) or 0), "sections": sections,
            "warnings": sorted(set(warnings)),
        })
    # Resolve requested conflicts by keeping latest. Vatican News is explicitly pinned to ID 1.
    def portal_keys(entry):
        keys=set()
        for sec in entry["sections"]:
            keys.update(sec.get("domains", []))
            for url in sec.get("url_prefixes", []) + sec.get("urls", []):
                keys.add(normalize_host(urlparse(url).hostname or ""))
        return {k for k in keys if k}
    discard_ids=set()
    conflict_groups=[]
    by_portal={}
    for e in entries:
        for key in portal_keys(e): by_portal.setdefault(key,[]).append(e)
    known={"cartacapital.com.br","cmjornal.pt","africanews.com"}
    for portal,group in by_portal.items():
        uniq={e["id"]:e for e in group}.values()
        uniq=list(uniq)
        if portal=="vaticannews.va":
            for e in uniq:
                if e["id"] != 1: discard_ids.add(e["id"])
        elif portal in known and len(uniq)>1:
            winner=max(uniq,key=lambda e:(e["update_date"],e["id"]))
            for e in uniq:
                if e["id"]!=winner["id"]: discard_ids.add(e["id"])
            conflict_groups.append({"portal":portal,"winner":winner["id"],"discarded":[e["id"] for e in uniq if e["id"]!=winner["id"]],"rule":"mais recente"})
    entries=[e for e in entries if e["id"] not in discard_ids]
    report={"styles_found":len(styles),"imported":len(entries),"skipped":skipped,"resolved_conflicts":conflict_groups,"discarded_ids":sorted(discard_ids)}
    return entries, report


def save_registry(entries: list[dict], report: dict | None = None) -> None:
    REGISTRY_FILE.write_text(json.dumps({"version":1,"entries":entries,"last_import_report":report or {}}, ensure_ascii=False, indent=2), encoding="utf-8")


def load_registry() -> dict:
    if not REGISTRY_FILE.exists() and BUNDLED_STYLUS_FILE.exists():
        try:
            entries, report = parse_stylus_export(json.loads(BUNDLED_STYLUS_FILE.read_text(encoding="utf-8")))
            save_registry(entries, report)
        except Exception:
            pass
    if not REGISTRY_FILE.exists(): return {"version":1,"entries":[],"last_import_report":{}}
    try: return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except Exception: return {"version":1,"entries":[],"last_import_report":{}}


def match_registry(url: str) -> dict:
    registry=load_registry(); host=normalize_host(urlparse(url).hostname or "")
    candidates=[]
    for entry in registry.get("entries",[]):
        matched_css=[]; score=0; reasons=[]
        for sec in entry.get("sections",[]):
            sec_score=0
            if url in sec.get("urls",[]): sec_score=100000; reasons.append("URL exata")
            for prefix in sec.get("url_prefixes",[]):
                if url.startswith(prefix) and 50000+len(prefix)>sec_score:
                    sec_score=50000+len(prefix); reasons.append("prefixo de URL")
            if host in [normalize_host(x) for x in sec.get("domains",[])]:
                sec_score=max(sec_score,10000); reasons.append("domínio")
            if sec_score:
                matched_css.append(sec.get("code","")); score=max(score,sec_score)
        if matched_css:
            candidates.append({"id":entry.get("id"),"name":entry.get("name"),"update_date":entry.get("update_date",0),"score":score,"css":"\n\n".join(matched_css),"warnings":entry.get("warnings",[]),"reason":", ".join(sorted(set(reasons)))})
    candidates.sort(key=lambda x:(x["score"],x["update_date"]), reverse=True)
    if not candidates: return {"status":"none","candidates":[]}
    top_score=candidates[0]["score"]
    top=[x for x in candidates if x["score"]==top_score]
    if len(top)>1:
        # A conflict is only ambiguous when equally specific profiles overlap.
        return {"status":"ambiguous","candidates":top}
    return {"status":"ok","profile":candidates[0],"candidates":candidates}


def load_profiles() -> dict[str, dict]:
    if not PROFILE_FILE.exists():
        return {}
    try:
        data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        profiles: dict[str, dict] = {}
        for key, value in data.items():
            if isinstance(value, str):
                profiles[str(key)] = {"css": value, "body_font_px": 68, "fidelity": 60}
            elif isinstance(value, dict):
                zoom = int(value.get("body_zoom", 200))
                profiles[str(key)] = {
                    "css": str(value.get("css", "")),
                    "body_font_px": int(value.get("body_font_px", max(46, min(96, round(zoom * 0.34))))),
                    "fidelity": int(value.get("fidelity", 60)),
                }
        return profiles
    except Exception:
        return {}


def save_profiles(profiles: dict[str, dict]) -> None:
    PROFILE_FILE.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_stylus_css(css: str) -> str:
    css = re.sub(r"/\*\s*==UserStyle==.*?==/UserStyle==\s*\*/", "", css, flags=re.DOTALL)
    wrapper = re.match(r"^\s*@-moz-document[^\{]*\{(.*)\}\s*$", css, flags=re.DOTALL)
    if wrapper:
        css = wrapper.group(1)
    css = re.sub(r"^\s*@-moz-document[^\{]*\{\s*$", "", css, flags=re.MULTILINE)
    return css.strip()


def fetch_html(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=25)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        if len(response.text) > 1000:
            return response.text
    except Exception:
        pass
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 900}, locale="pt-BR")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        source = page.content()
        browser.close()
        return source


def iter_json_ld(soup: BeautifulSoup) -> Iterable[dict]:
    for tag in soup.select('script[type="application/ld+json"]'):
        raw = tag.string or tag.get_text()
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in list(items):
            if isinstance(item, dict) and "@graph" in item:
                items.extend(x for x in (item.get("@graph") or []) if isinstance(x, dict))
            if isinstance(item, dict):
                yield item


def extract_article(url: str) -> Article:
    source = fetch_html(url)
    soup = BeautifulSoup(source, "html.parser")
    title = subtitle = author = published = image = article_body = ""
    images: list[EditorialImage] = []
    for obj in iter_json_ld(soup):
        kinds = obj.get("@type") if isinstance(obj.get("@type"), list) else [obj.get("@type")]
        if any(k in {"NewsArticle", "Article", "ReportageNewsArticle"} for k in kinds):
            title = title or clean_text(obj.get("headline"))
            subtitle = subtitle or clean_text(obj.get("description"))
            article_body = article_body or clean_text(obj.get("articleBody"))
            published = published or clean_text(obj.get("datePublished"))
            image_obj = obj.get("image")
            image_urls: list[str] = []
            if isinstance(image_obj, str): image_urls = [image_obj]
            elif isinstance(image_obj, list):
                for x in image_obj:
                    if isinstance(x, str): image_urls.append(x)
                    elif isinstance(x, dict) and x.get("url"): image_urls.append(x["url"])
            elif isinstance(image_obj, dict) and image_obj.get("url"): image_urls = [image_obj["url"]]
            if image_urls:
                image = image or image_urls[0]
                images.extend(EditorialImage(url=x) for x in image_urls)
            author_obj = obj.get("author")
            if isinstance(author_obj, dict): author = author or clean_text(author_obj.get("name"))
            elif isinstance(author_obj, list): author = author or ", ".join(clean_text(x.get("name")) for x in author_obj if isinstance(x, dict))
    h1 = soup.select_one("h1")
    title = title or (clean_text(h1.get_text(" ")) if h1 else "")
    if not subtitle:
        candidate = soup.select_one('[class*="subtitle"], [class*="description"], h1 + p')
        subtitle = clean_text(candidate.get_text(" ")) if candidate else ""
    paragraphs: list[str] = []
    selectors = ["article p", "main article p", '[class*="single-content"] p', '[class*="article-content"] p', '[data-testid*="article"] p']
    for selector in selectors:
        found = [clean_text(p.get_text(" ")) for p in soup.select(selector)]
        found = [p for p in found if len(p) >= 35]
        if len(found) >= 2:
            paragraphs = found
            break
    if not paragraphs and article_body:
        paragraphs = [clean_text(x) for x in re.split(r"\n{2,}|(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ\"])", article_body)]
        paragraphs = [p for p in paragraphs if len(p) >= 35]
    unique, seen = [], set()
    noise = ("leia mais", "assine", "publicidade", "veja também", "siga a")
    for paragraph in paragraphs:
        key = normalize_for_match(paragraph)
        if key in seen or any(key.startswith(x) for x in noise): continue
        seen.add(key); unique.append(paragraph)
    return Article(title, subtitle, author, published, image, unique, images)


def split_editor_text(text: str) -> list[str]:
    text = re.sub(r"^\s*\*?\d+[-–.]\s+.*?\*?\s*$", "", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"https?://\S+\s*$", "", text.strip(), flags=re.MULTILINE)
    return [clean_text(x) for x in re.split(r"\n\s*\n", text) if clean_text(x)]


def compare_paragraphs(editor_text: str, source_paragraphs: list[str]) -> list[dict]:
    normalized_sources = [normalize_for_match(x) for x in source_paragraphs]
    results = []
    for idx, paragraph in enumerate(split_editor_text(editor_text), start=1):
        if not source_paragraphs:
            results.append({"index": idx, "editor": paragraph, "source": "", "score": 0}); continue
        match = process.extractOne(normalize_for_match(paragraph), normalized_sources, scorer=fuzz.token_set_ratio)
        _, score, source_index = match
        results.append({"index": idx, "editor": paragraph, "source": source_paragraphs[source_index], "score": round(float(score), 1), "source_index": source_index})
    return results


def parse_highlight_markup(text: str) -> tuple[str, list[str]]:
    highlights: list[str] = []
    def repl(match: re.Match[str]) -> str:
        phrase = clean_text(match.group(1))
        if phrase: highlights.append(phrase)
        return match.group(1)
    plain = re.sub(r"\[\[(.+?)\]\]", repl, text, flags=re.DOTALL)
    return plain, highlights


def extract_editor_title(text: str) -> str:
    for line in text.splitlines():
        line = clean_text(line).strip("*")
        if not line: continue
        match = re.match(r"^\d+\s*[-–.]\s*(.+)$", line)
        return clean_text(match.group(1) if match else line)
    return ""


def parse_paragraph_plan(marked_text: str) -> tuple[str, list[dict]]:
    title = extract_editor_title(marked_text)
    cleaned = re.sub(r"^\s*\*?\d+[-–.]\s+.*?\*?\s*$", "", marked_text, count=1, flags=re.MULTILINE)
    cleaned = re.sub(r"https?://\S+\s*$", "", cleaned.strip(), flags=re.MULTILINE)
    plans = []
    for block in [x for x in re.split(r"\n\s*\n", cleaned) if clean_text(x)]:
        plain, highlights = parse_highlight_markup(block)
        plans.append({"plain": clean_text(plain), "highlights": highlights})
    return title, plans


def build_capture_plan(marked_text: str, mode: str) -> tuple[str, list[dict]]:
    title, paragraphs = parse_paragraph_plan(marked_text)
    return title, paragraphs


def click_cookie_consent(page) -> None:
    patterns = [r"aceitar( tudo)?", r"aceito", r"concordo", r"ok", r"entendi", r"i agree", r"accept( all)?", r"agree", r"got it", r"continuar"]
    for frame in page.frames:
        for raw in patterns:
            pattern = re.compile(rf"^{raw}$", re.I)
            for factory in (lambda: frame.get_by_role("button", name=pattern).first, lambda: frame.get_by_text(pattern, exact=True).first):
                try:
                    loc = factory()
                    if loc.count() and loc.is_visible(timeout=150):
                        loc.click(timeout=700); page.wait_for_timeout(150)
                except Exception:
                    pass


def extract_visual_model(url: str, stylus_css: str, viewport: dict) -> tuple[Article, VisualIdentity, list[EditorialImage]]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport, locale="pt-BR")
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(2200)
        click_cookie_consent(page)
        if stylus_css.strip(): page.add_style_tag(content=clean_stylus_css(stylus_css))
        page.wait_for_timeout(500)
        model = page.evaluate("""() => {
          const cs = el => el ? getComputedStyle(el) : null;
          const pick = (...sels) => { for (const s of sels) { const el=document.querySelector(s); if(el) return el; } return null; };
          const h1=pick('h1');
          const article=pick('article','main article','[class*="article-content"]','[class*="single-content"]','main');
          const bodyP=article ? [...article.querySelectorAll('p')].find(p=>p.innerText.trim().length>80) : null;
          const header=pick('header','[role="banner"]');
          const logo=header ? [...header.querySelectorAll('img,svg')].find(el=>{const r=el.getBoundingClientRect();return r.width>55&&r.height>20&&r.height<160}) : null;
          const meta = document.querySelector('meta[property="og:site_name"]');
          let vehicle=(meta&&meta.content)||document.title.split(/[|\-–]/).pop().trim()||location.hostname;
          let logoUrl=''; if(logo && logo.tagName==='IMG') logoUrl=logo.currentSrc||logo.src||'';
          const hc=cs(header), tc=cs(h1), bc=cs(bodyP), ac=cs(article), bodyc=cs(document.body);
          const images=[];
          const roots=[article].filter(Boolean);
          const candidates=roots.flatMap(root=>[...root.querySelectorAll('figure img, picture img, img')]);
          for(const img of candidates){
            const r=img.getBoundingClientRect(); const src=img.currentSrc||img.src||'';
            if(!src||r.width<350||r.height<180) continue;
            if(/logo|icon|avatar|sprite|banner|advert|ads/i.test(src+' '+img.className)) continue;
            const fig=img.closest('figure');
            const cap=fig ? fig.querySelector('figcaption') : null;
            images.push({url:src,caption:cap?cap.innerText.trim():'',credit:'',width:Math.round(r.width),height:Math.round(r.height),top:Math.round(r.top+scrollY)});
          }
          return {
            identity:{vehicle,logo_url:logoUrl,header_bg:hc?.backgroundColor||'#202124',header_fg:hc?.color||'#fff',title_font:tc?.fontFamily||'Arial, sans-serif',title_weight:tc?.fontWeight||'700',title_color:tc?.color||'#202124',body_font:bc?.fontFamily||'Arial, sans-serif',body_color:bc?.color||'#202124',body_bg:(ac?.backgroundColor&&ac.backgroundColor!=='rgba(0, 0, 0, 0)')?ac.backgroundColor:(bodyc?.backgroundColor||'#fff'),link_color:cs(article?.querySelector('a'))?.color||'#c40000'},
            images
          };
        }""")
        browser.close()
    article = extract_article(url)
    identity = VisualIdentity(**model["identity"])
    images = [EditorialImage(url=x["url"], caption=x.get("caption", ""), credit=x.get("credit", ""), width=x.get("width", 0), height=x.get("height", 0)) for x in model["images"]]
    # Deduplicate while preserving order.
    seen: set[str] = set(); dedup: list[EditorialImage] = []
    for img in images + article.images:
        key = img.url.split("?")[0]
        if not key or key in seen: continue
        seen.add(key); dedup.append(img)
    identity, _brand = apply_brand_profile(identity, url)
    return article, identity, dedup[:12]


def data_uri(url: str) -> str:
    if not url: return ""
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        mime = r.headers.get("Content-Type", "").split(";")[0] or mimetypes.guess_type(url)[0] or "image/jpeg"
        return f"data:{mime};base64,{base64.b64encode(r.content).decode('ascii')}"
    except Exception:
        return url


def phrase_ranges(text: str, phrases: list[str]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    folded = text.casefold()
    cursor = 0
    for phrase in phrases:
        needle = phrase.casefold()
        pos = folded.find(needle, cursor)
        if pos < 0:
            pos = folded.find(needle)
        if pos >= 0:
            ranges.append((pos, pos + len(phrase)))
            cursor = pos + len(phrase)
    return ranges


def highlight_chunk_html(full_text: str, chunk_start: int, chunk_end: int, active_phrases: list[str]) -> str:
    chunk = full_text[chunk_start:chunk_end]
    local_ranges: list[tuple[int, int]] = []
    for start, end in phrase_ranges(full_text, active_phrases):
        a, b = max(start, chunk_start), min(end, chunk_end)
        if a < b:
            local_ranges.append((a - chunk_start, b - chunk_start))
    local_ranges.sort()
    out: list[str] = []
    cursor = 0
    for a, b in local_ranges:
        if a < cursor:
            a = cursor
        if a >= b:
            continue
        out.append(html.escape(chunk[cursor:a]))
        out.append('<mark class="nc-highlight">' + html.escape(chunk[a:b]) + '</mark>')
        cursor = b
    out.append(html.escape(chunk[cursor:]))
    return ''.join(out)


def render_template_page(identity: VisualIdentity, width: int, height: int, fidelity: int, kind: str, content: dict, body_font_px: int) -> str:
    logo = data_uri(identity.logo_url)
    header_height = max(72, min(150, round(height * identity.header_height_ratio)))
    logo_html = f'<img class="source-logo" src="{html.escape(logo, quote=True)}" alt="">' if logo else f'<div class="source-fallback">{html.escape(identity.vehicle or "Fonte")}</div>'
    if kind == "title":
        title = html.escape(content.get("title", ""))
        body = f'<section class="title-stage"><h1 id="fit-title">{title}</h1></section>'
    elif kind == "image":
        src = data_uri(content.get("url", ""))
        caption = html.escape(content.get("caption", ""))
        credit = html.escape(content.get("credit", ""))
        cap = f'<div class="caption">{caption}{(" — "+credit) if credit else ""}</div>' if caption or credit else ''
        body = f'<section class="image-stage"><div class="image-box"><img id="editorial-image" src="{html.escape(src, quote=True)}" alt=""></div>{cap}</section>'
    else:
        paragraph_html = content.get("paragraph_html", "")
        body = f'<section class="text-stage"><article><p>{paragraph_html}</p></article></section>'
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}} html,body{{margin:0;width:{width}px;height:{height}px;overflow:hidden;background:{identity.body_bg};color:{identity.body_color}}}
body{{font-family:{identity.body_font};}}
.source-header{{height:{header_height}px;background:{identity.header_bg};color:{identity.header_fg};display:flex;align-items:center;justify-content:{"center" if identity.header_align=="center" else "flex-start"};padding:0 {max(26,round(width*.035))}px;border-bottom:{identity.divider_size}px solid {identity.accent};}}
.source-logo{{height:{round(header_height*.55*identity.logo_scale)}px;width:auto;max-width:{round(width*.88)}px;object-fit:contain;filter:{identity.logo_filter};transform-origin:{"center center" if identity.header_align=="center" else "left center"}}}
.source-fallback{{font-size:{round(header_height*.3)}px;font-weight:700;white-space:nowrap}}
main{{height:{height-header_height}px;position:relative}}
.title-stage{{height:100%;padding:{round(height*.045)}px {round(width*.055)}px {round(height*.085)}px;display:flex;align-items:center}}
h1{{font-family:{identity.title_font};font-weight:{identity.title_weight};color:{identity.title_color};line-height:1.02;letter-spacing:-.025em;margin:0;overflow-wrap:anywhere;width:100%}}
.text-stage{{height:100%;padding:{round(height*.065)}px {round(width*.07)}px;display:flex;align-items:center;justify-content:center;overflow:hidden}}
.text-stage article{{width:100%;max-width:{round(width*.9)}px;margin:0 auto}}
.text-stage p{{font-size:{body_font_px}px;font-weight:{identity.body_weight};font-variation-settings:"wght" {identity.body_weight};font-synthesis:weight;line-height:1.32;letter-spacing:-.006em;margin:0;color:{identity.body_color}}}
.nc-highlight{{background:#ffe132;color:inherit;border-radius:.10em;padding:0;margin:0;box-shadow:.08em .10em .13em rgba(0,0,0,.20);box-decoration-break:clone;-webkit-box-decoration-break:clone}}
.image-stage{{height:100%;padding:{round(height*.018)}px {round(width*.022)}px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:{round(height*.012)}px}}
.image-box{{width:100%;flex:1;min-height:0;display:flex;align-items:center;justify-content:center;overflow:hidden}}
.image-stage img{{width:100%;height:100%;object-fit:contain;display:block}}
.caption{{width:100%;font-size:{max(18,round(body_font_px*.28))}px;line-height:1.2;color:{identity.body_color};opacity:.84;padding:0 {round(width*.012)}px}}
</style></head><body><header class="source-header">{logo_html}</header><main>{body}</main>
<script>
if(document.getElementById('fit-title')){{const h=document.getElementById('fit-title');const stage=h.parentElement;const reserve=Math.max(54,Math.round({height}*.065));let lo=30,hi=210,best=30;while(lo<=hi){{const mid=Math.floor((lo+hi)/2);h.style.fontSize=mid+'px';const fits=h.scrollHeight<=Math.max(1,stage.clientHeight-reserve)&&h.scrollWidth<=stage.clientWidth;if(fits){{best=mid;lo=mid+1}}else hi=mid-1}}h.style.fontSize=best+'px';}}
</script></body></html>'''


def pagination_measure_page(identity: VisualIdentity, width: int, height: int, fidelity: int, body_font_px: int, paragraph: str) -> str:
    tokens = []
    for match in re.finditer(r'\S+\s*', paragraph, flags=re.UNICODE):
        tokens.append((match.start(), match.end(), match.group(0)))
    spans = ''.join(f'<span class="tok" data-s="{a}" data-e="{b}">{html.escape(token)}</span>' for a, b, token in tokens)
    logo = data_uri(identity.logo_url)
    header_height = max(72, min(150, round(height * identity.header_height_ratio)))
    logo_html = f'<img class="source-logo" src="{html.escape(logo, quote=True)}" alt="">' if logo else ''
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}}html,body{{margin:0;width:{width}px;height:{height}px;overflow:hidden;background:{identity.body_bg}}}
body{{font-family:{identity.body_font}}}.source-header{{height:{header_height}px;background:{identity.header_bg};display:flex;align-items:center;justify-content:{"center" if identity.header_align=="center" else "flex-start"};padding:0 {max(26,round(width*.035))}px;border-bottom:{identity.divider_size}px solid {identity.accent}}}.source-logo{{height:{round(header_height*.55*identity.logo_scale)}px;width:auto;max-width:{round(width*.88)}px;object-fit:contain;filter:{identity.logo_filter};transform-origin:{"center center" if identity.header_align=="center" else "left center"}}}
main{{height:{height-header_height}px}}.text-stage{{height:100%;padding:{round(height*.065)}px {round(width*.07)}px;overflow:hidden}}article{{width:100%;max-width:{round(width*.9)}px;margin:0 auto}}p{{font-size:{body_font_px}px;font-weight:{identity.body_weight};font-variation-settings:"wght" {identity.body_weight};font-synthesis:weight;line-height:1.32;letter-spacing:-.006em;margin:0;color:{identity.body_color}}}.tok{{white-space:pre-wrap}}
</style></head><body><header class="source-header">{logo_html}</header><main><section class="text-stage"><article><p>{spans}</p></article></section></main></body></html>'''


def measure_paragraph_layout(page, identity: VisualIdentity, width: int, height: int, fidelity: int, body_font_px: int, paragraph: str) -> dict:
    page.set_content(pagination_measure_page(identity, width, height, fidelity, body_font_px, paragraph), wait_until="load")
    page.wait_for_timeout(60)
    result = page.evaluate("""() => {
      const spans=[...document.querySelectorAll('.tok')];
      if(!spans.length) return null;
      const stage=document.querySelector('.text-stage');
      const bottom=stage.getBoundingClientRect().bottom;
      const lines=[];
      for(const sp of spans){
        const r=sp.getBoundingClientRect();
        let line=lines.find(x=>Math.abs(x.top-r.top)<2);
        if(!line){line={top:r.top,bottom:r.bottom,start:Number(sp.dataset.s),end:Number(sp.dataset.e)};lines.push(line)}
        else{line.bottom=Math.max(line.bottom,r.bottom);line.end=Number(sp.dataset.e)}
      }
      lines.sort((a,b)=>a.top-b.top);
      const visibleCount=Math.max(1,lines.filter(x=>x.bottom<=bottom+1).length);
      return {lines,visibleCount};
    }""")
    if not result or not result.get("lines"):
        return {"lines": [{"start": 0, "end": len(paragraph)}], "visible_count": 1}
    return {"lines": result["lines"], "visible_count": max(1, int(result.get("visibleCount", 1)))}


def line_for_offset(lines: list[dict], offset: int, prefer_end: bool = False) -> int:
    for idx, line in enumerate(lines):
        if prefer_end:
            if offset <= int(line["end"]):
                return idx
        elif int(line["start"]) <= offset < int(line["end"]):
            return idx
    return max(0, len(lines) - 1)


def window_chars(lines: list[dict], start_line: int, end_line: int) -> tuple[int, int]:
    return int(lines[start_line]["start"]), int(lines[end_line]["end"])


def choose_highlight_window(current_end_line: int, phrase_start_line: int, phrase_end_line: int, visible_count: int, total_lines: int) -> tuple[int, int]:
    # Prefer the normal one-line overlap. If the complete highlight would not fit,
    # move just enough to keep the whole phrase visible, then use the remaining
    # space below it to make the frame feel full.
    start = current_end_line
    if phrase_end_line - start + 1 > visible_count:
        start = phrase_start_line
    max_start = max(0, total_lines - visible_count)
    start = min(max(0, start), max_start)
    if phrase_start_line < start:
        start = phrase_start_line
    if phrase_end_line >= start + visible_count:
        start = max(0, phrase_end_line - visible_count + 1)
    end = min(total_lines - 1, start + visible_count - 1)
    return start, end


def generate_reconstructed_frames(url: str, marked_text: str, mode: str, width: int, height: int, stylus_css: str, body_font_px: int, fidelity: int, include_images: bool) -> Path:
    editor_title, paragraphs = build_capture_plan(marked_text, mode)
    article, identity, images = extract_visual_model(url, stylus_css, {"width": width, "height": height})
    title = editor_title or article.title
    job_id = uuid.uuid4().hex[:10]
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height}, locale="pt-BR")
        index = 0
        page.set_content(render_template_page(identity, width, height, fidelity, "title", {"title": title}, body_font_px), wait_until="load")
        page.wait_for_timeout(180)
        page.screenshot(path=str(job_dir / f"frame_{index:03d}_titulo.png")); index += 1

        if include_images and images:
            for img_idx, img in enumerate(images):
                page.set_content(render_template_page(identity, width, height, fidelity, "image", asdict(img), body_font_px), wait_until="load")
                try:
                    page.wait_for_function("() => { const i=document.getElementById('editorial-image'); return i && i.complete; }", timeout=5000)
                except Exception:
                    pass
                valid = page.evaluate("() => { const i=document.getElementById('editorial-image'); return !!(i && i.naturalWidth>80 && i.naturalHeight>80); }")
                if not valid:
                    continue
                page.screenshot(path=str(job_dir / f"frame_{index:03d}_foto_{img_idx+1:02d}.png")); index += 1

        for p_index, paragraph in enumerate(paragraphs, start=1):
            plain = paragraph["plain"]
            highlights = paragraph["highlights"]
            layout = measure_paragraph_layout(page, identity, width, height, fidelity, body_font_px, plain)
            lines = layout["lines"]
            visible_count = layout["visible_count"]
            total_lines = len(lines)

            highlight_items = []
            search_cursor = 0
            folded = plain.casefold()
            for h_index, phrase in enumerate(highlights, start=1):
                needle = phrase.casefold()
                pos = folded.find(needle, search_cursor)
                if pos < 0:
                    pos = folded.find(needle)
                if pos < 0:
                    continue
                end_pos = pos + len(phrase)
                search_cursor = end_pos
                highlight_items.append({
                    "index": h_index, "phrase": phrase, "start": pos, "end": end_pos,
                    "start_line": line_for_offset(lines, pos),
                    "end_line": line_for_offset(lines, max(pos, end_pos - 1), prefer_end=True),
                })

            current_start = 0
            current_end = min(total_lines - 1, visible_count - 1)
            next_h = 0
            active_global: list[str] = []
            frame_page = 1

            while current_start < total_lines:
                chunk_start, chunk_end = window_chars(lines, current_start, current_end)
                inherited_active = [] if mode == "individual" else [
                    ph for ph in active_global
                    if any(a < chunk_end and b > chunk_start for a, b in phrase_ranges(plain, [ph]))
                ]
                clean_content = {"paragraph_html": highlight_chunk_html(plain, chunk_start, chunk_end, inherited_active)}
                page.set_content(render_template_page(identity, width, height, fidelity, "text", clean_content, body_font_px), wait_until="load")
                page.wait_for_timeout(60)
                state_name = "base" if inherited_active else "limpo"
                page.screenshot(path=str(job_dir / f"frame_{index:03d}_p{p_index:02d}_pg{frame_page:02d}_{state_name}.png")); index += 1

                repositioned = False
                while next_h < len(highlight_items):
                    item = highlight_items[next_h]
                    if item["start_line"] > current_end:
                        break
                    if item["end_line"] > current_end or item["start_line"] < current_start:
                        new_start, new_end = choose_highlight_window(
                            current_end, item["start_line"], item["end_line"], visible_count, total_lines
                        )
                        if new_start != current_start or new_end != current_end:
                            current_start, current_end = new_start, new_end
                            frame_page += 1
                            repositioned = True
                            break
                    active_global.append(item["phrase"])
                    visible_active = [item["phrase"]] if mode == "individual" else [
                        ph for ph in active_global
                        if any(a < chunk_end and b > chunk_start for a, b in phrase_ranges(plain, [ph]))
                    ]
                    highlighted = {"paragraph_html": highlight_chunk_html(plain, chunk_start, chunk_end, visible_active)}
                    page.set_content(render_template_page(identity, width, height, fidelity, "text", highlighted, body_font_px), wait_until="load")
                    page.wait_for_timeout(60)
                    page.screenshot(path=str(job_dir / f"frame_{index:03d}_p{p_index:02d}_pg{frame_page:02d}_g{item['index']:02d}.png")); index += 1
                    next_h += 1

                if repositioned:
                    continue
                if current_end >= total_lines - 1:
                    break
                current_start = current_end
                current_end = min(total_lines - 1, current_start + visible_count - 1)
                frame_page += 1
        browser.close()
    manifest = {
        "source_url": url,
        "vehicle": identity.vehicle,
        "fidelity": fidelity,
        "body_font_px": body_font_px,
        "images_included": len(images) if include_images else 0,
        "frames": index,
        "pagination": "single sequential pass; clean frame then highlights; one-line overlap",
    }
    (job_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    archive = shutil.make_archive(str(job_dir), "zip", root_dir=job_dir)
    return Path(archive)




def _strip_title_markup(line: str) -> str:
    value = clean_text(line).strip().strip("*").strip()
    match = re.match(r"^(?:not[ií]cia\s*)?(\d+)\s*[-–.:)]\s*(.+)$", value, flags=re.I)
    return clean_text(match.group(2) if match else value)


def parse_batch_input(raw_text: str) -> tuple[list[dict], list[str]]:
    """Parse blocks in the form title + marked body + URL. The URL closes each item."""
    lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    jobs: list[dict] = []
    errors: list[str] = []
    buffer: list[str] = []
    url_re = re.compile(r"https?://[^\s<>]+", re.I)
    for line_no, line in enumerate(lines, start=1):
        matches = list(url_re.finditer(line))
        if not matches:
            buffer.append(line)
            continue
        # A URL closes the current article. Text after it starts the next one.
        before = line[:matches[0].start()].strip()
        if before:
            buffer.append(before)
        url = matches[0].group(0).rstrip(".,;)")
        nonempty = [x for x in buffer if clean_text(x)]
        if not nonempty:
            errors.append(f"Link na linha {line_no} sem título e texto anteriores: {url}")
        else:
            title = _strip_title_markup(nonempty[0])
            body_lines = buffer[buffer.index(nonempty[0]) + 1:]
            body = "\n".join(body_lines).strip()
            if not body:
                errors.append(f"Notícia {len(jobs)+1}: texto vazio antes de {url}")
            jobs.append({
                "number": len(jobs) + 1,
                "title": title,
                "body": body,
                "marked_text": f"*{len(jobs)+1}- {title}*\n\n{body}\n\n{url}",
                "url": url,
            })
        buffer = []
        after = line[matches[0].end():].strip()
        if after:
            buffer.append(after)
    if any(clean_text(x) for x in buffer):
        errors.append("Há texto no final sem um link que encerre a notícia.")
    if not jobs and not errors:
        errors.append("Nenhuma notícia foi reconhecida. Use: título, texto e link ao final de cada notícia.")
    return jobs, errors


def validate_batch_jobs(raw_text: str) -> dict:
    jobs, errors = parse_batch_input(raw_text)
    results = []
    for job in jobs:
        style = match_registry(job["url"])
        item = {
            "number": job["number"], "title": job["title"], "url": job["url"],
            "style_status": style.get("status"), "style": style.get("profile"),
            "style_candidates": style.get("candidates", []), "warnings": [], "errors": [],
        }
        if style.get("status") == "none":
            item["warnings"].append("Nenhum perfil Stylus encontrado; será usada a identidade extraída do site.")
        elif style.get("status") == "ambiguous":
            item["errors"].append("Há mais de um estilo igualmente específico; escolha um perfil antes de gerar.")
        try:
            article = extract_article(job["url"])
            comparison = compare_paragraphs(job["body"], article.paragraphs)
            low = [x for x in comparison if x["score"] < 65]
            item["source_title"] = article.title
            item["paragraphs"] = len(comparison)
            item["images"] = len(article.images)
            item["minimum_match"] = min((x["score"] for x in comparison), default=0)
            if low:
                item["warnings"].append(f"{len(low)} parágrafo(s) tiveram correspondência inferior a 65% com a página original.")
        except Exception as exc:
            item["errors"].append(f"Não foi possível ler a página: {exc}")
        results.append(item)
    return {"jobs": jobs, "results": results, "errors": errors, "ok": not errors and not any(x["errors"] for x in results)}


def generate_batch_archive(raw_text: str, width: int, height: int, mode: str, body_font_px: int, fidelity: int, include_images: bool) -> Path:
    validated = validate_batch_jobs(raw_text)
    if validated["errors"]:
        raise ValueError(" ".join(validated["errors"]))
    blocking = [f"N{x['number']}: {'; '.join(x['errors'])}" for x in validated["results"] if x["errors"]]
    if blocking:
        raise ValueError(" | ".join(blocking))
    batch_id = uuid.uuid4().hex[:10]
    batch_dir = OUTPUT_DIR / f"batch_{batch_id}"
    batch_dir.mkdir(parents=True)
    batch_manifest = {"items": [], "settings": {"width": width, "height": height, "mode": mode, "body_font_px": body_font_px, "include_images": include_images}}
    profiles = load_profiles()
    for job, check in zip(validated["jobs"], validated["results"]):
        domain = domain_from_url(job["url"])
        manual = profiles.get(domain, {})
        brand = load_brand_profiles().get(brand_key_for_url(job["url"]), {})
        auto_css = (check.get("style") or {}).get("css", "")
        css = manual.get("css", auto_css)
        font_px = int(brand.get("body_font_px", manual.get("body_font_px", body_font_px)))
        item_fidelity = 100
        archive = generate_reconstructed_frames(job["url"], job["marked_text"], mode, width, height, css, font_px, item_fidelity, include_images)
        target = batch_dir / f"N{job['number']}"
        target.mkdir()
        shutil.unpack_archive(str(archive), str(target))
        batch_manifest["items"].append({"folder": target.name, "number": job["number"], "title": job["title"], "url": job["url"], "marked_text": job["marked_text"], "style": (check.get("style") or {}).get("name", "extraído automaticamente")})
    (batch_dir / "manifest.json").write_text(json.dumps(batch_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    archive_path = Path(shutil.make_archive(str(batch_dir), "zip", root_dir=batch_dir))
    LATEST_BATCH_FILE.write_text(batch_dir.name, encoding="utf-8")
    return archive_path


@app.post("/api/batch/validate")
def api_batch_validate():
    data = request.get_json(force=True)
    raw_text = data.get("raw_text", "")
    return jsonify(validate_batch_jobs(raw_text))


@app.post("/api/batch/generate")
def api_batch_generate():
    data = request.get_json(force=True)
    try:
        archive = generate_batch_archive(
            data.get("raw_text", ""),
            max(640, min(3840, int(data.get("width", 1406)))),
            max(480, min(2160, int(data.get("height", 1080)))),
            data.get("mode", "cumulative"),
            max(36, min(120, int(data.get("body_font_px", 68)))),
            100,
            bool(data.get("include_images", True)),
        )
        return send_file(archive, as_attachment=True, download_name="news_batch_frames.zip", mimetype="application/zip")
    except Exception as exc:
        return jsonify(error=f"Erro ao gerar o lote: {exc}"), 500




def registry_css_for_domain(domain: str) -> str:
    domain = normalize_host(domain)
    pieces = []
    for entry in load_registry().get("entries", []):
        for sec in entry.get("sections", []):
            domains = [normalize_host(x) for x in sec.get("domains", [])]
            prefixes = sec.get("url_prefixes", [])
            urls = sec.get("urls", [])
            if domain in domains or any(normalize_host(urlparse(x).hostname or "") == domain for x in prefixes + urls):
                code = sec.get("code", "").strip()
                if code:
                    pieces.append(f"/* {entry.get('name','Stylus')} · ID {entry.get('id','')} */\n{code}")
    return "\n\n".join(dict.fromkeys(pieces))


def discover_logo_candidates(site_url: str) -> list[dict]:
    if not site_url.startswith(("http://", "https://")):
        site_url = "https://" + site_url.lstrip("/")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
    response = requests.get(site_url, timeout=18, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    found = []
    def add(raw, label, score):
        if not raw or raw.startswith("data:"):
            return
        url = urljoin(response.url, raw)
        if not url.startswith(("http://", "https://")):
            return
        ext = urlparse(url).path.lower()
        bonus = 16 if ext.endswith('.svg') else 10 if ext.endswith(('.png','.webp')) else 0
        if any(x in url.lower() for x in ('logo','brand','marca','header')):
            bonus += 18
        found.append({"url": url, "label": label, "score": score + bonus})
    for rel, score in (("logo",95),("apple-touch-icon",45),("icon",30)):
        for tag in soup.find_all("link", rel=lambda v: v and rel in " ".join(v if isinstance(v,list) else [v]).lower()):
            add(tag.get("href"), f"link rel={rel}", score)
    for prop, score in (("og:logo",100),("og:image",40),("twitter:image",35)):
        tag=soup.find("meta", attrs={"property":prop}) or soup.find("meta", attrs={"name":prop})
        if tag: add(tag.get("content"), prop, score)
    for img in soup.find_all("img"):
        attrs=" ".join([str(img.get("class", "")), img.get("id", ""), img.get("alt", ""), img.get("src", "")]).lower()
        if any(k in attrs for k in ("logo","brand","marca","cabecalho","header")):
            add(img.get("src") or img.get("data-src") or img.get("data-lazy-src"), img.get("alt") or "imagem do cabeçalho", 75)
    unique={}
    for item in found:
        if item["url"] not in unique or item["score"]>unique[item["url"]]["score"]:
            unique[item["url"]]=item
    return sorted(unique.values(), key=lambda x:(-x["score"], x["url"]))[:12]


@app.get("/api/brands")
def api_brands():
    profiles=load_brand_profiles()
    registry=load_registry().get("entries",[])
    known=set(profiles)
    for e in registry:
        for sec in e.get("sections",[]):
            known.update(normalize_host(x) for x in sec.get("domains",[]) if x)
    rows=[]
    for key in sorted(known):
        p=dict(profiles.get(key,{}))
        rows.append({"key":key,"name":p.get("name",key),"profile":p,"configured":bool(p)})
    return jsonify(items=rows)

@app.get("/api/brands/<path:key>")
def api_brand_get(key):
    key=normalize_host(key); profiles=load_brand_profiles()
    profile=dict(profiles.get(key,{"name":key,"header_mode":"auto_capture","primary":"#202124","secondary":"#ffffff","header_fg":"#ffffff","logo_scale":0.64,"header_height_ratio":0.095,"divider_size":5,"title_font":"Arial, sans-serif","body_font":"Arial, sans-serif","body_font_px":68,"body_weight":"400","stylus_css":"","logo_url":""}))
    if not profile.get("stylus_css"):
        profile["stylus_css"] = registry_css_for_domain(key)
    profile.setdefault("logo_url", "")
    return jsonify(key=key, profile=profile)

@app.post("/api/brands/<path:key>")
def api_brand_save(key):
    key=normalize_host(key); data=request.get_json(force=True) or {}; profiles=load_brand_profiles()
    clean={
      "name":clean_text(data.get("name")) or key,
      "header_mode":data.get("header_mode","auto_capture"),
      "primary":data.get("primary","#202124"),"secondary":data.get("secondary","#ffffff"),"header_fg":data.get("header_fg","#ffffff"),
      "logo_scale":max(.25,min(3.0,float(data.get("logo_scale",.64)))),
      "header_height_ratio":max(.055,min(.18,float(data.get("header_height_ratio",.095)))),
      "header_align":data.get("header_align","left"),"divider_size":max(0,min(12,int(data.get("divider_size",5)))),"logo_filter":data.get("logo_filter","none"),
      "title_font":data.get("title_font","Arial, sans-serif"),"title_weight":data.get("title_weight","700"),
      "title_color":data.get("title_color","#202124"),"body_font":data.get("body_font","Arial, sans-serif"),
      "body_color":data.get("body_color","#202124"),"body_bg":data.get("body_bg","#ffffff"),
      "body_weight":str(max(100,min(900,int(data.get("body_weight",400))))),
      "body_font_px":max(36,min(120,int(data.get("body_font_px",68)))),
      "stylus_css":data.get("stylus_css",""),
      "logo_url":data.get("logo_url","")
    }
    profiles[key]=clean; save_brand_profiles(profiles)
    return jsonify(ok=True,key=key,profile=clean)

@app.delete("/api/brands/<path:key>")
def api_brand_delete(key):
    key=normalize_host(key); profiles=load_brand_profiles(); profiles.pop(key,None); save_brand_profiles(profiles); return jsonify(ok=True)

@app.post("/api/brands/preview")
def api_brand_preview():
    data=request.get_json(force=True) or {}; key=normalize_host(data.get("key","preview.local")); profile=data.get("profile",{})
    ident=VisualIdentity(vehicle=profile.get("name",key),logo_url=data.get("logo_url","") or profile.get("logo_url",""),header_bg=profile.get("primary","#202124"),header_fg=profile.get("header_fg",profile.get("secondary","#fff")),title_font=profile.get("title_font","Arial, sans-serif"),title_weight=profile.get("title_weight","700"),title_color=profile.get("title_color","#202124"),body_font=profile.get("body_font","Arial, sans-serif"),body_weight=str(profile.get("body_weight","400")),body_color=profile.get("body_color","#202124"),body_bg=profile.get("body_bg","#fff"),accent=profile.get("secondary","#fff"),header_mode=profile.get("header_mode","custom_theme"),logo_scale=float(profile.get("logo_scale",.64)),header_height_ratio=float(profile.get("header_height_ratio",.095)),header_align=profile.get("header_align","left"),divider_size=int(profile.get("divider_size",5)),logo_filter=profile.get("logo_filter","none"))
    kind=data.get("kind","title")
    content={"title":data.get("title","Título de exemplo para conferir a identidade do veículo"),"paragraph_html":data.get("paragraph_html",'Este é um parágrafo de exemplo com <mark class="nc-highlight">um trecho grifado</mark> para conferir fonte, corpo, espaçamento e cores.')}
    return render_template_page(ident,1406,1080,100,kind,content,int(profile.get("body_font_px",68)))


@app.post("/api/brands/logo-scan")
def api_brand_logo_scan():
    data=request.get_json(force=True) or {}
    key=normalize_host(data.get("key", ""))
    url=clean_text(data.get("url")) or ("https://"+key if key else "")
    if not url:
        return jsonify(error="Informe o domínio ou a URL do veículo."),400
    try:
        candidates=discover_logo_candidates(url)
        return jsonify(ok=True,key=key,url=url,candidates=candidates)
    except Exception as exc:
        return jsonify(error=f"Não foi possível pesquisar os logos: {exc}"),400

@app.post("/api/brands/logo-scan-all")
def api_brand_logo_scan_all():
    profiles=load_brand_profiles(); results=[]
    for key, profile in profiles.items():
        if profile.get("logo_url"):
            results.append({"key":key,"status":"mantido","logo_url":profile["logo_url"]}); continue
        try:
            candidates=discover_logo_candidates("https://"+key)
            if candidates:
                profile["logo_url"]=candidates[0]["url"]
                results.append({"key":key,"status":"encontrado","logo_url":profile["logo_url"]})
            else:
                results.append({"key":key,"status":"não encontrado"})
        except Exception as exc:
            results.append({"key":key,"status":"erro","error":str(exc)})
    save_brand_profiles(profiles)
    return jsonify(ok=True,results=results)

@app.get("/api/batches/latest")
def api_latest_batch():
    if not LATEST_BATCH_FILE.exists():
        return jsonify(items=[], batch=None)
    name = LATEST_BATCH_FILE.read_text(encoding="utf-8").strip()
    root = OUTPUT_DIR / name
    if not root.exists():
        return jsonify(items=[], batch=None)
    manifest = {}
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
    meta = {x.get("folder"): x for x in manifest.get("items", [])}
    items = []
    for folder in sorted([x for x in root.iterdir() if x.is_dir()], key=lambda x: x.name):
        frames = sorted(x.name for x in folder.glob("*.png"))
        item_meta = meta.get(folder.name, {})
        items.append({
            "folder": folder.name,
            "number": item_meta.get("number"),
            "title": item_meta.get("title", folder.name),
            "frames": [f"/api/batches/{name}/{folder.name}/{fn}" for fn in frames],
            "download": f"/api/batches/{name}/{folder.name}/download",
            "open_folder": f"/api/batches/{name}/{folder.name}/open-folder",
        })
    return jsonify(batch=name, items=items, download=f"/api/batches/{name}/download")


@app.get("/api/batches/<batch>/<folder>/<filename>")
def api_batch_image(batch, folder, filename):
    safe = (OUTPUT_DIR / batch / folder / filename).resolve()
    base = OUTPUT_DIR.resolve()
    if base not in safe.parents or not safe.exists():
        return jsonify(error="Arquivo não encontrado"), 404
    response = send_file(safe)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


def _safe_export_name(value: str, limit: int = 70) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return (value or "noticia")[:limit].rstrip("_")


@app.get("/api/batches/<batch>/<folder>/download")
def api_news_download(batch, folder):
    root = (OUTPUT_DIR / batch).resolve()
    target = (root / folder).resolve()
    base = OUTPUT_DIR.resolve()
    if base not in target.parents or not target.is_dir():
        return jsonify(error="Notícia não encontrada"), 404
    title = folder
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            item = next((x for x in manifest.get("items", []) if x.get("folder") == folder), None)
            if item:
                title = item.get("title") or title
        except Exception:
            pass
    number_match = re.search(r"\d+", folder)
    number = int(number_match.group()) if number_match else 0
    filename = f"N{number:02d}_{_safe_export_name(title)}.zip"
    temp_base = TEMP_DIR / f"download_{batch}_{folder}"
    archive_path = Path(shutil.make_archive(str(temp_base), "zip", root_dir=root, base_dir=folder))
    return send_file(archive_path, as_attachment=True, download_name=filename, mimetype="application/zip")


@app.get("/api/batches/<batch>/download")
def api_batch_download(batch):
    root = (OUTPUT_DIR / batch).resolve()
    base = OUTPUT_DIR.resolve()
    if base not in root.parents or not root.exists():
        return jsonify(error="Lote não encontrado"), 404
    archive = Path(str(root) + ".zip")
    if not archive.exists():
        archive = Path(shutil.make_archive(str(root), "zip", root_dir=root))
    return send_file(archive, as_attachment=True, download_name="news_batch_frames.zip")


def _open_local_path(path: Path) -> None:
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        import subprocess
        subprocess.Popen(["open", str(path)])
    else:
        import subprocess
        subprocess.Popen(["xdg-open", str(path)])


@app.post("/api/batches/<batch>/<folder>/open-folder")
def api_open_news_folder(batch, folder):
    target = (OUTPUT_DIR / batch / folder).resolve()
    base = OUTPUT_DIR.resolve()
    if base not in target.parents or not target.is_dir():
        return jsonify(error="Pasta não encontrada"), 404
    try:
        _open_local_path(target)
        return jsonify(ok=True)
    except Exception as exc:
        return jsonify(error=f"Não foi possível abrir a pasta: {exc}"), 400


@app.post("/api/batches/<batch>/<folder>/<filename>/open")
def api_open_current_png(batch, folder, filename):
    target = (OUTPUT_DIR / batch / folder / filename).resolve()
    base = OUTPUT_DIR.resolve()
    if base not in target.parents or not target.is_file() or target.suffix.lower() != ".png":
        return jsonify(error="PNG não encontrado"), 404
    try:
        _open_local_path(target)
        return jsonify(ok=True)
    except Exception as exc:
        return jsonify(error=f"Não foi possível abrir o PNG: {exc}"), 400


@app.get("/api/system/info")
def system_info():
    return jsonify({
        "data_root": str(DATA_ROOT),
        "profiles": str(PROFILES_DIR),
        "brand_themes": str(BRAND_THEMES_DIR),
        "logos": str(LOGOS_DIR),
        "fonts": str(FONTS_DIR),
        "temporary": str(TEMP_DIR),
        "cache": str(CACHE_DIR),
        "projects": str(PROJECTS_DIR),
        "output": str(OUTPUT_DIR),
    })


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _human_size(value: int) -> str:
    size=float(value)
    for unit in ("B","KB","MB","GB","TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024


def _clear_dir(path: Path) -> None:
    if not path.exists():
        return
    for item in path.iterdir():
        if item.is_dir(): shutil.rmtree(item, ignore_errors=True)
        else:
            try: item.unlink()
            except OSError: pass


@app.get("/api/storage")
def api_storage():
    latest_name = LATEST_BATCH_FILE.read_text(encoding="utf-8").strip() if LATEST_BATCH_FILE.exists() else ""
    latest_dir = OUTPUT_DIR / latest_name if latest_name else None
    values = {
        "profiles": _dir_size(PROFILES_DIR),
        "themes": _dir_size(BRAND_THEMES_DIR),
        "logos": _dir_size(LOGOS_DIR),
        "web_cache": _dir_size(CACHE_DIR),
        "temporary": _dir_size(TEMP_DIR),
        "projects": _dir_size(PROJECTS_DIR),
        "last_batch": _dir_size(latest_dir) if latest_dir else 0,
        "output": _dir_size(OUTPUT_DIR),
    }
    return jsonify(values=values, human={k:_human_size(v) for k,v in values.items()}, total=sum(values.values()), total_human=_human_size(sum(values.values())))


@app.post("/api/storage/clean")
def api_storage_clean():
    data=request.get_json(force=True) or {}; target=data.get("target")
    if target == "cache":
        _clear_dir(CACHE_DIR); _clear_dir(TEMP_DIR)
    elif target == "previews":
        _clear_dir(OUTPUT_DIR)
        if LATEST_BATCH_FILE.exists(): LATEST_BATCH_FILE.unlink()
    elif target == "projects":
        days=max(1,int(data.get("days",30)))
        import time
        cutoff=time.time()-days*86400
        for p in PROJECTS_DIR.iterdir():
            try:
                if p.stat().st_mtime < cutoff:
                    shutil.rmtree(p,ignore_errors=True) if p.is_dir() else p.unlink()
            except OSError: pass
    elif target == "all":
        _clear_dir(CACHE_DIR); _clear_dir(TEMP_DIR); _clear_dir(OUTPUT_DIR); _clear_dir(PROJECTS_DIR)
        if LATEST_BATCH_FILE.exists(): LATEST_BATCH_FILE.unlink()
    else:
        return jsonify(error="Ação de limpeza desconhecida."),400
    return api_storage()


@app.post("/api/brands/font-scan")
def api_brand_font_scan():
    data=request.get_json(force=True) or {}; url=clean_text(data.get("url"))
    if not url: return jsonify(error="Informe a URL do veículo."),400
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True); page=browser.new_page(viewport={"width":1406,"height":1080})
            page.goto(url,wait_until="domcontentloaded",timeout=60000); page.wait_for_timeout(1200)
            result=page.evaluate("""() => {
              const pick=(sels)=>{for(const s of sels){const e=document.querySelector(s);if(e&&e.textContent.trim()){const c=getComputedStyle(e);return {selector:s,fontFamily:c.fontFamily,fontWeight:c.fontWeight,fontStyle:c.fontStyle}}}return null};
              return {title:pick(['article h1','main h1','h1']),body:pick(['article p','main article p','main p'])};
            }""")
            browser.close()
        return jsonify(ok=True,**result)
    except Exception as exc:
        return jsonify(error=f"Não foi possível detectar as fontes: {exc}"),400


@app.post("/api/batches/latest/rerender")
def api_rerender_latest_news():
    data=request.get_json(force=True) or {}; folder=clean_text(data.get("folder"))
    if not LATEST_BATCH_FILE.exists(): return jsonify(error="Nenhum lote disponível."),404
    name=LATEST_BATCH_FILE.read_text(encoding="utf-8").strip(); root=OUTPUT_DIR/name; manifest_path=root/"manifest.json"
    if not manifest_path.exists(): return jsonify(error="O lote não possui dados para renderização parcial."),400
    manifest=json.loads(manifest_path.read_text(encoding="utf-8")); item=next((x for x in manifest.get("items",[]) if x.get("folder")==folder),None)
    if not item or not item.get("marked_text"): return jsonify(error="A notícia selecionada não possui roteiro salvo."),400
    settings=manifest.get("settings",{}); url=item["url"]; domain=domain_from_url(url); manual=load_profiles().get(domain,{})
    brand=load_brand_profiles().get(brand_key_for_url(url),{})
    style=match_registry(url); css=manual.get("css",(style.get("profile") or {}).get("css","")); font_px=int(brand.get("body_font_px",manual.get("body_font_px",settings.get("body_font_px",68))))
    archive=generate_reconstructed_frames(url,item["marked_text"],settings.get("mode","cumulative"),int(settings.get("width",1406)),int(settings.get("height",1080)),css,font_px,100,bool(settings.get("include_images",True)))
    temp=TEMP_DIR/(folder+"_rerender"); _clear_dir(temp); temp.mkdir(parents=True,exist_ok=True); shutil.unpack_archive(str(archive),str(temp))
    target=root/folder; backup=TEMP_DIR/(folder+"_backup"); _clear_dir(backup)
    if target.exists(): shutil.move(str(target),str(backup))
    shutil.move(str(temp),str(target)); _clear_dir(backup)
    zip_path=Path(str(root)+".zip")
    if zip_path.exists(): zip_path.unlink()
    shutil.make_archive(str(root),"zip",root_dir=root)
    return jsonify(ok=True,folder=folder,frames=len(list(target.glob("*.png"))))


@app.get("/")
def index(): return render_template("index.html")


@app.post("/api/extract")
def api_extract():
    data = request.get_json(force=True)
    url = clean_text(data.get("url")); editor_text = data.get("editor_text", "")
    if not url.startswith(("http://", "https://")): return jsonify(error="Informe um link válido."), 400
    try:
        article = extract_article(url); profiles = load_profiles(); domain = domain_from_url(url)
        manual = profiles.get(domain, {})
        resolved = match_registry(url)
        auto_css = resolved.get("profile", {}).get("css", "") if resolved.get("status") == "ok" else ""
        profile = {"css": manual.get("css", auto_css), "body_font_px": manual.get("body_font_px", 68), "fidelity": manual.get("fidelity", 60)}
        return jsonify(article=asdict(article), comparison=compare_paragraphs(editor_text, article.paragraphs), domain=domain, stylus_css=profile.get("css", ""), body_font_px=profile.get("body_font_px", 68), fidelity=profile.get("fidelity", 60), stylus_resolution=resolved)
    except Exception as exc: return jsonify(error=f"Não foi possível extrair a notícia: {exc}"), 500


@app.post("/api/profile")
def api_profile():
    data = request.get_json(force=True)
    domain = clean_text(data.get("domain")).lower().removeprefix("www.")
    if not domain: return jsonify(error="Domínio inválido."), 400
    profiles = load_profiles()
    profiles[domain] = {"css": data.get("css", ""), "body_font_px": max(36, min(120, int(data.get("body_font_px", 68)))), "fidelity": max(40, min(90, int(data.get("fidelity", 60))))}
    save_profiles(profiles)
    return jsonify(ok=True, domain=domain)



@app.get("/api/stylus-registry")
def api_stylus_registry():
    registry=load_registry()
    return jsonify(count=len(registry.get("entries",[])), report=registry.get("last_import_report",{}), entries=[{"id":e.get("id"),"name":e.get("name"),"update_date":e.get("update_date"),"warnings":e.get("warnings",[])} for e in registry.get("entries",[])])


@app.post("/api/stylus-import")
def api_stylus_import():
    uploaded=request.files.get("file")
    if not uploaded: return jsonify(error="Selecione um arquivo JSON exportado pelo Stylus."),400
    try:
        payload=json.loads(uploaded.read().decode("utf-8-sig"))
        entries,report=parse_stylus_export(payload)
        save_registry(entries,report)
        return jsonify(ok=True,count=len(entries),report=report)
    except Exception as exc:
        return jsonify(error=f"Não foi possível importar o arquivo: {exc}"),400


@app.post("/api/generate")
def api_generate():
    data = request.get_json(force=True)
    url = clean_text(data.get("url")); marked_text = data.get("marked_text", "")
    if not url.startswith(("http://", "https://")): return jsonify(error="Informe o link da notícia."), 400
    if not split_editor_text(marked_text): return jsonify(error="O texto está vazio."), 400
    try:
        archive = generate_reconstructed_frames(
            url, marked_text, data.get("mode", "cumulative"),
            max(640, min(3840, int(data.get("width", 1406)))),
            max(480, min(2160, int(data.get("height", 1080)))),
            data.get("stylus_css", ""),
            max(36, min(120, int(data.get("body_font_px", 68)))),
            100,
            bool(data.get("include_images", True)),
        )
        return send_file(archive, as_attachment=True, download_name="news_reconstruction_frames.zip", mimetype="application/zip")
    except Exception as exc: return jsonify(error=f"Erro ao gerar os quadros: {exc}"), 500


if __name__ == "__main__": app.run(host="127.0.0.1", port=5050, debug=False)
