---
name: s-portal-magazine-post
description: Turn an article + category into a new cube in the "המגזין שלנו" magazine on the Dr. Shawn Portal website (s-portal.co.il) — generates a matching cover image with AI, shows a preview, and publishes (or schedules) only after the user approves. Use this whenever the user wants to add, upload, post or schedule an article/cube/post/כתבה/מאמר to המגזין שלנו or the s-portal blog, even if they just paste Hebrew article text with a category, or say "תעלה את זה למגזין".
---

# s-portal magazine post

The magazine page (https://s-portal.co.il/המגזין-שלנו/, page 168) shows a JetEngine listing grid (listing 10179,
query 16 "לולאה-כולם", 9 cubes, newest first). Each cube is an article in the **category's own JetEngine post type**
(`blog-food`, `blog-women`, … — see the table), with a featured image, excerpt and title. Never edit the magazine
page itself. Don't create regular WordPress posts: they only appear in a second grid that is hidden on every device.
Reference article for "the same structure": **10523** (blog-food).

All site and image work goes through `scripts/magazine_post.py` (Python 3, standard library only, works on
macOS/Linux/Windows). It is installed as the `s-portal-magazine` plugin; use the full script path shown in the
commands below. On Windows, run it with `python` (or `py`) instead of `python3`.

## Rules the site owner set

- **Don't change the article's words** — body, headings and anything taken from it stay exactly as written.
  Converting their markup (`##`, `**bold**`, links) into WordPress blocks is fine. If something looks like a typo,
  point it out and let them decide.
- **Title: you decide.** If the article opens with a line that is clearly its title, use it (and drop it from the
  body). Otherwise propose a short, faithful title in the article's language, built from the article's own
  wording. The title is always shown in the preview for approval.
- **Summary (the text on the cube)**: the article's opening sentence or two, **word for word** (roughly 150–250
  characters, cut at a sentence end). If the user supplies one, use theirs.
- **The category comes from the user.** If it's missing or not in the table below, ask — don't guess.
- **Author**: the connected WordPress user by default (each person publishes under their own name), unless the
  user names someone.
- **Preview, then wait.** Nothing is created on the site until the user approves the preview. Approval for one
  article doesn't carry over to the next.
- The magazine's category tabs stay as they are (new posts showing in every tab is known and accepted).
- SEO (Yoast) fields stay empty.

## Workflow

### 0. Connections (first use, or when something fails)
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/s-portal-magazine-post/scripts/magazine_post.py" check
```
If WordPress or OpenAI isn't `OK`, the keys from the plugin's settings form haven't reached the script yet. In the
user's language, one step at a time: (1) if they just installed or changed the keys, fully quit and reopen Claude Code
(the keys are handed over when a session starts); (2) otherwise have them re-enter the keys: `/plugin` → Installed →
**s-portal-magazine** → Configure (desktop app: **+ → Plugins → Manage plugins**). Never ask them to paste a key into
the chat. If Python itself is missing, point them to python.org (Windows: tick "Add python.exe to PATH").
Don't continue until `check` passes.

### 1. Collect
The user sends the article and category (optionally: author, a publish date/time for scheduling). Ask for the
category if missing. Accept pasted text or a Word file (extract its text).

### 2. Write the article file
Save to the scratchpad as `article.txt`, exactly the user's words, in this format:
```
קטגוריה: תזונה נשים
כותרת: <title — see rules>
תקציר: <opening sentence(s), verbatim>
כותב: <only if the user named an author>
פרסום: <DD.MM.YYYY HH:MM — only if scheduling>

<article body; blank line between paragraphs; "## " subheading, "### " sub-subheading>
```
Check it: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/s-portal-magazine-post/scripts/magazine_post.py" parse article.txt` — `problems` must be empty.

### 3. Generate cover images
Write one English image prompt from the article's main idea, then:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/s-portal-magazine-post/scripts/magazine_post.py" image --out <scratchpad>/images --n 2 --prompt "<prompt>"
```
Prompt style, so the magazine looks consistent: *editorial photograph, realistic, natural warm light, shallow
depth of field, landscape, clean composition, warm neutral and golden tones that suit a dark-and-gold website,
no text, no letters, no logos, no watermarks.* Describe a concrete scene tied to the topic (food, people, an
everyday moment). Keep people respectful and non-sensational — no before/after bodies, no scales-shaming, no
medical gore, no identifiable real people or brands. If generation fails (billing, safety filter), report the
error in plain words and retry with a gentler prompt once.

### 4. Preview
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/s-portal-magazine-post/scripts/magazine_post.py" mock article.txt --images <img1> <img2> --out <scratchpad>/magazine-preview.html
```
This opens a local page showing the cube with each image option and the full article page. Tell the user in
chat: the title, summary, category, author and publish time you used, and that it's a close mock-up (not the
live site). Ask them to pick an image and approve, or say what to change. Then **stop and wait**.

### 5. Changes
Apply only what they ask (new image → new prompt and `image` again; different title/summary/category → edit
`article.txt`), re-run `mock`, and wait again.

### 6. Publish (only after explicit approval — "מאושר", "תפרסם", "publish"…)
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/s-portal-magazine-post/scripts/magazine_post.py" create article.txt --image <chosen image>
python3 "${CLAUDE_PLUGIN_ROOT}/skills/s-portal-magazine-post/scripts/magazine_post.py" publish <post_id>                 # or: --at "15.10.2026 09:00"
python3 "${CLAUDE_PLUGIN_ROOT}/skills/s-portal-magazine-post/scripts/magazine_post.py" verify <post_id>                  # immediate publishing only
```
`publish` uses the `פרסום:` time from `article.txt` if there is one. After publishing, **always purge the site
cache** with the Cloudways MCP `app_purge_cache` (server `1432214`, app `5348289`) — the page is cached separately per
URL spelling and visitors otherwise keep seeing the old grid for days. Then run `verify` and report from its output,
not from assumptions: the article URL, `has_cover_image`, `position_in_visible_grid` (1 = first cube) and
`cached_page_shows_it`. The purge is asynchronous: run it only after `publish` returns (not in parallel), and poll
`operation_status` until it completes before running `verify`. If the article still isn't in the grid or the cached
page, wait a minute, purge again and re-run before investigating. For a scheduled post, report the time; it appears automatically then (purge the cache after
that time if the user checks).

If the user wants to see it on the real site before publishing, stop after `create` and give them the preview
link it prints (requires being logged in to WordPress); publish after they approve.

## Categories

| User writes | Post type |
|---|---|
| תזונה נשים | blog-women |
| תזונה ספורט | blog-sport |
| תזונה ילדים | blog-child |
| מודעות והתנהגות אכילה | blog-eating |
| מטבח בריא | blog-kitchen |
| דיאטות נפוצות | blog-diet |
| המזונות המומלצים שלנו | blog-food |
| חגים ויציאה מהשגרה | blog-holiday |

For a category not in this table (e.g. תזונה כללי has no magazine post type), ask — don't create post types or
categories without the owner's say-so.

## Troubleshooting

- `check` → WordPress 401: wrong username/application password, or the password was revoked.
- `check` → missing publish/upload permission: the WordPress user needs the Editor role.
- Cover image or excerpt not saved on an article: the post type lost Featured image/Excerpt support — in JetEngine →
  Post Types, the 8 "המגזין שלנו - …" types must support Title, Editor, Thumbnail, Excerpt, Author (set 29.09.2026).
- New articles not first: JetEngine query 16 must be ordered by date, newest first (set 29.09.2026; was random).
- OpenAI 401/403: invalid key, no billing, or the org isn't verified for the image model.
- Cache can't be cleared (no Cloudways tool, or 401): the Cloudways token in the plugin settings is missing or was
  deleted — re-enter it via Configure and restart. The article is live anyway; tell the user to ask Tal to clear it.
