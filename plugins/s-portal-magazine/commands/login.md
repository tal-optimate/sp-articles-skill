---
description: Connect the magazine skill — asks for each missing key (WordPress, OpenAI, Cloudways) one at a time
---

# Log in to the s-portal magazine connections

Walk the user through entering the keys the magazine skill needs. Speak in the user's language (Hebrew if they
write Hebrew), one step at a time, and wait for them between steps.

**Never ask for a key in the chat, and never accept one pasted there.** Keys go only into Claude Code's secure
settings forms, which the user opens with a `/plugin configure …` command. If they paste a key into the chat anyway,
tell them it is now in the conversation, that they should still enter it in the form, and that it is safer to
create a new one.

## 1. Check what's connected

Run the check (on Windows use `python` instead of `python3`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/s-portal-magazine-post/scripts/magazine_post.py" check
```

Also check whether a Cloudways tool is available (`app_purge_cache` from the `sportal-cloudways` plugin, or a
`cloudways` MCP server).

## 2. Ask for each missing key, one at a time

For every line that is not `OK`, give the user exactly one command to type in the chat box, in this order, and
wait until they say they've filled it in before giving the next:

| Missing | They type | They paste into the form |
|---|---|---|
| WordPress | `/plugin configure sportal-elementor@sportal` | the WordPress application password (the user field is pre-filled) |
| OpenAI | `/plugin configure s-portal-magazine@sportal` | the OpenAI API key (starts with `sk-`) |
| Cloudways | `/plugin configure sportal-cloudways@sportal` | the Cloudways access token |

Say where each key comes from if they don't have it: Tal sends them (e.g. via Bitwarden Send). Don't explain how to
create keys unless they ask.

Suggested Hebrew wording for each step:
- „כדי לחבר את וורדפרס, הקלידו בתיבת ההודעה: `/plugin configure sportal-elementor@sportal` והדביקו בטופס את סיסמת האפליקציה שקיבלתם מטל. תכתבו לי כשסיימתם."
- „עכשיו OpenAI (בשביל תמונות השער): `/plugin configure s-portal-magazine@sportal` והדביקו את המפתח שמתחיל ב־sk-."
- „ולבסוף Cloudways (לניקוי המטמון באתר): `/plugin configure sportal-cloudways@sportal` והדביקו את הטוקן."

## 3. Restart and confirm

Once every missing key is entered, tell them to **fully quit and reopen Claude Code** — the keys reach the skill
when a session starts. After they reopen and say so, run the check again. Report plainly:
- Both `OK` and Cloudways available → "הכל מחובר ✅ — אפשר לשלוח כתבה."
- Something still failing → give only that one key's command again. A WordPress `401` means the password was
  pasted wrong or revoked: ask Tal for a new one. An OpenAI failure means a wrong key or no billing credit.
