# Finance Overview 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Language: 5 Support](https://img.shields.io/badge/Language-Multi--5-blue)

**The Personal Financial Cockpit** — A realistic, long-term financial forecasting tool designed to give you clarity on your future net worth.

## Overview

This project is a personal finance dashboard that simulates your financial future over 30+ years. It accounts for assets, recurring cash flows (income/expenses), one-time events, and pensions, all while factoring in the impact of inflation on your purchasing power.

## ✨ Key Features

- **Long-term Forecast**: 30-year simulation of your net worth.
- **Inflation Monitor**: Visualizes the gap between nominal value and real purchasing power.
- **Dynamic Dashboards**: Customizable chart layouts, colors, and widget sizes.
- **Multi-Language Support**: Fully translated into **German, English, French, Spanish, and Italian**.
- **Smart Bank Import (Optimized)**: Fast import (1s analysis) with grouping, duplicate detection, and plan conflict alerts.
- **Privacy First (Local AI)**: Categorize transactions using a local **Ollama** instance (100% self-hosted) or cloud providers (Gemini, Groq).
- **Multi-Instance Support**: Easily distinguish between 'Private' and 'Open' instances in the header.

## 🛠 Tech Stack

- **Backend**: Django 6.0.2 (Single-Branch `main` strategy)
- **Frontend**: Bootstrap 5, HTMX, Chart.js
- **Database**: SQLite (default)
- **Deployment**: Docker & Docker Compose (Root-level orchestration)

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- (Optional) Docker & Docker Compose

### Fast Deployment (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/bzaiser/finanzplan.git
   cd finanzplan
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and set your APP_INSTANCE_NAME, LLM_PROVIDER etc.
   ```

3. **Start the containers**:
   ```bash
   ./update-fast.sh
   # This will build, migrate, and start the app in Docker.
   ```
   Access at `http://localhost:8000`.

### 🤖 Smart Import & AI

This project includes an **AI-powered bank statement import**. You can choose between different providers in your `.env`:

#### Local AI (Privacy-Modus)
Use **Ollama** for 100% local categorization. No financial data leaves your network!
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://your-ip:11434
OLLAMA_MODEL=llama3
```

#### Cloud AI (Performance-Modus)
Use **Gemini** or **Groq** for high-quality, external categorization.
```bash
LLM_PROVIDER=gemini # or groq
GEMINI_API_KEY=your-key
```

## 🔒 Security & Identification

- **Instance Branding**: Set `APP_INSTANCE_NAME=Private` to see it in the header.
- **Admin Access**: Authenticated users can manage their data via the integrated Admin panel.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
*Created with ❤️ by Bernd Zaiser*
