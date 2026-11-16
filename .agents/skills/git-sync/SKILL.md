---
name: git-sync
description: Synchronize 'main' branch across all project repositories (origin, open-repo, and commercial broker repo)
---

# Git Synchronization Workflow

This workflow ensures that the `main` branch is kept in sync across all target repositories while keeping commercial white-label/broker branding strictly isolated in `finanzplan-broker`.

## Configured Repositories
- **origin**: `https://github.com/bzaiser/finanzplan` (Main development repository in `d:\Daten\Dev\finanzplan`)
- **open-repo**: `https://github.com/bzaiser/Open-finanz-overview.git` (Public open-source repository in `d:\Daten\Dev\finanzplan`)
- **broker-repo**: `https://github.com/bzaiser/finanzplan-broker.git` (Private Commercial / White-Label Broker repository in `d:\Daten\Dev\finanzplan-broker`)

## Synchronization Steps

1. **Push to Origin (Main Dev Repo)**
   ```powershell
   git -C "d:\Daten\Dev\finanzplan" push origin main
   ```

2. **Push to Public Overview Repository**
   ```powershell
   git -C "d:\Daten\Dev\finanzplan" push open-repo main
   ```
   *(Wichtig: Niemals kommerziellen Branding-Code aus `finanzplan-broker` in `open-repo` pushen!)*

3. **Sync & Push Commercial Broker Repository (`finanzplan-broker`)**
   Übernimmt alle Basis-Updates aus `d:\Daten\Dev\finanzplan` (`main`) per Merge in `d:\Daten\Dev\finanzplan-broker` und pusht sie in das private Broker-Repo:
   ```powershell
   git -C "d:\Daten\Dev\finanzplan-broker" fetch "d:\Daten\Dev\finanzplan" main
   git -C "d:\Daten\Dev\finanzplan-broker" merge FETCH_HEAD --no-edit
   # Falls neue Migrationen in beiden Zweigen entstanden sind:
   Set-Location "d:\Daten\Dev\finanzplan-broker"
   python manage.py makemigrations --merge --noinput
   git add -A
   git diff --cached --quiet; if (-not $?) { git commit -m "chore(merge): merge upstream migrations" }
   git -C "d:\Daten\Dev\finanzplan-broker" push origin main
   ```

4. **Desktop App Setup Abfrage**
   - Nach erfolgreichem Push den Benutzer fragen, ob das Setup für die Desktop App erstellt werden soll.
   - **Nur bei Bestätigung** das Setup bauen:
     ```powershell
     python manage.py collectstatic --noinput
     python -m PyInstaller --clean -y finanzplan.spec
     & "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
     ```
   - **Andernfalls kein Setup erstellen.**

## Rules for Repositories
- Allgemeine App-Features werden in `d:\Daten\Dev\finanzplan` (`main`) entwickelt und nach Schritt 1–3 in alle 3 Repos synchronisiert.
- Exklusive Makler-/White-Label-Funktionen (`PartnerBrandingConfig`, Beratungs-Trigger) werden ausschließlich in `d:\Daten\Dev\finanzplan-broker` (`main`) gepflegt und nur zu `finanzplan-broker` (`origin main`) gepusht.
