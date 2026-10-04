# sportal: Dr. Shawn Portal tools for Claude Code

One plugin, **s-portal-magazine**: publish an article as a new cube in המגזין שלנו on s-portal.co.il (AI cover image,
preview, publish on approval). It also adds the s-portal **Elementor** and **Cloudways** connections.

Keys are stored **only in the OS keychain** (macOS Keychain, Windows Credential Manager, Linux libsecret) by the
plugin's login tool, which checks each key before saving it. **No keys or passwords are stored in this repository.**

## Install
Requires [Bun](https://bun.sh) 1.3+ and Python 3 (Windows: python.org, tick "Add python.exe to PATH").

1. In Claude Code (desktop app: **+ → Plugins → Add plugin**) add the marketplace `tal-optimate/sp-articles-skill`
   and install **s-portal-magazine**. Terminal alternative:
   ```
   claude plugin marketplace add tal-optimate/sp-articles-skill
   claude plugin install s-portal-magazine@sportal
   ```
2. Log in once, in a terminal. Input is hidden; each key is checked, then saved to the keychain:
   ```bash
   bun ~/.claude/plugins/marketplaces/sportal/plugins/s-portal-magazine/cli/sportal-auth.js login
   ```
   Windows (PowerShell):
   ```powershell
   bun "$env:USERPROFILE\.claude\plugins\marketplaces\sportal\plugins\s-portal-magazine\cli\sportal-auth.js" login
   ```
   Same file with `status` (which keys work) or `logout` (remove them); `login wordpress|openai|cloudways` redoes one.
3. Restart Claude Code, then say: *run the magazine skill check*. `/s-portal-magazine:login` walks you through this.
