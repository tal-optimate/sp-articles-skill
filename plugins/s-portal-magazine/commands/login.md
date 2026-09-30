---
description: Connect the magazine skill — opens the one settings form for the WordPress, OpenAI and Cloudways keys
---

# Log in to the s-portal magazine connections

Walk the user through entering the keys the magazine skill needs. Speak in the user's language (Hebrew if they
write Hebrew) and wait for them between steps.

**Never ask for a key in the chat, and never accept one pasted there.** Keys go only into Claude Code's secure
settings form, which the user opens with `/plugin configure s-portal-magazine@sportal`. If they paste a key into the chat anyway,
tell them it is now in the conversation, that they should still enter it in the form, and that it is safer to
create a new one.

## 1. Check what's connected

Run the check (on Windows use `python` instead of `python3`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/s-portal-magazine-post/scripts/magazine_post.py" check
```

Also check whether a Cloudways tool is available (`app_purge_cache` from this plugin's `cloudways` server,
or a separately added `cloudways` MCP server).

## 2. Open the settings form

All keys are in one form. If anything is not `OK` (or Cloudways is missing), tell the user which keys are missing
and give them this one command to type in the chat box:

`/plugin configure s-portal-magazine@sportal`

| Field in the form | What to paste |
|---|---|
| WordPress user | already filled in (`sportal.digital@gmail.com`), leave it |
| WordPress application password | the password from Tal (spaces are fine) |
| OpenAI API key | the key that starts with `sk-` |
| Cloudways access token | the Cloudways token |

Fields already saved can be left as they are; they only need to fill in what's missing. The keys come from Tal
(e.g. via Bitwarden Send); don't explain how to create keys unless they ask.

Suggested Hebrew wording:
„כדי לחבר את החשבונות, הקלידו בתיבת ההודעה: `/plugin configure s-portal-magazine@sportal` ובטופס שנפתח הדביקו את המפתחות שקיבלתם מטל: סיסמת האפליקציה של וורדפרס, מפתח OpenAI (מתחיל ב־sk-) והטוקן של Cloudways. שם המשתמש של וורדפרס כבר ממולא. תכתבו לי כשסיימתם."

## 3. Restart and confirm

Once they've saved the form, tell them to **fully quit and reopen Claude Code** — the keys reach the skill
when a session starts. After they reopen and say so, run the check again. Report plainly:
- Both `OK` and Cloudways available → "הכל מחובר ✅ — אפשר לשלוח כתבה."
- Something still failing → have them open the same form and re-enter only that key. A WordPress `401` means the password was
  pasted wrong or revoked: ask Tal for a new one. An OpenAI failure means a wrong key or no billing credit.
