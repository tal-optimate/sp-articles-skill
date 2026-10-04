---
description: Connect the magazine skill — log in once in a terminal; the keys are checked and saved in the OS keychain
---

# Log in to the s-portal magazine connections

The keys (WordPress application password, OpenAI key, Cloudways token) are stored **only in the OS keychain** by the
plugin's login tool. Speak in the user's language (Hebrew if they write Hebrew) and wait for them between steps.

**Never ask for a key in the chat, and never accept one pasted there.** If they paste one anyway, tell them it is now
in the conversation, that they should still enter it with the login command, and that it is safer to create a new
one.

## 1. Check what's connected

```bash
bun "${CLAUDE_PLUGIN_ROOT}/cli/sportal-auth.js" status
```
Each line shows ✓ or ✗ for WordPress, OpenAI and Cloudways. If the command fails because `bun` isn't found, go to
step 2 first.

## 2. Bun (only if missing)

Bun 1.3+ is required (the same as Optimate's Clockify plugin). Have them install it in a terminal, then open a new one:
- Mac: `curl -fsSL https://bun.sh/install | bash`
- Windows (PowerShell): `powershell -c "irm bun.sh/install.ps1 | iex"`

## 3. Log in (in their own terminal)

The login asks for hidden input, so it must run in a real terminal (Terminal on Mac, PowerShell on Windows), not
in this chat. Build the command from **this plugin's actual folder**, which depends on how it was installed
(Claude Code's `/plugin`, the desktop app's Plugins page, …): it is `${CLAUDE_PLUGIN_ROOT}/cli/sportal-auth.js`.
Show the user the command with that full path written out, in quotes:
- Mac: `bun "${CLAUDE_PLUGIN_ROOT}/cli/sportal-auth.js" login`
- Windows (PowerShell): the same, with the path in Windows form (backslashes), e.g.
  `bun "C:\Users\<name>\…\cli\sportal-auth.js" login`
If `${CLAUDE_PLUGIN_ROOT}` wasn't filled in above, find the file first (Windows PowerShell:
`Get-ChildItem $env:USERPROFILE -Recurse -Filter sportal-auth.js -ErrorAction SilentlyContinue | Select -Expand FullName`;
Mac: `find ~ -name sportal-auth.js 2>/dev/null`) and use the path it prints.

It asks for each key in turn (the WordPress user is pre-filled: Enter keeps `sportal.digital@gmail.com`), checks
each one against WordPress / OpenAI / Cloudways, and saves only the ones that pass. Pressing Enter on an empty key
skips it. To redo one key: add `wordpress`, `openai` or `cloudways` after `login`.

Suggested Hebrew wording:
„פתחו את הטרמינל (Terminal), הדביקו את השורה הזו ולחצו Enter: `<the command>`. הוא יבקש את המפתחות שקיבלתם מטל אחד־אחד – ההקלדה מוסתרת, וכל מפתח נבדק לפני שהוא נשמר. כשמופיע „All set" – כתבו לי."

## 4. Restart and confirm

Have them fully quit and reopen Claude Code (the Cloudways and Elementor connections read the keys when they
connect). Then run step 1 again and report plainly:
- All ✓ → "הכל מחובר ✅ — אפשר לשלוח כתבה."
- A ✗ → give the login command again with just that key (`login wordpress` / `login openai` / `login cloudways`).
  WordPress "wrong user or application password" → ask Tal for a new one; OpenAI "invalid key" → wrong key or no
  billing credit.

`status` shows which keys work; `logout` removes all of them from the keychain.
