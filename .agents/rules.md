# Docker & Git Workflow Rules

## 1. Docker Setup
- Workflows (like `makemigrations`, `migrate`, tests) run inside Docker, NOT on the host machine.
- Migrations are created/managed so that they can be committed to Git.

## 2. Git Workflow
- **Git Push Policy**: FIRST apply and display code changes to the user. DO NOT push to Git automatically. ONLY run `git push origin main` after the user has reviewed and explicitly given their OK.
- **Translation Check**: ALWAYS verify that `.po` files do NOT contain duplicate `msgid` definitions before committing or pushing changes to `locale/`.
- **JavaScript & Template Escaping Rule**: ALWAYS use double quotes `"{% trans ... %}"` around `{% trans %}` or `{% url %}` tags inside JavaScript code to prevent apostrophes (e.g. `Today's`) from breaking JS string literals. Never mix unescaped quotes inside Django tags.
