---
name: git-sync
description: Synchronize 'main' branch across all project repositories
---

# Git Synchronization Workflow

This workflow ensures that the `main` branch is kept in sync across all target repositories.

## Configured Repositories
- **origin**: `finanzplan.git` (Main development repository)
- **open-repo**: `Open-finanz-overview.git` (Public overview repository)

## Synchronization Steps

1. **Push to Origin**
   ```bash
   git push origin main
   ```

2. **Push to Public Overview Repository**
   ```bash
   git push open-repo main
   ```
   *(Alternativ falls remote als `overview` konfiguriert ist: `git push overview main`)*

3. **Desktop App Setup Abfrage**
   - Nach erfolgreichem Push den Benutzer fragen, ob das Setup für die Desktop App erstellt werden soll.
   - **Nur bei Bestätigung** das Setup bauen:
     ```powershell
     python manage.py collectstatic --noinput
     python -m PyInstaller --clean -y finanzplan.spec
     & "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
     ```
   - **Andernfalls kein Setup erstellen.**

## Rules for New Repositories
- If a new remote is added, it must follow the `origin` (internal) or `overview` (public) naming convention.
- Avoid using temporary labels.
- Use HTTPS tokens for write access if SSH permissions are limited to Deploy Keys.
