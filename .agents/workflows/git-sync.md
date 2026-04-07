---
description: Synchronize 'main' and 'master' branches across all project repositories
---
# Git Synchronization Workflow

This workflow ensures that both `main` and `master` branches are kept in sync across all target repositories.

## Configured Repositories
- **origin**: `finanzplan.git` (Main internal development)
- **overview**: `Open-finanz-overview.git` (Public/Overview version)

## Synchronization Steps

// turbo
1. **Prepare Master Branch locally**
   - Ensure the local `master` branch matches the local `main` branch.
   ```bash
   git checkout master
   git merge main
   git checkout main
   ```

// turbo-all
2. **Push to All Remotes**
   - Push both branches to all configured remotes to ensure they are identical everywhere.
   ```bash
   git push origin main master
   git push overview main master
   ```

## Rules for New Repositories
- If a new remote is added, it must follow the `origin` (internal) or `overview` (public) naming convention.
- Avoid using temporary labels like `repo-a` or `repo-b`.
- Use HTTPS tokens for write access if SSH permissions are limited to Deploy Keys.
