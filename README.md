# ApplyPilot

**Autonomous job application form filling and tracking. Open source.**

ApplyPilot automates the tedious part of job searching: opening job application forms, filling in personal details, work authorization, education, experience, answering complex screening questions with a persistent Q&A knowledge base, uploading resumes, and saving application records to `applied.json` and a local SQLite database.

---

## Core Features

- **Autonomous Form Filling**: Uses autonomous browser agents (Hermes Agent or Claude Code CLI + Chrome CDP + Playwright MCP) to navigate and fill out application forms across major ATS platforms (Greenhouse, Lever, Workday, iCIMS, Ashby, etc.).
- **Direct Application by URL**: Run `applypilot apply --url <URL>` to immediately launch an automated browser session for any job posting.
- **Application Saving & Export**: Automatically logs all submitted applications into SQLite and exports them to `applied.json` (viewable via `applypilot applied`).
- **Screening Q&A Knowledge Base**: Learns and stores your answers to employer screening questions in a local database (`applypilot qa`), answering recurring questions automatically.
- **Account & Credential Management**: Automatically saves new candidate logins created on employer portals in `applypilot creds`.
- **Human-In-The-Loop (HITL)**: Intelligently pauses and notifies you when encountering unsolvable CAPTCHAs, 2FA codes, or novel screening questions, then resumes once solved.
- **Anti-Fingerprinting Stealth**: Employs patched Chromium launch flags and Chrome extension script injections to ensure seamless form interaction.

---

## Quick Start

### 1. Installation

```bash
git clone https://github.com/ibarrajo/ApplyPilot.git
cd ApplyPilot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configuration

Set up your candidate profile:
- Edit `profile.json` with your personal information, work authorization, education, experience, and links.
- Place your master resume at `~/.applypilot/resume.pdf` or in the `documents/` folder.

### 3. Usage

#### Apply to a Specific Job URL:
```bash
applypilot apply --url "https://job-boards.greenhouse.io/company/jobs/12345"
```

#### Preview Actions (Dry Run):
```bash
applypilot apply --url "https://job-boards.greenhouse.io/company/jobs/12345" --dry-run
```

#### View All Applied Jobs & Update `applied.json`:
```bash
applypilot applied
```

#### Manage Screening Q&A Answers:
```bash
applypilot qa list
applypilot qa add "Are you authorized to work in Germany?" "Yes"
```

#### Manage ATS Credentials:
```bash
applypilot creds list
```

#### Check Status:
```bash
applypilot status
```

---

## License

AGPL-3.0-only
