---
description: Synchronize 'main' branch across all project repositories
---
# Git Synchronization Workflow

This workflow ensures that the `main` branch is kept in sync across all target repositories.

## Configured Repositories
- **origin**: `finanzplan.git` (Main internal development)
- **overview**: `Open-finanz-overview.git` (Public/Overview version)

## Synchronization Steps

// turbo-all
1. **Push to All Remotes**
   - Push the `main` branch to all configured remotes to ensure they are identical everywhere.
   ```bash
   git push origin main
   git push overview main
   ```

## Rules for New Repositories
- If a new remote is added, it must follow the `origin` (internal) or `overview` (public) naming convention.
- Avoid using temporary labels.
- Use HTTPS tokens for write access if SSH permissions are limited to Deploy Keys.
