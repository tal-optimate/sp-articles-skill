# sportal: Dr. Shawn Portal tools for Claude Code

A plugin marketplace with three plugins. No keys or passwords are stored in this repository: each person enters
their own in the plugin's settings form, which keeps them in the computer's secure credential store.

| Plugin | What it gives | Asks for |
|---|---|---|
| `s-portal-magazine` | Publish an article as a new cube in המגזין שלנו (AI cover image, preview, publish on approval). Installs the two plugins below automatically. | OpenAI API key |
| `sportal-elementor` | Elementor connection for s-portal.co.il, plus the WordPress login the magazine uses | WordPress user + application password |
| `sportal-cloudways` | Cloudways connection (clear the site cache, server info) | Cloudways access token |

## Install (Claude Code desktop app)
1. **+ → Plugins → Add plugin** → add marketplace `tal-optimate/sp-articles-skill`.
2. Install **s-portal-magazine** (or just the connection you need) and fill in the forms.
3. Quit and reopen Claude Code, then say: *run the magazine skill check*.

Terminal alternative:
```
claude plugin marketplace add tal-optimate/sp-articles-skill
claude plugin install s-portal-magazine@sportal
```
If a settings form doesn't appear, open it with `/plugin configure <plugin>@sportal`.

Requires Python 3 (Windows: python.org, tick "Add python.exe to PATH").
