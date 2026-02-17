# TalentScout AI: Automated Screening & Interview Prep

Executable demo of a modular agent that reads resumes, compares them to a Job Description, scores the candidate, and prepares an interview invitation using decoupled tools.

## Architecture
- CLI orchestrator in [main.py](main.py).
- Document extraction and anonymization in [tools/pdf_parser.py](tools/pdf_parser.py).
- Semantic scoring and matching in [tools/scorer.py](tools/scorer.py).
- Calendar slots and email (test mode by default) in [tools/calendar_client.py](tools/calendar_client.py) and [tools/email_sender.py](tools/email_sender.py).
- SQLite persistence in [tools/storage.py](tools/storage.py).
- Sample data in [data/resume.md](data/resume.md) and [data/jd.txt](data/jd.txt).

## Requirements
- Python 3.10+
- Optional: OPENAI_API_KEY for embeddings. Without it, the system uses local heuristics.

## Quick setup
1) Create a virtual environment (recommended).
2) Install dependencies:
```
pip install -r requirements.txt
```
3) Copy [.env.example](.env.example) to `.env` and set keys (OPENAI_API_KEY optional, EMAIL_TEST_MODE=true prevents real emails).

## Demo run
Use the included fake data:
```
python main.py data/resume.md data/jd.txt --threshold 70 --candidate-name "Alice" --candidate-email alice@example.com
```
Useful options:
- `--export-json outputs/result.json` saves the structured dict.
- `--skip-email` prevents sending (or simulating) email even if approved.
- `--threshold 80` raises the approval bar.

Expected outputs:
- Prints score, similarity, matched/missing skills, and warnings (e.g., missing OPENAI_API_KEY).
- Persists the record in `talentscout.db`.
- In test mode, shows the email that would be sent with suggested slots.

## Flow overview
1. **Perception:** [pdf_parser.ingest](tools/pdf_parser.py#L18) reads PDF/Markdown and anonymizes basic fields.
2. **Cognition:** [scorer.score_candidate](tools/scorer.py#L76) extracts skills, computes semantic similarity (embeddings if key is present, else local cosine) and experience.
3. **Action:** If `score >= threshold`, prepare slots via [calendar_client.fetch_available_slots](tools/calendar_client.py#L9) and build an email with [email_sender.build_invite_email](tools/email_sender.py#L6). Always writes to SQLite via [storage.save_candidate](tools/storage.py#L11).

## Quick customization
- Replace sample data in [data/](data) with real resumes (PDF or Markdown) and new JDs.
- Adjust the skill list in [tools/scorer.py](tools/scorer.py#L40) for your domain.
- Integrate your real calendar API inside [tools/calendar_client.py](tools/calendar_client.py#L9) and set `EMAIL_TEST_MODE=false` in `.env` to send real emails.

## Security notes
- Real email sending requires SMTP_USER and SMTP_PASSWORD in `.env`.
- Test mode avoids external traffic; keep it on for demos.
