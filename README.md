# SATHI 2026 - Program Management System
## Vision-Aid: Smart Assistive Technology for Holistic Inclusion

A web-based system to manage Vision-Aid's SATHI program — tracking beneficiaries,
assistive device distribution, partner organizations, training, and impact measurement.

## Quick Start

```bash
pip install Flask openpyxl python-docx
cd sathi
python app.py
# Open http://localhost:5000
# Default password: sathi2026
```

The database (sathi.db) is auto-created on first run with seeded device types and 2026 milestones.

## Features

- **Dashboard** — Key metrics, milestones, upcoming events, recent activity
- **Partners** — Hospitals, schools, NGOs, Rotary clubs (CRUD + MoU tracking)
- **Beneficiaries** — Registration matching official template, Excel upload/download
- **Events** — Distribution events, awareness camps, training sessions
- **Distributions** — Device-to-beneficiary tracking with serial numbers
- **Inventory** — Procurement batches, stock levels by device type
- **Training** — Session records, completion, certificates
- **Follow-ups** — Impact tracking, satisfaction ratings, success stories
- **Budget** — Expense tracking by category/quarter/vendor
- **Milestones** — 2026 targets with visual progress bars
- **Reports** — Word (.docx) quarterly/annual reports, Excel (.xlsx) exports, CSV exports
- **Activity Log** — Full audit trail of all system actions

## Password

Set in `config.py`. Falls back to `SATHI_PASSWORD` environment variable. Remove both for no auth.

## Tech Stack

Python 3 + Flask + sqlite3 (built-in) + openpyxl + python-docx
WCAG 2.1 AA accessible, responsive design.
