# s-portal Magazine (Claude Code plugin)

Publishes an article as a new cube in the **המגזין שלנו** magazine on s-portal.co.il: AI cover image options,
a preview, and publishing only after approval.

## Install (Claude Code desktop app)
1. **+ → Plugins → Add plugin** → add marketplace `tal-optimate/sp-articles-skill`.
2. Install **s-portal-magazine** and fill in the 4 fields (WordPress user + application password, OpenAI key,
   Cloudways token). The keys are stored in the computer's secure credential store, not in this repo.
3. Quit and reopen Claude Code, then say: *run the magazine skill check*.

Terminal alternative:
```
claude plugin marketplace add tal-optimate/sp-articles-skill
claude plugin install s-portal-magazine@sportal
```
Requires Python 3 (Windows: python.org, tick "Add python.exe to PATH").

No keys or passwords are stored in this repository.
