#!/usr/bin/env python3
"""Generate a static Arabic SEO blog from public Google Docs."""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://ahmedzakaria14.github.io/napolifakhama"
SITE_NAME = "أفران ومشبات الفخامة"
PHONE = "0556182491"
WHATSAPP = "966556182491"
TODAY = dt.date.today().isoformat()
ARTICLES: list[dict[str, Any]] = json.loads((Path(__file__).with_name("blog_articles.json")).read_text(encoding="utf-8"))
BASE_PAGES = [("", "1.0", "weekly"), ("products/", "0.9", "monthly"), ("why-al-fakhama/", "0.8", "monthly"), ("about/", "0.7", "monthly"), ("manufacturing/", "0.8", "monthly"), ("testimonials/", "0.6", "monthly"), ("contact/", "0.8", "monthly"), ("blog/", "0.9", "weekly")]


def e(value: str) -> str:
    return html.escape(value, quote=True)


def download_doc(doc_id: str, retries: int = 3) -> str:
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; FakhamaBlogGenerator/1.0)"})
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read()
            text = data.decode("utf-8-sig", errors="replace")
            if "<html" in text[:500].lower():
                raise RuntimeError("Google returned HTML instead of document text")
            return text
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Could not download Google Doc {doc_id}: {last_error}")


def normalize_lines(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    return [re.sub(r"\s+", " ", line).strip() for line in text.split("\n") if line.strip()]


def looks_like_h2(line: str) -> bool:
    if len(line) > 105:
        return False
    if line in {"الخاتمة", "الأسئلة الشائعة", "أسئلة شائعة", "ملخص المقال"}:
        return True
    starters = ("الفرق بين", "ما الذي", "ما هي", "ما أهمية", "مواصفات", "أنواع", "اختيار", "كيف تختار", "كيف تحدد", "كيف يتم", "مراحل", "أهمية", "تشطيبات", "مميزات", "معايير", "العوامل", "متطلبات", "خدمات", "تصميم", "تنفيذ", "تفصيل", "طريقة", "نصائح", "أخطاء", "مشكلات", "حلول", "سعر", "أسعار", "متى", "أيهما", "لماذا", "دور", "خطوات", "مواد", "نظام", "أفضل")
    return line.startswith(starters) or (line.endswith("؟") and len(line) < 80)


def extract_structure(lines: list[str]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    blocks: list[dict[str, str]] = []
    toc: list[dict[str, str]] = []
    in_faq = False
    heading_count = 0
    for line in lines[1:]:
        if line in {"الأسئلة الشائعة", "أسئلة شائعة"}:
            in_faq, kind = True, "h2"
        elif re.match(r"^[0-9٠-٩]+[.)-]\s+", line) and len(line) <= 110:
            kind = "h3"
        elif in_faq and line.endswith("؟") and len(line) <= 120:
            kind = "h3"
        elif looks_like_h2(line):
            kind = "h2"
        else:
            kind = "p"
        if kind in {"h2", "h3"}:
            heading_count += 1
            anchor = f"section-{heading_count}"
            block = {"type": kind, "text": line, "id": anchor}
            blocks.append(block); toc.append(block)
        else:
            blocks.append({"type": "p", "text": line})
    return blocks, toc


def first_paragraph(blocks: list[dict[str, str]]) -> str:
    return next((b["text"] for b in blocks if b["type"] == "p"), "مقالات متخصصة في الأفران والمشبات والشوايات بالرياض.")


def truncate(text: str, length: int = 158) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= length:
        return text
    return text[: length - 1].rsplit(" ", 1)[0] + "…"


def article_url(article: dict[str, Any]) -> str:
    return f"{SITE_URL}/blog/{article['slug']}/"


def related_articles(article: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    same = [a for a in ARTICLES if a["slug"] != article["slug"] and a["category"] == article["category"]]
    other = [a for a in ARTICLES if a["slug"] != article["slug"] and a["category"] != article["category"]]
    return (same + other)[:limit]


def add_contextual_links(text: str, current: dict[str, Any]) -> str:
    escaped, replacements = e(text), 0
    for target in ARTICLES:
        if target["slug"] == current["slug"]:
            continue
        for phrase in [target["keyword"], target["title"]]:
            escaped_phrase = e(phrase)
            if escaped_phrase in escaped and replacements < 2:
                escaped = escaped.replace(escaped_phrase, f'<a href="../{e(target["slug"])}/" target="_blank" rel="noopener">{escaped_phrase}</a>', 1)
                replacements += 1
                break
    return escaped


def faq_pairs(blocks: list[dict[str, str]]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    in_faq = False; question: str | None = None; answers: list[str] = []
    for block in blocks:
        if block["type"] == "h2" and block["text"] in {"الأسئلة الشائعة", "أسئلة شائعة"}:
            in_faq = True; continue
        if not in_faq:
            continue
        if block["type"] in {"h2", "h3"} and block["text"].endswith("؟"):
            if question and answers:
                pairs.append((question, " ".join(answers)))
            question, answers = block["text"], []
        elif block["type"] == "p" and question:
            answers.append(block["text"])
    if question and answers:
        pairs.append((question, " ".join(answers)))
    return pairs[:8]


def nav(prefix: str) -> str:
    return f'''<header class="site-header"><div class="topbar"><div class="container"><span>توصيل وتركيب داخل الرياض وضواحيها 🇸🇦</span><a href="tel:{PHONE}">☎&nbsp;{PHONE}</a></div></div><nav class="nav container" aria-label="التنقل الرئيسي"><a class="brand" href="{prefix}"><span class="brand-mark">♨</span><span><strong>{SITE_NAME}</strong><small>أفران ومشبات وشوايات بالرياض</small></span></a><div class="nav-links" data-nav-links><a href="{prefix}">الرئيسية</a><a href="{prefix}products/">منتجاتنا</a><a href="{prefix}why-al-fakhama/">لماذا الفخامة؟</a><a href="{prefix}about/">من نحن</a><a href="{prefix}manufacturing/">طريقة التصنيع</a><a href="{prefix}blog/" aria-current="page">المدونة</a><a href="{prefix}contact/">اتصل بنا</a></div><div class="nav-actions"><button class="icon-btn" type="button" data-theme-toggle aria-label="تفعيل الوضع الليلي">☾</button><a class="btn btn-whatsapp btn-sm desktop-wa" href="https://wa.me/{WHATSAPP}" target="_blank" rel="noopener">واتساب</a><button class="icon-btn menu-btn" type="button" data-menu-toggle aria-expanded="false" aria-label="فتح القائمة">☰</button></div></nav></header>'''


def footer(prefix: str) -> str:
    return f'''<footer class="site-footer"><div class="container"><div class="footer-grid"><div class="footer-about"><div class="brand"><span class="brand-mark">♨</span><span><strong class="footer-brand">{SITE_NAME}</strong><small>صناعة وتركيب في الرياض</small></span></div><p>مقالات وخدمات متخصصة في أفران نابولي والمطاعم والمشبات والشوايات بالرياض.</p></div><div><h2 class="footer-title">روابط مهمة</h2><ul class="footer-links"><li><a href="{prefix}products/">منتجاتنا</a></li><li><a href="{prefix}blog/">المدونة</a></li><li><a href="{prefix}manufacturing/">طريقة التصنيع</a></li><li><a href="{prefix}contact/">اتصل بنا</a></li></ul></div><div><h2 class="footer-title">تواصل معنا</h2><ul class="footer-links"><li><a href="tel:{PHONE}">{PHONE}</a></li><li><a href="https://wa.me/{WHATSAPP}" target="_blank" rel="noopener">واتساب</a></li><li>الرياض، السعودية</li></ul></div></div><div class="footer-bottom"><span>© 2026 {SITE_NAME}. جميع الحقوق محفوظة.</span><span class="credit">تم التطوير بواسطة <a href="https://nasharhub.com/" target="_blank" rel="noopener">NasharHub</a></span></div></div></footer><a class="floating floating-wa" href="https://wa.me/{WHATSAPP}" target="_blank" rel="noopener" aria-label="واتساب">◉</a><a class="floating floating-call" href="tel:{PHONE}" aria-label="اتصال">☎</a>'''


def render_article(article: dict[str, Any], raw_text: str) -> str:
    lines = normalize_lines(raw_text)
    if not lines:
        raise RuntimeError(f"Empty document: {article['doc_id']}")
    article["title"] = lines[0] or article["title"]
    blocks, toc = extract_structure(lines)
    description = truncate(first_paragraph(blocks))
    canonical = article_url(article); image_url = f"{SITE_URL}/assets/images/{article['image']}"
    keywords = ", ".join([article["keyword"], *article["related_keywords"]]); faqs = faq_pairs(blocks)
    toc_html = "".join(f'<li class="toc-{i["type"]}"><a href="#{i["id"]}" target="_blank" rel="noopener">{e(i["text"])}</a></li>' for i in toc)
    body_parts: list[str] = []; h2_count = 0; related = related_articles(article)
    for block in blocks:
        if block["type"] == "p":
            body_parts.append(f"<p>{add_contextual_links(block['text'], article)}</p>")
        elif block["type"] == "h2":
            h2_count += 1; body_parts.append(f'<h2 id="{block["id"]}">{e(block["text"])}</h2>')
            if h2_count == 2 and related:
                target = related[0]; body_parts.append(f'<p class="inline-related">اقرأ أيضًا: <a href="../{e(target["slug"])}/" target="_blank" rel="noopener">{e(target["title"])}</a></p>')
        else:
            body_parts.append(f'<h3 id="{block["id"]}">{e(block["text"])}</h3>')
    related_cards = "".join(f'<article class="blog-card reveal"><a class="blog-card-image" href="../{e(i["slug"])}/" target="_blank" rel="noopener"><img src="../../assets/images/{e(i["image"])}" alt="{e(i["title"])}" width="1200" height="800" loading="lazy"></a><div class="blog-card-body"><span class="blog-category">{e(i["category"])}</span><h3><a href="../{e(i["slug"])}/" target="_blank" rel="noopener">{e(i["title"])}</a></h3><p>{e(i["keyword"])}</p></div></article>' for i in related)
    graph: list[dict[str, Any]] = [{"@type":"BlogPosting","@id":canonical+"#article","headline":article["title"],"description":description,"image":[image_url],"datePublished":article["date"],"dateModified":TODAY,"inLanguage":"ar-SA","mainEntityOfPage":{"@type":"WebPage","@id":canonical},"author":{"@type":"Organization","name":SITE_NAME},"publisher":{"@type":"Organization","name":SITE_NAME,"url":SITE_URL+"/"},"keywords":keywords,"articleSection":article["category"]},{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"الرئيسية","item":SITE_URL+"/"},{"@type":"ListItem","position":2,"name":"المدونة","item":SITE_URL+"/blog/"},{"@type":"ListItem","position":3,"name":article["title"],"item":canonical}]}]
    if faqs:
        graph.append({"@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in faqs]})
    schema = json.dumps({"@context":"https://schema.org","@graph":graph}, ensure_ascii=False)
    wa_text = urllib.parse.quote("السلام عليكم، أريد عرض سعر بخصوص " + article["title"])
    return f'''<!doctype html><html lang="ar-SA" dir="rtl" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(article['title'])} | {SITE_NAME}</title><meta name="description" content="{e(description)}"><meta name="keywords" content="{e(keywords)}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="theme-color" content="#f36b2b"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ar-SA" href="{canonical}"><link rel="alternate" hreflang="x-default" href="{canonical}"><link rel="icon" href="../../favicon.svg" type="image/svg+xml"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet"><link rel="stylesheet" href="../../assets/css/styles.css"><link rel="stylesheet" href="../../assets/css/blog.css"><meta property="og:locale" content="ar_SA"><meta property="og:type" content="article"><meta property="og:site_name" content="{SITE_NAME}"><meta property="og:title" content="{e(article['title'])}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{image_url}"><meta property="article:published_time" content="{article['date']}"><meta property="article:modified_time" content="{TODAY}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema}</script></head><body><a class="skip-link" href="#article-content">انتقل إلى محتوى المقال</a>{nav('../../')}<main id="main"><section class="article-hero"><img src="../../assets/images/{e(article['image'])}" alt="{e(article['title'])}" width="1200" height="800" fetchpriority="high"><div class="article-hero-overlay"></div><div class="container article-hero-content"><nav class="breadcrumbs" aria-label="مسار الصفحة"><a href="../../">الرئيسية</a><span>›</span><a href="../">المدونة</a><span>›</span><span>{e(article['category'])}</span></nav><span class="blog-category">{e(article['category'])}</span><h1>{e(article['title'])}</h1><p>{e(description)}</p><div class="article-meta"><time datetime="{article['date']}">{article['date']}</time><span>قراءة متخصصة</span><span>{e(article['keyword'])}</span></div></div></section><section class="section article-section"><div class="container article-layout"><aside class="article-sidebar"><div class="toc-card"><h2>جدول المحتويات</h2><p>تُفتح عناصر الفهرس في علامة تبويب جديدة.</p><ol>{toc_html}</ol></div><div class="article-contact-card"><strong>تحتاج عرض سعر؟</strong><p>أرسل صورة الموقع والمقاسات التقريبية عبر واتساب.</p><a class="btn btn-whatsapp" href="https://wa.me/{WHATSAPP}?text={wa_text}" target="_blank" rel="noopener">تواصل واتساب</a></div></aside><article class="article-content" id="article-content">{''.join(body_parts)}<div class="article-cta"><h2>اطلب تنفيذًا يناسب مشروعك</h2><p>نصنع ونركب الأفران والمشبات والشوايات حسب مساحة الموقع وطبيعة التشغيل داخل الرياض وضواحيها.</p><div class="hero-actions"><a class="btn btn-whatsapp" href="https://wa.me/{WHATSAPP}" target="_blank" rel="noopener">واتساب {PHONE}</a><a class="btn btn-outline" href="tel:{PHONE}">اتصال مباشر</a></div></div></article></div></section><section class="section section-alt"><div class="container"><div class="section-head"><h2>مقالات <span class="accent">ذات صلة</span></h2><p>روابط داخلية تساعدك على مقارنة الخيارات والوصول إلى الخدمة المناسبة.</p></div><div class="blog-grid">{related_cards}</div></div></section></main>{footer('../../')}<script src="../../assets/js/main.js" defer></script></body></html>'''


def render_blog_index() -> str:
    cards = []
    for a in ARTICLES:
        search_text = e(a["title"] + " " + a["keyword"] + " " + " ".join(a["related_keywords"]))
        cards.append(f'<article class="blog-card reveal" data-category="{e(a["category"])}" data-search="{search_text}"><a class="blog-card-image" href="{e(a["slug"])}/"><img src="../assets/images/{e(a["image"])}" alt="{e(a["title"])}" width="1200" height="800" loading="lazy"></a><div class="blog-card-body"><div class="blog-card-meta"><span class="blog-category">{e(a["category"])}</span><time datetime="{a["date"]}">{a["date"]}</time></div><h2><a href="{e(a["slug"])}/">{e(a["title"])}</a></h2><p>{e(a["keyword"])}</p><a class="read-more" href="{e(a["slug"])}/">قراءة المقال <span aria-hidden="true">←</span></a></div></article>')
    schema = json.dumps({"@context":"https://schema.org","@type":"Blog","name":f"مدونة {SITE_NAME}","url":SITE_URL+"/blog/","inLanguage":"ar-SA","publisher":{"@type":"Organization","name":SITE_NAME},"blogPost":[{"@type":"BlogPosting","headline":a["title"],"url":article_url(a),"datePublished":a["date"]} for a in ARTICLES]}, ensure_ascii=False)
    return f'''<!doctype html><html lang="ar-SA" dir="rtl" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>مدونة أفران نابولي والمشبات بالرياض | {SITE_NAME}</title><meta name="description" content="دليل متخصص يضم 15 مقالًا عن أفران نابولي والمطاعم والمشبات والشوايات في الرياض، مع نصائح الاختيار والتصنيع والتركيب."><meta name="keywords" content="افران نابولي بالرياض, افران مطاعم بالرياض, مشبات بالرياض, شوايات مطاعم بالرياض"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1"><meta name="theme-color" content="#f36b2b"><link rel="canonical" href="{SITE_URL}/blog/"><link rel="icon" href="../favicon.svg" type="image/svg+xml"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet"><link rel="stylesheet" href="../assets/css/styles.css"><link rel="stylesheet" href="../assets/css/blog.css"><meta property="og:locale" content="ar_SA"><meta property="og:type" content="website"><meta property="og:title" content="مدونة أفران نابولي والمشبات بالرياض"><meta property="og:url" content="{SITE_URL}/blog/"><meta property="og:image" content="{SITE_URL}/assets/images/fakhama-pizza-oven-hero.webp"><script type="application/ld+json">{schema}</script></head><body><a class="skip-link" href="#blog-posts">انتقل إلى المقالات</a>{nav('../')}<main id="main"><section class="blog-hero"><div class="container"><span class="eyebrow">دليل الأفران والمشبات في الرياض</span><h1>مدونة أفران ومشبات <span class="gradient-text">الفخامة</span></h1><p>محتوى عملي يشرح المواصفات والأنواع ومراحل التنفيذ، ويربط كل موضوع بالخدمة الأنسب وفق خطة الكلمات المفتاحية.</p><div class="blog-stats"><span><strong>15</strong> مقالًا متخصصًا</span><span><strong>18</strong> مجموعة كلمات</span><span><strong>3</strong> أقسام رئيسية</span></div></div></section><section class="section" id="blog-posts"><div class="container"><div class="blog-toolbar"><label class="blog-search"><span>ابحث في المدونة</span><input type="search" data-blog-search placeholder="مثال: فرن نابولي أو مشبات حجر" aria-label="البحث في مقالات المدونة"></label><div class="blog-filters"><button class="active" type="button" data-blog-filter="الكل">الكل</button><button type="button" data-blog-filter="أفران نابولي والمطاعم">الأفران والمطاعم</button><button type="button" data-blog-filter="المشبات">المشبات</button><button type="button" data-blog-filter="الشوايات والتجهيزات">الشوايات والتجهيزات</button></div></div><div class="blog-grid" data-blog-grid>{''.join(cards)}</div><p class="blog-empty" data-blog-empty hidden>لا توجد مقالات مطابقة لعبارة البحث.</p></div></section><section class="cta"><div class="container"><h2>لم تجد الإجابة المناسبة؟</h2><p>أرسل تفاصيل مشروعك وصورة الموقع وسنساعدك على تحديد الفرن أو المشب المناسب.</p><a class="btn btn-whatsapp" href="https://wa.me/{WHATSAPP}" target="_blank" rel="noopener">واتساب {PHONE}</a></div></section></main>{footer('../')}<script src="../assets/js/main.js" defer></script><script src="../assets/js/blog.js" defer></script></body></html>'''


def write_sitemap() -> None:
    urls = [f"  <url><loc>{SITE_URL}/{path}</loc><lastmod>{TODAY}</lastmod><changefreq>{freq}</changefreq><priority>{priority}</priority></url>" for path, priority, freq in BASE_PAGES]
    urls += [f"  <url><loc>{article_url(a)}</loc><lastmod>{TODAY}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>" for a in ARTICLES]
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")


def main() -> int:
    blog_dir = ROOT / "blog"; blog_dir.mkdir(exist_ok=True); failures: list[str] = []
    for article in ARTICLES:
        try:
            text = download_doc(article["doc_id"]); target = blog_dir / article["slug"]; target.mkdir(parents=True, exist_ok=True)
            (target / "index.html").write_text(render_article(article, text), encoding="utf-8")
            print(f"Generated {article['slug']}")
        except Exception as exc:
            failures.append(f"{article['slug']}: {exc}")
    if failures:
        print("\n".join(failures), file=sys.stderr); return 1
    (blog_dir / "index.html").write_text(render_blog_index(), encoding="utf-8"); write_sitemap()
    print(f"Generated {len(ARTICLES)} articles and blog index"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
