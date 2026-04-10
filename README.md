# Finance Overview 🚀

[![Language: Multi-5](https://img.shields.io/badge/Language-Multi--5-blue)](#-internationalization)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with: Django](https://img.shields.io/badge/Backend-Django--6-green)](https://www.djangoproject.com/)

> [!TIP]
> **Deutschsprachige Dokumentation**: Du findest die deutsche Version der Dokumentation hier: [README.de.md](README.de.md) 🇩🇪

**The High-End Financial Cockpit** — A sophisticated, long-term financial forecasting tool designed to give you extreme clarity on your future net worth. 

---

## 🌟 Vision & Overview

Finanzplan is more than just a tracking app. It is a **Simulation Engine** for your life. It projects your financial trajectory over 30+ years, accounting for assets, liabilities, recurring cash flows, and one-time events, while strictly factoring in the eroding effect of inflation on your purchasing power.

---

## ✨ Key Expert Features

### 🧠 Smart AI Bank Import (2.0)
Our AI-assisted import doesn't just read CSV files; it **understands** them.
- **Pattern Recognition**: Automatically cleans bank descriptions and searches for repeating patterns.
- **Learned Memory**: Remembers your previous categorizations and applies them to new imports.
- **Duplicate Fingerprinting**: Every transaction gets a unique hash to prevent overlapping imports.
- **Privacy First**: Choose between **100% Local AI** (Ollama) or high-performance cloud providers (Gemini, Groq).

### 📈 Precision Simulation Engine
Understand the math behind your wealth.
- **Real vs. Nominal Value**: Distinguish between the absolute money you have and its real purchasing power.
- **Inflation Buffer**: Configurable inflation rates to visualize your "Real" net worth.
- **Dynamics & Indexing**: Simulate career growth with salary dynamics and contract-indexed pension increases.
- **Compound Interest Logic**: Monthly compounding of growth for every individual asset class.

### 🎨 Design Harmony System
A premium experience for premium data.
- **Mathematical Color Harmonies**: Choose a primary color, and our engine calculates perfectly matched Complementary or Analogous palettes.
- **Glassmorphism UI**: High-end depth effects with backdrop filters and translucency.
- **Night Mode Mastery**: A dedicated midnight theme engine for eye-soothing nighttime analysis.

---

## 🛠 Tech Stack

- **Backend**: Django 6.0.2
- **Frontend**: Bootstrap 5, HTMX, Alpine.js, Chart.js 4
- **AI Integration**: LangChain, Ollama, Google Gemini
- **Infrastructure**: Docker & Docker Compose

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (Recommended)

### Fast Deployment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/bzaiser/Open-finanz-overview.git
   cd finanzplan
   ```

2. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Set your APP_INSTANCE_NAME, LLM_PROVIDER, etc.
   ```

3. **Launch with Docker**:
   ```bash
   ./update-fast.sh
   ```
   Access your cockpit at `http://localhost:8000`.

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

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
*Created with ❤️ by Bernd Zaiser*
