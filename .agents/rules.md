# Docker & Git Workflow Rules

## 1. Docker Setup
- Workflows (like `makemigrations`, `migrate`, tests) run inside Docker, NOT on the host machine.
- Migrations are created/managed so that they can be committed to Git.

## 2. Git Workflow
- Default push remote: `origin main` (`git push origin main`).
- **Translation Check**: ALWAYS verify that `.po` files do NOT contain duplicate `msgid` definitions before committing or pushing changes to `locale/`.
