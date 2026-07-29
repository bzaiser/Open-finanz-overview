---
description: Synchronize 'main' branch across all project repositories
---
# Git Synchronization Workflow

This workflow ensures that the `main` branch is kept in sync across all target repositories.

## Configured Repositories
- **origin**: `finanzplan.git` (Main development repository)

## Synchronization Steps

1. **Push to Origin**
   ```bash
   git push origin main
   ```

## Rules for New Repositories
- If a new remote is added, it must follow the `origin` (internal) or `overview` (public) naming convention.
- Avoid using temporary labels.
- Use HTTPS tokens for write access if SSH permissions are limited to Deploy Keys.
