# Finanzplan – The High-End Financial & Retirement Cockpit 🚀

[![Language: Multi-5](https://img.shields.io/badge/Language-Multi--5-blue)](#-internationalization)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with: Django](https://img.shields.io/badge/Backend-Django--6-green)](https://www.djangoproject.com/)
[![Built with: Google Antigravity](https://img.shields.io/badge/AI--Assisted-Google%20Antigravity-orange?logo=google)](https://deepmind.google/technologies/)

> [!TIP]
> **Deutschsprachige Dokumentation**: Du findest die deutsche Version der Dokumentation hier: [README.de.md](README.de.md) 🇩🇪

**The Holistic Financial, Retirement & Real Estate Cockpit** — A high-precision 30+ year simulation engine for households, families, and property owners featuring real purchasing-power math, protection audits, and crisis stress testing.

---

## 🌟 Vision & Overview

Finanzplan is more than just a tracking app. It is a **Simulation Engine** for your life. It projects your financial trajectory over 30+ years, accounting for assets, real estate, loans, pension entitlements, recurring cash flows, and one-time events, while strictly factoring in the eroding effect of inflation on your purchasing power.

---

## ✨ Core Modules & Expert Features

### 📈 1. Precision Simulation Engine & Dashboard (`/finance/dashboard/`)
- **Real vs. Nominal Purchasing Power**: Every KPI card and Chart.js time series displays both nominal values and inflation-discounted **real purchasing power** in today's euros.
- **Interactive Target Date (`Stichtag`) Time Travel**: Inspect your balance sheet in any future month up to your simulation max age (default: 90) with expandable hover breakdowns.
- **Crisis & Stress-Test Simulator**: Simulate *Job Loss (ALG I)*, *Occupational Disability (BU)*, *Market Crash (-X%)*, *Refinancing Rate Shock (+X%)*, or *Emergency Expenses* with live baseline comparison curves.

### 🏛️ 2. Retirement Planning, Insurances & Protection Audit (`/finance/pensions/`)
- **4 Pension Pillars**: Statutory Pension (DRV with pension points, `40.79 €` point value, and disability pension), Private Capital Pension, Civil Service Pension (`civil_service`), and Professional/Occupational Funds (`occupational_fund`).
- **3 Payout Models**: Monthly capital drawdown, lifelong annuity, or one-time lump-sum payout (automatically credited to liquid cash at maturity).
- **Insurance & Risk Audit (`InsurancePolicy`)**: Traffic-light coverage checklist, disability gap analysis (80% net rule), term-life protection check (3× annual net income + current loan debt), and emergency fund runway.

### 🏘️ 3. Real Estate, Loans & Tax Cockpit (`/finance/real-estate/`)
- **Loan & Amortization Engine**: Annuity, fixed-amortization, and bullet loans with live LTV tracking, interest-lock expiry alerts, and an **interactive Extra Repayment Simulator** (interest saved & months/years shaved off).
- **Renovation Roadmap (`PropertyComponent`)**: Lifecycle tracking for roof, heating, windows, and facade with 20-year capex forecasting.
- **Rental Tax (Anlage V) & Payment Calendar**: 12-month property cashflow calendar and automated calculation of linear building depreciation (AfA), deductible loan interest, maintenance invoices, and taxable rental result.

### 💰 4. Assets, Accounts & Physical Valuables (`/finance/assets/`)
- **All Asset Classes**: Cash/Checking, Overnight/Money Market, ETF/Securities Depots, Crypto, Precious Metals, and Physical Assets (`PhysicalAsset`).
- **Promotional Teaser Rate Guard**: Tracks promotional overnight rates (`interest_teaser_rate` / `interest_teaser_until`) with automatic fallback to standard growth rates after expiry.
- **Automated Savings Reconciliation**: Account savings plans (`monthly_savings_amount`) compound monthly into wealth while reconciling with manual savings cash flows to prevent double-counting.

### 🪄 5. Guided Setup Wizard & 5 Target-Group Demo Profiles
- **Statement & Setup Wizard (`/finance/wizard/`)**: Captures household & partner data, statutory/private pension statements, cash flows, assets, properties, and loans with chronological snapshot protection (`AssetSnapshot`).
- **Annual Adjustment Wizard (`/finance/cash-flows/`)**: Rolls over recurring contracts and salaries into the new year while preserving clean historical end dates.
- **6 Household Situations & 1-Click Demo Profiles**: Tailored dashboard presets for *Standard Family (`demo_familie`)*, *Low Income (`gering`)*, *Single Parent (`allein`)*, *Student (`student`)*, and *Early Retiree (`rentner`)*.

### 🎨 6. Design Harmony System
- **Mathematical Color Harmonies**: Choose from curated color presets (*Deep Ocean*, *Emerald Trust*, *Sunset Gold*, *Midnight Purple*) or build custom palettes.
- **Glassmorphism UI & Night Mode**: High-end depth effects with automatic dark/light theme adaptation.

---

## 🛠 Tech Stack

- **Backend**: Django 6.0.2
- **Frontend**: Bootstrap 5, HTMX, Alpine.js, Chart.js 4
- **AI Integration**: LangChain, Ollama, Google Gemini
- **Infrastructure**: Docker & Docker Compose

---

## 🚀 Getting Started

We offer two ways to run your financial cockpit, depending on your environment.

### Option A: Windows Installer / Desktop App (.exe)
**Best for**: Windows users who want a native standalone application with a full installer (no Docker, WSL2, or Python installation needed).
1. **Download Installer**: Grab `FinanzplanDesktop_Setup.exe` from the `dist_installer/` directory or GitHub Releases.
2. **Install**: Run `FinanzplanDesktop_Setup.exe`, choose an optional desktop icon, and complete the installer wizard.
3. **Launch**: The application starts in its own dedicated window with an integrated desktop runner and local database management.

*(Alternative: For portable zero-installer usage, run `native-dist/setup-native.bat` and `start-dashboard.bat`.)*

### Option B: Server/NAS (Docker & Podman)
**Best for**: Advanced users, NAS systems (Synology/QNAP), or Linux servers.
1. **Clone**: `git clone https://github.com/bzaiser/Open-finanz-overview.git`.
2. **Config**: `cp .env.example .env`.
3. **Launch**: `./update-fast.sh` (or `docker-compose up -d`).

---

---

## 🌍 Internationalization

Finanzplan is built for a global audience. We support:
- 🇩🇪 **German** (DE)
- 🇺🇸 **English** (EN)
- 🇫🇷 **French** (FR)
- 🇪🇸 **Spanish** (ES)
- 🇮🇹 **Italian** (IT)

Our system uses a **Key-based i18n strategy** for maximum stability, especially when handling special formatting like currency and percentages.

---

## 🔒 Security & Privacy

Your financial data is sensitive. That's why Finanzplan is designed to be **completely self-hosted**. No data ever leaves your control unless you explicitly choose a cloud-based AI provider. Even then, only anonymized transaction descriptions are processed.

---

## 🤖 Built with Google Antigravity
This project was architected, built, and continuously evolved with **Google Antigravity** (Advanced Agentic Pair-Programming).

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
*Created with ❤️ by Bernd Zaiser*
