# ApplyPilot (AI Agent With Human in the Loop) 🚀

**Autonomous, AI-Powered Job Application Assistant & Form Filler. Open Source.**

ApplyPilot takes the tedious, repetitive pain out of job hunting. Powered by modern autonomous AI agents (**Claude Code CLI** or the open-source **Hermes Agent**) and browser automation (**Chrome CDP + Playwright MCP**), ApplyPilot opens job portals, navigates complex multi-page application forms, auto-fills personal details, work authorization, education, and work history, answers custom screening questions using a persistent Q&A memory, uploads the right documents in the right priority order, and securely logs every application.

---

## 📑 Table of Contents

- [What is ApplyPilot?](#what-is-applypilot)
- [Key Features](#key-features)
- [How It Works Under the Hood](#how-it-works-under-the-hood)
- [System Requirements](#system-requirements)
- [Step-by-Step Setup Guide](#step-by-step-setup-guide)
  - [🍎 macOS Setup](#-macos-setup)
  - [🪟 Windows Setup](#-windows-setup)
- [🤖 Choosing & Configuring Your AI Agent (Claude vs. Hermes)](#-choosing--configuring-your-ai-agent-claude-vs-hermes)
  - [Why Use Hermes Agent?](#why-use-hermes-agent)
  - [Why Use Claude Code CLI?](#why-use-claude-code-cli)
  - [Agent Comparison & Supported Models](#agent-comparison--supported-models)
  - [How to Switch Between Agents](#how-to-switch-between-agents)
- [Setting Up API Keys (.env)](#setting-up-api-keys-env)
- [Configuring Your Profile (profile.json)](#configuring-your-profile-profilejson)
- [Managing Documents & The Cover Letter Feature](#managing-documents--the-cover-letter-feature)
- [Customizing Application Instructions (prompt.txt)](#customizing-application-instructions-prompttxt)
- [How to Run ApplyPilot](#how-to-run-applypilot)
  - [1. Recommended Workflow (Review-First Mode)](#1-recommended-workflow-review-first-mode)
  - [2. Running with Hermes Agent (Open Source / Low Cost)](#2-running-with-hermes-agent-open-source--low-cost)
  - [3. Running with Claude Code CLI](#3-running-with-claude-code-cli)
  - [4. Preview Mode (Dry Run)](#4-preview-mode-dry-run)
  - [5. Fully Autonomous Mode (Auto-Submit)](#5-fully-autonomous-mode-auto-submit)
  - [6. Inspect Agent Prompts (--gen)](#6-inspect-agent-prompts---gen)
- [Complete CLI Command Reference](#complete-cli-command-reference)
  - [Overview of All Commands](#overview-of-all-commands)
  - [1. applypilot apply (Core Automation Engine)](#1-applypilot-apply-core-automation-engine)
  - [2. applypilot status (Pipeline Analytics)](#2-applypilot-status-pipeline-analytics)
  - [3. applypilot applied (Export & View Submissions)](#3-applypilot-applied-export--view-submissions)
  - [4. applypilot qa (Screening Questions Knowledge Base)](#4-applypilot-qa-screening-questions-knowledge-base)
  - [5. applypilot creds (Portal Credentials Manager)](#5-applypilot-creds-portal-credentials-manager)
  - [Global Flags & Keyboard Controls](#global-flags--keyboard-controls)
- [Troubleshooting & FAQs](#troubleshooting--faqs)
- [License](#license)

---

## What is ApplyPilot?

Applying for jobs online today is broken. Every company uses a different Applicant Tracking System (ATS)—such as **Greenhouse, Lever, Workday, Personio, Ashby, SmartRecruiters, Jobvite, iCIMS**, or custom enterprise portals. Each portal forces you to:
1. Re-enter your name, address, and contact details.
2. Re-type your employment history and education degrees.
3. Answer repetitive screening questions (*"Are you authorized to work in Germany?", "What are your salary expectations?", "Will you require visa sponsorship?"*).
4. Upload tailored resumes, cover letters, and certificates.
5. Create new login credentials for every company career site.

**ApplyPilot automates this entire flow.** You point it to a job URL, and an autonomous AI agent opens Google Chrome, fills out the application with verified facts from your personal profile and documents, leaves the browser ready for you to review (or submits automatically if configured), archives the specific cover letter used, and records the application in `applied.json`.

---

## Key Features

- 🎯 **Direct URL Applications**: Simply run `applypilot apply --url "https://..."` to apply to any supported job posting.
- 🤖 **Flexible Agent Support (Claude & Hermes)**: Run with **Claude Code CLI** (Anthropic Claude Sonnet) or the open-source **Hermes Agent** powered by DeepSeek, NVIDIA NIM, or Google Gemini.
- 🛡️ **Stop-Before-Submit (Review-First Safety)**: By default, the agent fills all form fields, answers questions, uploads documents, and pauses on the final review page. You get to verify everything in Chrome before submitting.
- 📂 **Intelligent Document Upload Hierarchy**:
  1. **Priority 1 — Resume / CV (`cv.pdf`)**: Always uploaded fresh to Resume / CV / Lebenslauf fields.
  2. **Priority 2 — Cover Letter (`cover_letter.pdf`)**: Uploaded to Cover Letter / Anschreiben fields, or pasted if it is a text area.
  3. **Priority 3 — Other Documents (`other_docs.pdf`)**: Uploaded to general attachment, certificates, transcripts, or "Weitere Dokumente" fields.
  4. **Priority 4 — Dedicated Specific Documents**: Visa / Work Permit, Enrollment Certificates, Transcripts, or Profile Photos uploaded *only* when an explicit field requests them.
- 🗄️ **Automatic Cover Letter Archiving**: When an application is completed, `documents/cover_letter.pdf` is automatically copied and moved to `applied_cv/{job_url}.pdf`. You will always have an exact record of the cover letter submitted for each job!
- 📊 **Application Export & History**: Automatically tracks every submission in a local SQLite database and exports to `applied.json` (viewable via `applypilot applied`).
- 🧠 **Screening Q&A Knowledge Base (`applypilot qa`)**: Learns and stores your answers to screening questions so recurring questions are answered consistently.
- 🔑 **Credential Manager (`applypilot creds`)**: Stores logins and passwords generated for ATS portals so you never get locked out.
- 🤝 **Human-In-The-Loop (HITL)**: If an unknown CAPTCHA or 2FA/MFA prompt appears, the agent pauses, asks for your input, and resumes once resolved.

---

## How It Works Under the Hood

```
┌─────────────────────────────────────────────────────────────┐
│                       ApplyPilot CLI                        │
│             applypilot apply --url <JOB_URL>                │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌───────────────────────┐             ┌───────────────────────┐
│     User Profile      │             │   Application Files   │
│    (profile.json)     │             │     (documents/)      │
│  - Personal Details   │             │  - cv.pdf             │
│  - Work Authorization │             │  - cover_letter.pdf   │
│  - Availability       │             │  - other_docs.pdf     │
│  - Experience/Edu     │             │  - visum, transcripts │
└───────────┬───────────┘             └───────────┬───────────┘
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Instruction & Prompt Engine                 │
│         (documents/prompt.txt + src/applypilot/apply/)      │
│  - Dynamic system instructions with document hierarchy     │
│  - Injects verified profile facts (NEVER hallucinates)     │
│  - Incorporates past Q&A knowledge base answers             │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            Autonomous Browser Agent Subprocess              │
│     ┌─────────────────────────────────────────────────┐     │
│     │  Option A: Claude Code CLI (Claude 3.7 Sonnet)  │     │
│     │  Option B: Hermes Agent (DeepSeek / NVIDIA NIM) │     │
│     └─────────────────────────────────────────────────┘     │
│                              │                              │
│                Playwright MCP / Chrome CDP                  │
│                              ▼                              │
│              Controlled Google Chrome Window                │
│    (Navigates form, uploads files, fills text fields)       │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    On Successful Submit                     │
│  1. Moves documents/cover_letter.pdf -> applied_cv/<url>.pdf│
│  2. Records application in applypilot.db                    │
│  3. Appends record to applied.json                          │
└─────────────────────────────────────────────────────────────┘
```

---

## System Requirements

| Tool | Minimum Version | Purpose |
|------|-----------------|---------|
| **Python** | 3.11 or higher | Core ApplyPilot runtime |
| **Git** | Any modern version | Downloading and updating the code |
| **Google Chrome** | Latest stable | The browser controlled by the agent |
| **Node.js** | v18.0 or higher (with `npm` & `npx`) | Required for Playwright MCP server |
| **AI Agent Backend** | **Hermes Agent** *(Free/Open Source)* OR **Claude Code CLI** | The autonomous brain that operates the browser |

---

## Step-by-Step Setup Guide

Follow the instructions below for your operating system. Even if you have never used a terminal before, follow these steps line by line.

---

### 🍎 macOS Setup

#### Step 1: Open Terminal
Press `Command (⌘) + Space`, type **Terminal**, and press `Enter`.

#### Step 2: Install Homebrew (if not already installed)
Homebrew is the package manager for Mac. In Terminal, run:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Step 3: Install Python, Git, and Node.js
```bash
brew install python git node
```
Make sure Google Chrome is installed from [google.com/chrome](https://www.google.com/chrome/).

#### Step 4: Clone the ApplyPilot Repository
Choose a folder where you want ApplyPilot to live (for example, `Documents`):
```bash
cd ~/Documents
git clone https://github.com/TusharKhari/ApplyPilot-f.git ApplyPilot
cd ApplyPilot
```

#### Step 5: Create and Activate a Python Virtual Environment
A virtual environment keeps ApplyPilot's packages isolated:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
*(Whenever you open a new Terminal window to run ApplyPilot, run `source .venv/bin/activate` first. You will see `(.venv)` in your terminal prompt).*

#### Step 6: Install ApplyPilot in Editable Mode
```bash
pip install --upgrade pip
pip install -e .
```

#### Step 7: Install Your Preferred AI Agent

You can choose **Hermes Agent** (recommended for low cost and open models) or **Claude Code CLI** (or both!):

- **Option A: Hermes Agent (Open Source — Recommended)**:
  Install Hermes Agent in your environment:
  ```bash
  pip install hermes-agent
  ```
  *Alternatively, via the official install script:*
  ```bash
  curl -fsSL https://raw.githubusercontent.com/nousresearch/hermes-agent/main/install.sh | bash
  ```
  Verify the installation:
  ```bash
  hermes --version
  ```

- **Option B: Claude Code CLI**:
  Install globally via npm:
  ```bash
  npm install -g @anthropic-ai/claude-code
  ```
  Log in to your Claude account by running:
  ```bash
  claude
  ```
  Follow the on-screen prompt to authenticate with Anthropic, then type `/exit` to return to your terminal.

---

### 🪟 Windows Setup

#### Step 1: Open PowerShell as Administrator
Press the `Windows Key`, type **PowerShell**, right-click **Windows PowerShell**, and select **Run as administrator**.

#### Step 2: Enable Script Execution
By default, Windows blocks PowerShell scripts. Run this command and press `Y` (Yes) when prompted:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```
You can now close the administrator window and open a regular PowerShell window.

#### Step 3: Install Prerequisites
1. **Python 3.11+**: Download the installer from [python.org](https://www.python.org/downloads/).
   > ⚠️ **IMPORTANT**: During installation, check the box that says **"Add python.exe to PATH"**!
2. **Git**: Download and install from [git-scm.com](https://git-scm.com/).
3. **Node.js**: Download the LTS installer from [nodejs.org](https://nodejs.org/).
4. **Google Chrome**: Ensure Chrome is installed in its default location (`C:\Program Files\Google\Chrome\Application\chrome.exe`).

#### Step 4: Clone the ApplyPilot Repository
In PowerShell, navigate to where you want the project:
```powershell
cd $HOME\Documents
git clone https://github.com/TusharKhari/ApplyPilot-f.git ApplyPilot
cd ApplyPilot
```

#### Step 5: Create and Activate a Python Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```
*(If PowerShell shows a script execution error, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` then try activating again. You will see `(.venv)` in your prompt).*

#### Step 6: Install ApplyPilot in Editable Mode
```powershell
python -m pip install --upgrade pip
pip install -e .
```

#### Step 7: Install Your Preferred AI Agent

- **Option A: Hermes Agent (Open Source — Recommended)**:
  ```powershell
  pip install hermes-agent
  ```
  Verify the installation:
  ```powershell
  hermes --version
  ```

- **Option B: Claude Code CLI**:
  ```powershell
  npm install -g @anthropic-ai/claude-code
  ```
  Log in to your Claude account:
  ```powershell
  claude
  ```
  Follow the login instructions in your browser, then type `/exit` to return to PowerShell.

---

## 🤖 Choosing & Configuring Your AI Agent (Claude vs. Hermes)

ApplyPilot supports two autonomous browser agent engines: **Hermes Agent** and **Claude Code CLI**. You can use whichever fits your workflow best.

### Why Use Hermes Agent?
1. **No Expensive Anthropic Subscription**: You don't need a Claude Max or Claude Pro account.
2. **Flexible & Cost-Effective LLM Backends**:
   - **DeepSeek** (`deepseek-flash`): Incredibly fast, smart, and costs fractions of a cent per application.
   - **NVIDIA NIM** (`nvidia/nemotron-3.5-lightning-30b-a3b` or `moonshotai/kimi-k3`): Free tier credits available with top-tier reasoning.
   - **Google Gemini** (`gemini-3.6-flash`): Generous free tier via Google AI Studio.
3. **100% Open Source**: Developed by Nous Research for autonomous local task execution.

### Why Use Claude Code CLI?
1. Powered directly by Anthropic's flagship **Claude 3.7 / 3.5 Sonnet**.
2. Industry-leading browser comprehension and complex edge-case recovery.
3. Requires an Anthropic Claude subscription or API billing.

### Agent Comparison & Supported Models

| Feature | Hermes Agent 🪶 | Claude Code CLI 🧠 |
|---|---|---|
| **License** | Open Source (Nous Research) | Proprietary (Anthropic) |
| **Subscription Required?** | ❌ No subscription required | ✅ Requires Anthropic account / subscription |
| **Default Models** | `deepseek-flash`<br>`nvidia/nemotron-3.5-lightning-30b-a3b`<br>`gemini-3.6-flash` | `sonnet` (Claude 3.7/3.5 Sonnet) |
| **Supported API Keys** | `DEEPSEEK_API_KEY`, `NVIDIA_API_KEY`, `GEMINI_API_KEY` | Anthropic browser login / Max plan |
| **Average Cost per Job** | ~$0.04 (or free tier) | Included in subscription plan |

### How to Switch Between Agents

ApplyPilot makes switching completely effortless:

1. **Automatic Detection (Hermes Default)**:
   If Hermes is installed in your system (on PATH or at `~/.local/bin/hermes`), ApplyPilot **automatically selects Hermes** as your default agent! If not found, it falls back to Claude.

2. **Explicit CLI Flag**:
   You can force either agent at any time when running:
   ```bash
   # Use Hermes Agent
   applypilot apply --agent hermes --url "https://..."

   # Use Claude Code CLI
   applypilot apply --agent claude --url "https://..."
   ```

3. **Set Default in `.env`**:
   Add this line to your `.env` file to lock in your preferred agent:
   ```bash
   APPLYPILOT_AGENT=hermes   # or APPLYPILOT_AGENT=claude
   ```

---

## Setting Up API Keys (.env)

ApplyPilot reads environment variables from a `.env` file in the project root (or `~/.applypilot/.env`).

### 1. Create your `.env` file from the example

**On macOS / Linux:**
```bash
cp .env.example .env
```

**On Windows (PowerShell):**
```powershell
copy .env.example .env
```

### 2. Configure your keys
Open `.env` in any text editor (VS Code, Notepad, or TextEdit):

```bash
# ===========================================================================
# AI Agent & Provider Selection
# ===========================================================================
# Choose default agent: "hermes" or "claude" (defaults to hermes if installed)
APPLYPILOT_AGENT=hermes

# ===========================================================================
# LLM Provider Keys
# ===========================================================================

# 1. DeepSeek (Recommended for Hermes Agent — high speed & lowest cost)
# Get a key at: https://platform.deepseek.com/
DEEPSEEK_API_KEY=sk-...

# 2. NVIDIA NIM (Great free tier with Kimi-K3 & Nemotron-3.5)
# Get a key at: https://build.nvidia.com/
NVIDIA_API_KEY=nvapi-...

# 3. Google Gemini (Recommended for free tier)
# Get your free key at: https://aistudio.google.com/
GEMINI_API_KEY=AIzaSy...

# 4. Optional Fallback Providers
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# ===========================================================================
# Optional: CAPTCHA Solver
# ===========================================================================
# If you want automatic CAPTCHA solving (hCaptcha, Turnstile, reCAPTCHA):
# Get a key at: https://capsolver.com
CAPSOLVER_API_KEY=
```

> 💡 **Quick Start for Hermes Users**: Put your `DEEPSEEK_API_KEY` (or `NVIDIA_API_KEY` or `GEMINI_API_KEY`) into `.env`. ApplyPilot automatically configures the worker environment to use your key!

---

## Configuring Your Profile (profile.json)

ApplyPilot reads your candidate profile directly from `profile.json` in the project root (or `~/.applypilot/profile.json`). A template is provided in `profile.example.json`.

### How to Edit Your Profile

Open `profile.json` in an editor. Below is an explanation of the main sections:

```json
{
  "personal": {
    "first_name": "Alex",
    "last_name": "Smith",
    "full_name": "Alex Smith",
    "email": "alex.smith@example.com",
    "phone": "+1 555-0199",
    "address": "123 Market St",
    "city": "San Francisco",
    "state": "California",
    "postal_code": "94105",
    "country": "United States",
    "linkedin_url": "https://linkedin.com/in/alexsmith",
    "github_url": "https://github.com/alexsmith",
    "portfolio_url": "https://alexsmith.dev",
    "password": "StrongPassword123!" // Used to create ATS portal accounts automatically
  },
  "work_authorization": {
    "legally_authorized_to_work": "Yes",
    "require_sponsorship": "No",
    "work_permit_type": "Citizen / Permanent Resident / Student Visa"
  },
  "availability": {
    "earliest_start_date": "Immediately",
    "notice_period": "2 weeks"
  },
  "compensation": {
    "salary_expectation": "85000",
    "salary_currency": "USD",
    "hourly_wage_werkstudent_eur": 15
  },
  "files": {
    "cover_letter": "documents/cover_letter.pdf",
    "other_documents": "documents/other_docs.pdf",
    "enrollment_certificate": "documents/Certificate of enrolment.pdf",
    "transcript_of_records": "documents/TranscriptOfRecords.pdf",
    "visa_work_permit": "documents/visum.pdf",
    "profile_photo": "documents/prof_img.png",
    "cv_pdf": "documents/cv.pdf"
  }
}
```

> 🔒 **Security Note**: `profile.json` and `.env` contain sensitive personal data. They are added to `.gitignore` so they are never committed to a public Git repository.

---

## Managing Documents & The Cover Letter Feature

All candidate files live inside the `documents/` folder in the project:

```text
ApplyPilot/
├── documents/
│   ├── cv.pdf               <-- Your master resume / CV (Priority 1)
│   ├── cover_letter.pdf     <-- Active cover letter for the job (Priority 2)
│   ├── other_docs.pdf       <-- Transcripts, letters, certificates (Priority 3)
│   ├── visum.pdf            <-- (Optional) Work permit / Visa (Priority 4)
│   ├── TranscriptOfRecords  <-- (Optional) University grades (Priority 4)
│   └── prompt.txt           <-- Custom agent instructions
├── applied_cv/              <-- Archived cover letters (Auto-generated)
└── applied.json             <-- List of all applied jobs (Auto-updated)
```

### Document Upload Priority Hierarchy
When ApplyPilot navigates an application form, it strictly adheres to this hierarchy:
1. **Priority 1 — Resume / CV (`cv.pdf`)**: Always uploaded fresh to the Resume / CV / Lebenslauf field. Any pre-existing resume in an ATS account is deleted and replaced.
2. **Priority 2 — Cover Letter (`cover_letter.pdf`)**: Uploaded to Cover Letter / Anschreiben / Motivationsschreiben fields. If the form only provides a text area instead of a file upload, ApplyPilot extracts the text from `cover_letter.pdf` (or `cover_letter.txt`) and pastes it cleanly into the field.
3. **Priority 3 — Other Documents (`other_docs.pdf`)**: Uploaded to general attachment fields, "Weitere Dokumente", "Work Samples", or "Zeugnisse/Zertifikate".
4. **Priority 4 — Specific Documents**: Documents such as University Enrollment Certificates (*Immatrikulationsbescheinigung*), Academic Transcripts (*Notenspiegel*), or Residence Permits (*Aufenthaltstitel*) are uploaded **only** if the form provides an explicit field dedicated to that specific file.

### 🌟 Automatic Cover Letter Archiving
Whenever an application is completed or marked as applied:
1. ApplyPilot takes `documents/cover_letter.pdf`.
2. It renames the file using the job URL (e.g. `https___company.workdayjobs.com_job_123.pdf`).
3. It moves the file into the `applied_cv/` directory.
4. It logs the job into `applied.json`.

This ensures you can always review the exact cover letter that was sent to each employer!

---

## Customizing Application Instructions (prompt.txt)

You can customize exactly how the AI agent acts by editing `documents/prompt.txt`.

This file controls the agent's behavior and personality. For example, you can tell it:
- *"Never check TalentPool or marketing consent checkboxes without asking me first."*
- *"If the job posting is in German, write responses in professional German."*
- *"If asked about relocation, say I am flexible within Baden-Württemberg only."*
- *"For Werkstudent roles, weekly availability is 20 hours/week."*

### How to Preview Instructions Before Running
Want to see the exact prompt that will be sent to the AI agent before opening a browser? Use the `--gen` flag:
```bash
applypilot apply --url "https://job-url-here" --gen
```
This generates a prompt file in `~/.applypilot/` so you can inspect every instruction and field mapping without touching the browser.

---

## How to Run ApplyPilot

Make sure your virtual environment is active (`source .venv/bin/activate` on Mac or `.venv\Scripts\Activate.ps1` on Windows).

### 1. Recommended Workflow (Review-First Mode)

This is the safest and most effective way to apply:

1. **Place your cover letter**: Put your cover letter for the role at `documents/cover_letter.pdf` (if you have one).
2. **Run the apply command with the job URL**:
   ```bash
   applypilot apply --url "https://boards.greenhouse.io/company/jobs/123456"
   ```
3. **Watch the automation**:
   - Google Chrome opens automatically.
   - The AI agent navigates to the URL.
   - It fills out your name, contact information, education, and employment history.
   - It uploads your `cv.pdf` and `cover_letter.pdf`.
   - It answers screening questions using your profile.
4. **Human Review**:
   - Because `--stop-before-submit` is enabled by default, the agent stops on the final confirmation page.
   - Review the fields on screen.
   - Click the final **Submit Application** button yourself!
5. **Archiving**:
   - ApplyPilot automatically moves your `cover_letter.pdf` into `applied_cv/` and updates `applied.json`!

---

### 2. Running with Hermes Agent (Open Source / Low Cost)

To run with **Hermes Agent** using your preferred model backend:

```bash
# Using DeepSeek (Default model for Hermes if DEEPSEEK_API_KEY is present)
applypilot apply --agent hermes --model deepseek-flash --url "https://job-url"

# Using NVIDIA NIM (Nemotron 3.5 Lightning)
applypilot apply --agent hermes --model nvidia/nemotron-3.5-lightning-30b-a3b --url "https://job-url"

# Using NVIDIA NIM (Moonshot Kimi-K3)
applypilot apply --agent hermes --model moonshotai/kimi-k3 --url "https://job-url"

# Using Google Gemini
applypilot apply --agent hermes --model gemini-3.6-flash --url "https://job-url"
```

---

### 3. Running with Claude Code CLI

To run with **Claude Code CLI** (uses Claude 3.7 / 3.5 Sonnet):

```bash
applypilot apply --agent claude --model sonnet --url "https://job-url"
```

---

### 4. Preview Mode (Dry Run)
Test an application flow without submitting anything:
```bash
applypilot apply --url "https://jobs.lever.co/company/123" --dry-run
```

---

### 5. Fully Autonomous Mode (Auto-Submit)
If you want ApplyPilot to click the final submit button without waiting for you:
```bash
applypilot apply --url "https://jobs.lever.co/company/123" --auto-submit
```

---

### 6. Running Headless (Invisible Browser)
If you do not want the browser window to pop up on your screen:
```bash
applypilot apply --url "https://jobs.lever.co/company/123" --headless
```

---

## Complete CLI Command Reference

ApplyPilot provides a full-featured Command Line Interface built with Typer and Rich.

### Overview of All Commands

| Command | Subcommand | Purpose |
|---------|------------|---------|
| `applypilot apply` | *(none)* | Launch browser automation to fill and submit job applications. |
| `applypilot status` | *(none)* | Display detailed pipeline metrics, score funnels, and state distribution. |
| `applypilot applied` | *(none)* | Display all submitted applications and export records to `applied.json`. |
| `applypilot qa` | `list` | Show stored screening question-and-answer pairs from past runs. |
| | `stats` | Display statistics on Q&A pairs, outcomes, and ATS sources. |
| | `export` | Export Q&A knowledge base to a YAML file for bulk editing. |
| | `import` | Import Q&A pairs from a YAML file. |
| `applypilot creds` | `list` | List saved ATS/portal credentials (passwords masked by default). |
| | `show` | Show full, unmasked login details for a single domain. |
| | `add` | Add or update credentials for a specific company or ATS portal. |
| | `set` | Update specific fields (email, password, notes) for an existing entry. |
| | `import-logs` | Automatically mine credentials created during past application runs from logs. |
| | `delete` | Remove saved credentials for a domain. |

---

### 1. `applypilot apply` (Core Automation Engine)

Launch autonomous browser workers to fill and submit job applications.

```bash
applypilot apply [OPTIONS]
```

#### All Supported Options & Flags

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--url` | | `None` | Direct application to a specific job posting URL. Bypasses database queue. |
| `--limit` | `-l` | `1` (or `None`) | Maximum number of applications to submit in this run. |
| `--workers` | `-w` | `1` | Number of parallel browser workers running concurrently. |
| `--min-score` | | `8` | Minimum fit score (1–10) required to select a job from the database. |
| `--max-score` | | `None` | Maximum fit score for job selection (useful for testing on lower-score jobs). |
| `--max-age-days` | | `14` | Skip jobs discovered older than N days (`0` = no age filter). |
| `--agent` | `-a` | `hermes` | Autonomous agent backend: `hermes` (recommended) or `claude`. |
| `--model` | `-m` | `sonnet` | Model name. Examples: `deepseek-v4-pro`, `deepseek-flash`, `nvidia/nemotron-3.5-lightning-30b-a3b`, `moonshotai/kimi-k3`, `gemini-3.6-flash`, or `sonnet`. |
| `--continuous` | `-c` | `False` | Run indefinitely, polling the database every 60s for new ready jobs. |
| `--dry-run` | | `False` | Fill form and preview all agent actions with browser dry-run protection enabled. |
| `--stop-before-submit` | | `True` | **(Default)** Fill complete form and pause on final review page for manual verification. |
| `--auto-submit` | | `False` | Automatically click final Submit Application button without human pause. |
| `--headless` | | `False` | Run Chrome in headless mode (invisible, no GUI window). |
| `--doc-format` | | `docx` | Document format for resumes/cover letters: `docx` or `pdf`. |
| `--gen` | | `False` | Generate the prompt file in `~/.applypilot/` for manual inspection without opening Chrome. |
| `--no-hitl` | | `False` | Skip Human-in-the-Loop waits: park `needs_human` jobs and proceed immediately. Ideal for overnight runs. |
| `--no-focus` | | `False` | Prevent Chrome windows from stealing keyboard focus (Linux/GNOME). |
| `--fresh-sessions` | | `False` | Refresh Chrome session cookies from your personal Chrome profile before launching. |
| `--sessions` | | `False` | List all saved ATS sessions (Workday, etc.) and cookie ages. |
| `--clear-session` | | `None` | Clear a saved ATS session by name (e.g. `--clear-session workday`). |
| `--mark-applied` | | `None` | Manually mark a job URL as applied in the database without running Chrome. |
| `--mark-failed` | | `None` | Manually mark a job URL as failed in the database (provide URL). |
| `--fail-reason` | | `None` | Optional reason string when using `--mark-failed`. |
| `--reset-failed` | | `False` | Reset all failed jobs back to ready for retry. |
| `--reset-category` | | `None` | Reset all jobs in a specific failure category (e.g. `--reset-category blocked_technical`). |

#### Practical Examples

```bash
# 1. Apply to a specific job URL in safe review mode (stops before submit):
applypilot apply --url "https://boards.greenhouse.io/company/jobs/123456"

# 2. Test application flow without submitting (Dry Run):
applypilot apply --url "https://jobs.lever.co/company/789" --dry-run

# 3. Apply using Hermes Agent with DeepSeek V4 Pro:
applypilot apply --agent hermes --model deepseek-v4-pro --url "https://company.jobs.personio.com/job/123"

# 4. Apply using Hermes Agent with NVIDIA NIM:
applypilot apply --agent hermes --model nvidia/nemotron-3.5-lightning-30b-a3b --url "https://job-url"

# 5. Apply using Claude Code CLI (Sonnet):
applypilot apply --agent claude --model sonnet --url "https://job-url"

# 6. Run a batch of 5 jobs from the database using 2 parallel browser windows:
applypilot apply --workers 2 --limit 5

# 7. Overnight unattended batch run (no human waits, continuous queue polling):
applypilot apply --continuous --no-hitl --auto-submit

# 8. Inspect generated prompt without launching browser:
applypilot apply --url "https://job-url" --gen

# 9. List and clear saved ATS login sessions:
applypilot apply --sessions
applypilot apply --clear-session workday

# 10. Reset retryable technical failures back to queue:
applypilot apply --reset-category blocked_technical
```

---

### 2. `applypilot status` (Pipeline Analytics)

Display rich terminal tables detailing the state of your application pipeline.

```bash
applypilot status
```

**Information Displayed:**
- **Pipeline Overview**: Total jobs discovered, scraped, scored by LLM, tailored, ready to apply, applied, and failed.
- **Score Distribution**: Visual ASCII colored histogram of fit scores from 1 to 10.
- **Pipeline Funnel by Score**: Stage-by-stage breakdown (Cover Ready, Tailored, Needs Tailor, Applied, Errors).
- **Apply Categories**: Categorized status breakdown (`applied`, `needs_human`, `blocked_auth`, `blocked_technical`, `archived_ineligible`, `archived_expired`, `manual_only`).
- **Jobs by Source**: Job count breakdown across platforms (Greenhouse, Lever, Personio, Workday, HackerNews, etc.).
- **State Machine Distribution**: Current lifecycle status distribution of all database records.

---

### 3. `applypilot applied` (Export & View Submissions)

Display a clean summary table of all submitted applications and automatically export/refresh `applied.json`.

```bash
# View submissions and update applied.json in the project root:
applypilot applied

# Export records to a custom file location:
applypilot applied --output ~/Desktop/my_applications.json
```

#### Supported Options
* `-o, --output <path>`: Custom file path for the exported JSON file.

---

### 4. `applypilot qa` (Screening Questions Knowledge Base)

Manage the persistent question-and-answer database used by agents to answer recurring ATS screening questions.

```bash
applypilot qa COMMAND [ARGS]...
```

#### Subcommands

##### `applypilot qa list`
List stored Q&A pairs with question text, answer, source, outcome status, and field type.
```bash
# Show the first 50 stored questions (default):
applypilot qa list

# Show up to 100 questions:
applypilot qa list --limit 100
```

##### `applypilot qa stats`
Show knowledge base statistics: total question count, unique questions, breakdown by source (`human` vs `llm`), outcome (`accepted` vs `rejected`), and ATS platform.
```bash
applypilot qa stats
```

##### `applypilot qa export`
Export all stored Q&A pairs to a clean YAML file for review or manual modification.
```bash
# Export to default 'qa_export.yaml':
applypilot qa export

# Export to a custom path:
applypilot qa export --output documents/qa_backup.yaml
```

##### `applypilot qa import`
Import Q&A pairs from a YAML file into the database.
```bash
applypilot qa import documents/qa_backup.yaml
```

---

### 5. `applypilot creds` (Portal Credentials Manager)

Manage login credentials generated or used for company career portals (Workday, SmartRecruiters, iCIMS, etc.).

```bash
applypilot creds COMMAND [ARGS]...
```

#### Subcommands

##### `applypilot creds list`
List all saved site credentials. Passwords are automatically masked by default.
```bash
# List credentials with masked passwords:
applypilot creds list

# List credentials with plaintext passwords displayed:
applypilot creds list --show
```

##### `applypilot creds show`
Display full details for a single domain including email, password, notes, and the initial job URL.
```bash
applypilot creds show myworkdayjobs.com
```

##### `applypilot creds add`
Add or update credentials for a specific company or ATS domain.
```bash
# Add with interactive password prompt (secure):
applypilot creds add myworkdayjobs.com --email candidate@example.com

# Add with inline parameters:
applypilot creds add lever.co --email user@example.com --password "Secret123!" --site "Lever Portal" --notes "Created for Acme Corp"
```

##### `applypilot creds set`
Update existing credentials for a domain without overwriting untouched fields.
```bash
applypilot creds set myworkdayjobs.com --email newemail@example.com
```

##### `applypilot creds import-logs`
Scan apply logs in `~/.applypilot/logs/` for credentials created during previous autonomous sessions and import them into the database.
```bash
# Preview what credentials would be imported without writing:
applypilot creds import-logs --dry-run

# Import credentials automatically:
applypilot creds import-logs --yes
```

##### `applypilot creds delete`
Remove saved credentials for a domain from the database.
```bash
applypilot creds delete myworkdayjobs.com
```

---

### Global Flags & Keyboard Controls

#### Global CLI Flags
- `--version`, `-V`: Display the current ApplyPilot version and exit.
- `--help`: Display available commands, arguments, and default values.

#### Live Interactive Keyboard Controls
While an application worker is actively running in Chrome, you can interact with it directly from your terminal:
- **`p` or `Space`**: **Pause & Take Over** — Immediately pauses the agent, leaving Chrome open so you can interact with the page manually. Press `p` or `Space` again to return control to the agent.
- **`Ctrl + C`**: **Skip Job** — Safely skips the current job and moves on to the next application.
- **`Ctrl + C` (twice)**: **Emergency Stop** — Immediately halts all browser workers and exits cleanly.

---

## Troubleshooting & FAQs

### 1. "Command not found: applypilot"
You need to activate your virtual environment:
- **macOS / Linux**: `source .venv/bin/activate`
- **Windows**: `.venv\Scripts\Activate.ps1`
Then ensure ApplyPilot is installed: `pip install -e .`

### 2. Windows: "cannot be loaded because running scripts is disabled on this system"
Open PowerShell and run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Then run `.venv\Scripts\Activate.ps1` again.

### 3. How do I verify Hermes Agent is installed?
Run in your terminal:
```bash
hermes --version
```
If not found, install it with:
```bash
pip install hermes-agent
```
Make sure `DEEPSEEK_API_KEY`, `NVIDIA_API_KEY`, or `GEMINI_API_KEY` is present in your `.env` file.

### 4. "Autonomous Agent CLI not found"
ApplyPilot requires at least one autonomous agent:
- Either install **Hermes Agent**: `pip install hermes-agent`
- Or install **Claude Code CLI**: `npm install -g @anthropic-ai/claude-code` followed by `claude` (to log in).

### 5. "Chrome/Chromium not found"
Ensure Google Chrome is installed. If Chrome is installed in a non-standard location, set the `CHROME_PATH` environment variable:
- **macOS**:
  ```bash
  export CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  ```
- **Windows (PowerShell)**:
  ```powershell
  $env:CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
  ```

### 6. What if an employer asks for a CAPTCHA or Two-Factor Code (2FA)?
ApplyPilot has built-in **Human-in-the-Loop (HITL)** handling. The agent will pause and ask you in the terminal to solve the CAPTCHA or enter the 2FA code in the open Chrome window. Once you complete it, press Enter in the terminal, and ApplyPilot will continue where it left off.

---

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0-only)**. See the [LICENSE](LICENSE) file for details.
