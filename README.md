# sportal: Dr. Shawn Portal tools for Claude Code

One plugin, **s-portal-magazine**: publish an article as a new cube in המגזין שלנו on s-portal.co.il (AI cover image,
preview, publish on approval). It also adds the s-portal **Elementor** and **Cloudways** connections.

It asks for all its keys in one settings form: WordPress user (pre-filled) + application password, OpenAI API key,
Cloudways access token. **No keys or passwords are stored in this repository**: the form keeps them in the
computer's secure credential store.

## Install (Claude Code desktop app)
1. **+ → Plugins → Add plugin** → add marketplace `tal-optimate/sp-articles-skill`.
2. Install **s-portal-magazine** and fill in the form.
3. Quit and reopen Claude Code, then say: *run the magazine skill check*.

Terminal alternative:
```
claude plugin marketplace add tal-optimate/sp-articles-skill
claude plugin install s-portal-magazine@sportal
```
First use: the skill checks the connections and asks for any missing keys. Run the same flow any time with
`/s-portal-magazine:login`, or open the form directly with `/plugin configure s-portal-magazine@sportal`.

Requires Python 3 (Windows: python.org, tick "Add python.exe to PATH").
