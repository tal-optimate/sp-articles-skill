#!/usr/bin/env python3
"""Generate, preview and publish magazine posts ("cubes") on s-portal.co.il.

Subcommands:
  check                                          verify the WordPress + OpenAI connections (run first)
  parse   <article.txt>                          dry run: show how the article is parsed (no network)
  image   --prompt TEXT --out DIR [--n 2]        generate cover image options with OpenAI
  mock    <article.txt> --images A.jpg [B.jpg]   write a local preview page (cube + article) and open it
  create  <article.txt> --image PATH             upload image + create DRAFT article (category's post type)
  update  <post_id> <article.txt> [--image PATH] update an existing draft
  publish <post_id> [--at "DD.MM.YYYY HH:MM"]    publish now, or schedule (site-local time)
  verify  <post_id>                              check the article is live and shown in the visible grid

Credentials (never printed):
  WordPress: env SPORTAL_WP_AUTH ("user:application-password" or "Basic <base64>"), otherwise the
             Authorization header of any MCP server in ~/.claude.json whose URL is on s-portal.co.il.
  OpenAI:    env OPENAI_API_KEY. Image model: env OPENAI_IMAGE_MODEL (default gpt-image-1).
  Plugin install: both are also read from keys.json, which the plugin's SessionStart hook (save_keys.py)
             writes from the plugin settings form into ~/.claude/plugins/data/<plugin>/.
Standard library only; works on macOS, Linux and Windows.
"""
import argparse
import base64
import datetime as dt
import html
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import pathlib
import webbrowser

SITE = "https://s-portal.co.il"
API = SITE + "/wp-json/wp/v2"
MAGAZINE_URL = SITE + "/" + urllib.parse.quote("המגזין-שלנו") + "/"
OPENAI_URL = "https://api.openai.com/v1/images/generations"

# The visible magazine grid (Elementor widget 531ce36, JetEngine listing 10179) lists these JetEngine post
# types, one per category. Regular WordPress posts only appear in a grid that is hidden on every device.
CATEGORIES = {
    "תזונה נשים": "blog-women",
    "תזונה ספורט": "blog-sport",
    "תזונה ילדים": "blog-child",
    "מודעות והתנהגות אכילה": "blog-eating",
    "מטבח בריא": "blog-kitchen",
    "דיאטות נפוצות": "blog-diet",
    "המזונות המומלצים שלנו": "blog-food",
    "חגים ויציאה מהשגרה": "blog-holiday",
}
VISIBLE_LISTING = "jet-listing-grid--10179"
AUTHORS = {
    "sitemanager": 3,
    "sportal.digital@gmail.com": 4,
    "directorj": 2,
    "מרט רמפל": 6,
    "רוני": 5,
}
HEADER_KEYS = {
    "קטגוריה": "category", "category": "category",
    "כותרת": "title", "title": "title",
    "תקציר": "summary", "summary": "summary", "excerpt": "summary",
    "כותב": "author", "author": "author",
    "פרסום": "publish_at", "publish": "publish_at", "schedule": "publish_at",
}


# ---------------------------------------------------------------- parsing

def parse_article(text):
    lines = text.replace("\r\n", "\n").split("\n")
    fields, i = {}, 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"^([^:：]{2,20})\s*[:：]\s*(.*)$", line)
        key = HEADER_KEYS.get(m.group(1).strip().lower()) if m else None
        if key:
            fields[key] = m.group(2).strip()
            i += 1
        elif not line and not fields:
            i += 1  # leading blank lines
        elif not line:
            i += 1
            break  # blank line ends the header block
        else:
            break
    body = "\n".join(lines[i:]).strip()
    blocks = []
    for chunk in re.split(r"\n\s*\n", body):
        para = []
        for line in chunk.split("\n"):
            if re.match(r"^#{2,3}\s", line.strip()):  # a heading line is always its own block
                if para:
                    blocks.append("\n".join(para))
                    para = []
                blocks.append(line.strip())
            elif line.strip():
                para.append(line)
        if para:
            blocks.append("\n".join(para))
    fields["blocks"] = blocks
    return fields


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               lambda m: '<a href="%s">%s</a>' % (html.escape(m.group(2)), m.group(1)), s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", s)
    return s


def spacer(px):
    return ('<!-- wp:spacer {"height":"%dpx"} --><div style="height:%dpx" aria-hidden="true" '
            'class="wp-block-spacer"></div><!-- /wp:spacer -->' % (px, px))


def to_blocks(blocks):
    """Render in the same block style as reference post 10466 (paragraph/heading + spacers)."""
    out = []
    for n, b in enumerate(blocks):
        h = re.match(r"^(#{2,3})\s+(.*)$", b.strip(), re.S)
        if n:
            out.append(spacer(40 if h else 24))
        if h:
            level = len(h.group(1))
            attrs = "" if level == 2 else ' {"level":%d}' % level
            out.append("<!-- wp:heading%s --><h%d>%s</h%d><!-- /wp:heading -->"
                       % (attrs, level, inline(h.group(2).strip()), level))
        else:
            para = "<br>".join(inline(l.strip()) for l in b.split("\n"))
            out.append("<!-- wp:paragraph --><p>%s</p><!-- /wp:paragraph -->" % para)
    return "\n\n".join(out)


def parse_when(s):
    s = s.strip()
    for fmt in ("%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    sys.exit("Can't read publish time %r — use DD.MM.YYYY HH:MM" % s)


def resolve(fields):
    problems = []
    cat = fields.get("category", "").strip()
    cats = CATEGORIES.get(cat)
    if not cat:
        problems.append("missing category (קטגוריה) — ask the user")
    elif cats is None:
        problems.append("unknown category %r — known: %s" % (cat, ", ".join(CATEGORIES)))
    if not fields.get("title"):
        problems.append("missing title (כותרת)")
    if not fields.get("summary"):
        problems.append("missing summary (תקציר) — use the article's opening sentence(s), word for word")
    author = fields.get("author", "").strip()
    author_id = None  # None = the connected WordPress user
    if author:
        author_id = int(author) if author.isdigit() else AUTHORS.get(author.lower())
        if author_id is None:
            problems.append("unknown author %r — known: %s" % (author, ", ".join(AUTHORS)))
    if not fields["blocks"]:
        problems.append("empty article body")
    when = parse_when(fields["publish_at"]) if fields.get("publish_at") else None
    return cats, author_id, when, problems


# ---------------------------------------------------------------- credentials + http

def plugin_keys():
    """Keys saved by the plugin's settings form (see save_keys.py); empty when installed as a plain skill."""
    import glob
    for path in glob.glob(os.path.expanduser("~/.claude/plugins/data/*s-portal-magazine*/keys.json")):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    return {}


def openai_key():
    return os.environ.get("OPENAI_API_KEY", "").strip() or plugin_keys().get("openai_api_key", "")


def wp_auth():
    env = os.environ.get("SPORTAL_WP_AUTH", "").strip()
    keys = plugin_keys()
    if not env and keys.get("wp_user") and keys.get("wp_app_password"):
        env = "%s:%s" % (keys["wp_user"], keys["wp_app_password"])
    if env:
        if env.lower().startswith("basic "):
            return "Basic " + "".join(env[6:].split())
        return "Basic " + base64.b64encode(env.encode()).decode()
    try:
        with open(os.path.expanduser("~/.claude.json"), encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return None
    servers = list((cfg.get("mcpServers") or {}).values())
    for proj in (cfg.get("projects") or {}).values():
        servers += list((proj.get("mcpServers") or {}).values())
    for s in servers:
        if "s-portal.co.il" in str(s.get("url", "")):
            val = (s.get("headers") or {}).get("Authorization", "")
            if val.lower().startswith("basic"):
                return "Basic " + "".join(val[5:].split())  # tolerate stray newlines/spaces
    return None


def call(method, path, data=None, raw=None, headers=None):
    auth = wp_auth()
    if not auth:
        sys.exit("No WordPress connection found — re-enter the keys in the plugin settings (Configure), then restart Claude Code")
    url = path if path.startswith("http") else API + path
    h = {"Authorization": auth}
    if headers:
        h.update(headers)
    body = raw
    if data is not None:
        body = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        sys.exit("WordPress %s %s failed: HTTP %s %s" % (method, path, e.code, e.read().decode()[:500]))


def upload_image(path, alt):
    if path.isdigit():  # an image already in the media library
        return call("GET", "/media/%s?_fields=id,source_url" % path)
    if not os.path.isfile(path):
        sys.exit("Image not found: %s" % path)
    ext = os.path.splitext(path)[1].lower() or ".jpg"
    mime = mimetypes.guess_type("x" + ext)[0] or "image/jpeg"
    name = "magazine-%s%s" % (dt.datetime.now().strftime("%Y%m%d-%H%M%S"), ext)
    with open(path, "rb") as f:
        media = call("POST", "/media", raw=f.read(),
                     headers={"Content-Type": mime, "Content-Disposition": 'attachment; filename="%s"' % name})
    call("POST", "/media/%d" % media["id"], data={"alt_text": alt})
    return media


def post_payload(fields, cats, author_id, when):
    p = {
        "title": fields["title"],
        "content": to_blocks(fields["blocks"]),
        "excerpt": fields["summary"],
    }
    if author_id:
        p["author"] = author_id
    if when:
        p["date"] = when.strftime("%Y-%m-%dT%H:%M:00")  # site-local time; remembered for `publish`
    return p


def load(article_path):
    with open(article_path, encoding="utf-8") as f:
        fields = parse_article(f.read())
    cats, author_id, when, problems = resolve(fields)
    return fields, cats, author_id, when, problems


def find_type(pid):
    """REST base of the magazine article with this ID (the ID alone doesn't say which post type it is)."""
    for base in sorted(set(CATEGORIES.values())):
        req = urllib.request.Request("%s/%s/%d?context=edit&_fields=id" % (API, base, pid),
                                     headers={"Authorization": wp_auth()})
        try:
            urllib.request.urlopen(req, timeout=60).read()
            return base
        except urllib.error.HTTPError as e:
            if e.code != 404:
                sys.exit("WordPress GET %s/%d failed: HTTP %s" % (base, pid, e.code))
    sys.exit("No magazine article with ID %d (regular posts don't show on the magazine)" % pid)


def links(pid):
    return {"preview (login required)": "%s/?p=%d&preview=true" % (SITE, pid),
            "edit": "%s/wp-admin/post.php?post=%d&action=edit" % (SITE, pid)}


# ---------------------------------------------------------------- commands

def cmd_check(a):
    result = {}
    auth = wp_auth()
    if not auth:
        result["wordpress"] = "MISSING — no SPORTAL_WP_AUTH and no s-portal MCP server in ~/.claude.json"
    else:
        req = urllib.request.Request(API + "/users/me?context=edit", headers={"Authorization": auth})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                me = json.loads(r.read().decode())
            caps = me.get("capabilities", {})
            ok = caps.get("publish_posts") and caps.get("upload_files")
            result["wordpress"] = "OK — connected as %s (id %s)%s" % (
                me.get("name"), me.get("id"), "" if ok else " BUT missing publish/upload permission (needs Editor role)")
        except urllib.error.HTTPError as e:
            result["wordpress"] = "FAILED — HTTP %s (wrong user or application password?)" % e.code
    key = openai_key()
    if not key:
        result["openai"] = "MISSING — OPENAI_API_KEY is not set"
    else:
        req = urllib.request.Request("https://api.openai.com/v1/models", headers={"Authorization": "Bearer " + key})
        try:
            urllib.request.urlopen(req, timeout=30).read()
            result["openai"] = "OK — key works (image model: %s)" % os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
        except urllib.error.HTTPError as e:
            result["openai"] = "FAILED — HTTP %s (invalid key or no billing?)" % e.code
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(not v.startswith("OK") for v in result.values()):
        print("Setup needed — re-enter the keys in the plugin settings (Configure), then fully restart Claude Code")
        sys.exit(1)


def cmd_parse(a):
    fields, cats, author_id, when, problems = load(a.article)
    kinds = ["h%d" % len(re.match(r"^(#+)", b).group(1)) if b.startswith("#") else "p" for b in fields["blocks"]]
    print(json.dumps({
        "title": fields.get("title"), "summary": fields.get("summary"),
        "category": fields.get("category"), "post_type": cats,
        "author": fields.get("author") or "(connected WordPress user)", "author_id": author_id,
        "publish_at": when.strftime("%d.%m.%Y %H:%M") if when else "on approval (now)",
        "blocks": len(kinds), "block_types": kinds,
        "first_block": fields["blocks"][0][:120] if fields["blocks"] else None,
        "problems": problems,
    }, ensure_ascii=False, indent=2))


def cmd_image(a):
    key = openai_key()
    if not key:
        sys.exit("OPENAI_API_KEY is not set — re-enter it in the plugin settings (Configure), then restart Claude Code")
    model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
    payload = {"model": model, "prompt": a.prompt, "n": a.n, "size": a.size, "quality": a.quality,
               "output_format": "jpeg"}
    req = urllib.request.Request(OPENAI_URL, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            res = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit("OpenAI image generation failed: HTTP %s %s" % (e.code, e.read().decode()[:500]))
    os.makedirs(a.out, exist_ok=True)
    stamp = dt.datetime.now().strftime("%H%M%S")
    paths = []
    for n, item in enumerate(res.get("data", []), 1):
        path = os.path.join(a.out, "cover-%s-%d.jpg" % (stamp, n))
        if item.get("b64_json"):
            data = base64.b64decode(item["b64_json"])
        else:
            data = urllib.request.urlopen(item["url"], timeout=120).read()
        with open(path, "wb") as f:
            f.write(data)
        paths.append(os.path.abspath(path))
    print(json.dumps({"model": model, "images": paths}, ensure_ascii=False, indent=2))


MOCK_CSS = """
body{margin:0;background:#1D1E1B;color:#F4E9D9;font-family:Heebo,Arial,sans-serif;direction:rtl}
.wrap{max-width:980px;margin:0 auto;padding:32px 16px 64px}
h1.page{color:#C79F4D;font-weight:600;font-size:22px;margin:0 0 6px}
.note{color:#bba98c;font-size:14px;margin:0 0 28px}
.opts{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:28px;margin-bottom:48px}
.optlabel{color:#DAA124;font-weight:700;margin:0 0 8px}
.cube{background:#FFFBF5;color:#1D1E1B;border-radius:4px;overflow:hidden}
.cube img{width:100%;aspect-ratio:3/2;object-fit:cover;display:block}
.cube .in{padding:18px 20px 22px;text-align:center}
.cube h2{color:#A57F31;font-size:24px;line-height:1.3;margin:0 0 10px}
.cube p{font-size:16px;line-height:1.6;margin:0 0 12px}
.meta{font-size:13px;color:#7a6a55}
.article{background:#FFFBF5;color:#1D1E1B;border-radius:4px;padding:32px 28px;line-height:1.8;font-size:17px}
.article h1{color:#A57F31;margin-top:0}.article img{width:100%;border-radius:4px;margin-bottom:20px}
.article h2{margin:36px 0 12px}.article h3{margin:28px 0 10px}
"""


def cmd_mock(a):
    fields, cats, author_id, when, problems = load(a.article)
    t = html.escape(fields.get("title") or "(no title)")
    s = inline(fields.get("summary") or "(no summary)")
    meta = "%s · %s · %s" % (html.escape(fields.get("category") or "?"),
                             (when or dt.datetime.now()).strftime("%d.%m.%Y"),
                             html.escape(fields.get("author") or "המשתמש המחובר"))
    imgs = []
    for p in a.images:  # embed as data URIs so the preview works anywhere (even if forwarded)
        with open(p, "rb") as f:
            mime = mimetypes.guess_type(p)[0] or "image/jpeg"
            imgs.append("data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode()))
    cubes = "".join(
        '<div><p class="optlabel">תמונה %d</p><div class="cube"><img src="%s"><div class="in">'
        '<h2>%s</h2><p>%s</p><div class="meta">%s</div></div></div></div>'
        % (n, src, t, s, meta) for n, src in enumerate(imgs, 1))
    body = ""
    for b in fields["blocks"]:
        h = re.match(r"^(#{2,3})\s+(.*)$", b.strip(), re.S)
        body += ("<h%d>%s</h%d>" % (len(h.group(1)), inline(h.group(2)), len(h.group(1))) if h
                 else "<p>%s</p>" % "<br>".join(inline(l.strip()) for l in b.split("\n")))
    page = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>תצוגה מקדימה – %s</title>'
            '<style>%s</style></head><body><div class="wrap"><h1 class="page">תצוגה מקדימה – קובייה במגזין</h1>'
            '<p class="note">הדמיה בלבד (המראה באתר עשוי להיות מעט שונה). %s</p><div class="opts">%s</div>'
            '<h1 class="page">עמוד הכתבה</h1><div class="article"><img src="%s"><h1>%s</h1>%s</div>'
            '</div></body></html>') % (t, MOCK_CSS, "בחרו תמונה." if len(imgs) > 1 else "",
                                        cubes, imgs[0], t, body)
    out = os.path.abspath(a.out)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    if not a.no_open:
        webbrowser.open(pathlib.Path(out).as_uri())  # correct file:// URL on macOS and Windows (C:\...)
    print(json.dumps({"preview_file": out, "problems": problems}, ensure_ascii=False, indent=2))


def cmd_create(a):
    fields, cats, author_id, when, problems = load(a.article)
    if problems:
        sys.exit("Fix before creating:\n- " + "\n- ".join(problems))
    media = upload_image(a.image, fields["title"])
    p = post_payload(fields, cats, author_id, when)
    p.update(status="draft", featured_media=media["id"])
    post = call("POST", "/" + cats, data=p)
    print(json.dumps({"post_id": post["id"], "post_type": cats, "status": post["status"], "image_id": media["id"],
                      "image_url": media.get("source_url"), **links(post["id"])}, ensure_ascii=False, indent=2))


def cmd_update(a):
    fields, cats, author_id, when, problems = load(a.article)
    if problems:
        sys.exit("Fix before updating:\n- " + "\n- ".join(problems))
    p = post_payload(fields, cats, author_id, when)
    if a.image:
        p["featured_media"] = upload_image(a.image, fields["title"])["id"]
    base = find_type(a.post_id)
    if base != cats:
        sys.exit("Article %d is %s but the category needs %s — create a new article instead" % (a.post_id, base, cats))
    post = call("POST", "/%s/%d" % (base, a.post_id), data=p)
    print(json.dumps({"post_id": post["id"], "status": post["status"], **links(post["id"])},
                     ensure_ascii=False, indent=2))


def cmd_publish(a):
    base = find_type(a.post_id)
    cur = call("GET", "/%s/%d?context=edit" % (base, a.post_id))
    now_utc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    if a.at:
        when = parse_when(a.at)
        data = {"status": "future", "date": when.strftime("%Y-%m-%dT%H:%M:00")}
    elif cur.get("date_gmt") and dt.datetime.fromisoformat(cur["date_gmt"]) > now_utc + dt.timedelta(minutes=1):
        data = {"status": "future", "date_gmt": cur["date_gmt"]}  # schedule given at creation
    else:
        data = {"status": "publish", "date_gmt": now_utc.strftime("%Y-%m-%dT%H:%M:%S")}
    post = call("POST", "/%s/%d" % (base, a.post_id), data=data)
    print(json.dumps({"post_id": post["id"], "status": post["status"], "date (site time)": post["date"],
                      "url": post["link"]}, ensure_ascii=False, indent=2))
    if post["status"] == "future":
        print("Scheduled — it will appear on the magazine automatically at that time.")


def visible_ids(url):
    """Post IDs in the grid visitors actually see, and whether the response came from the page cache."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        page = r.read().decode("utf-8", "replace")
        cached = r.headers.get("x-cache", "")
    start = page.find(VISIBLE_LISTING)
    if start < 0:
        sys.exit("Visible magazine grid (%s) not found — the page layout changed" % VISIBLE_LISTING)
    return [int(x) for x in re.findall(r'data-post-id="(\d+)"', page[start:])], cached


def cmd_verify(a):
    base = find_type(a.post_id)
    post = call("GET", "/%s/%d?_fields=id,status,featured_media,link" % (base, a.post_id))
    fresh, _ = visible_ids(MAGAZINE_URL + "?nocache=%d" % dt.datetime.now().timestamp())
    # Visitors reach the page through differently-encoded URLs, each cached separately.
    lower = MAGAZINE_URL.replace(MAGAZINE_URL[len(SITE) + 1:], MAGAZINE_URL[len(SITE) + 1:].lower())
    cached, hit = visible_ids(lower)
    print(json.dumps({"magazine_url": urllib.parse.unquote(MAGAZINE_URL), "post_type": base,
                      "status": post["status"], "has_cover_image": bool(post.get("featured_media")),
                      "url": post["link"], "position_in_visible_grid": fresh.index(a.post_id) + 1
                      if a.post_id in fresh else None, "visible_grid_first": fresh[:3],
                      "cached_page_shows_it": a.post_id in cached, "cached_page": hit or "?"},
                     ensure_ascii=False, indent=2))
    if post["status"] != "publish":
        print("Not live yet (status: %s) — it isn't expected on the magazine until it's published." % post["status"])
    elif a.post_id not in cached:
        print("The cached copy visitors get is stale — purge the Cloudways cache (server 1432214, app 5348289).")


def main():
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to a codepage that can't print Hebrew
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("check"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("parse"); s.add_argument("article"); s.set_defaults(fn=cmd_parse)
    s = sub.add_parser("image"); s.add_argument("--prompt", required=True); s.add_argument("--out", required=True)
    s.add_argument("--n", type=int, default=2); s.add_argument("--size", default="1536x1024")
    s.add_argument("--quality", default="medium"); s.set_defaults(fn=cmd_image)
    s = sub.add_parser("mock"); s.add_argument("article"); s.add_argument("--images", nargs="+", required=True)
    s.add_argument("--out", default="magazine-preview.html"); s.add_argument("--no-open", action="store_true")
    s.set_defaults(fn=cmd_mock)
    s = sub.add_parser("create"); s.add_argument("article"); s.add_argument("--image", required=True, help="image file, or media ID to reuse")
    s.set_defaults(fn=cmd_create)
    s = sub.add_parser("update"); s.add_argument("post_id", type=int); s.add_argument("article")
    s.add_argument("--image"); s.set_defaults(fn=cmd_update)
    s = sub.add_parser("publish"); s.add_argument("post_id", type=int); s.add_argument("--at")
    s.set_defaults(fn=cmd_publish)
    s = sub.add_parser("verify"); s.add_argument("post_id", type=int); s.set_defaults(fn=cmd_verify)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
