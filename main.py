import os
from pathlib import Path
from typing import Optional

import json
import os
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from tools import calendar_client, email_sender, pdf_parser, scorer, storage

console = Console()
app = typer.Typer(help="TalentScout AI demo orchestrator")


def _validate_paths(cv: Path, jd: Path) -> None:
    missing = [str(p) for p in (cv, jd) if not p.exists()]
    if missing:
        raise FileNotFoundError(f"No se encontraron archivos: {', '.join(missing)}")


def _print_warnings(warnings):
    for w in warnings:
        console.print(f"[yellow]Aviso:[/] {w}")


@app.command()
def run(
    cv: Path = typer.Argument(..., help="Path to resume file (.pdf or .md/.txt)"),
    jd: Path = typer.Argument(..., help="Path to job description file (.txt/.md)"),
    threshold: int = typer.Option(70, help="Score threshold to approve candidate"),
    candidate_name: str = typer.Option("Candidate", help="Candidate name"),
    candidate_email: str = typer.Option("candidate@example.com", help="Candidate email"),
    anonymize: bool = typer.Option(True, help="Anonymize resume before scoring"),
    db_path: Path = typer.Option(Path("talentscout.db"), help="SQLite database path"),
    export_json: Optional[Path] = typer.Option(None, help="Path to save structured result as JSON"),
    skip_email: bool = typer.Option(False, help="Skip sending (or simulating) email even if approved"),
):
    load_dotenv()
    _validate_paths(cv, jd)

    storage.init_db(db_path)

    console.rule("Ingestion")
    try:
        cv_text = pdf_parser.ingest(cv, anonymize_data=anonymize)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to read resume:[/] {exc}")
        raise typer.Exit(code=1)
    try:
        jd_text = jd.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to read JD:[/] {exc}")
        raise typer.Exit(code=1)

    console.rule("Evaluation")
    card = scorer.score_candidate(cv_text, jd_text, threshold=threshold)
    _print_warnings(card.warnings)
    details = (
        f"Score: {card.score}\nStatus: {card.status}\n"
        f"Similarity: {card.similarity:.2f}\n"
        f"Skills match: {len(card.skills_matched)} / {len(card.skills_matched) + len(card.skills_missing)}\n"
        f"Experience CV/JD: {card.experience_cv} / {card.experience_jd}\n"
        f"Missing: {', '.join(card.skills_missing) if card.skills_missing else 'None'}\n"
        f"Matched: {', '.join(card.skills_matched) if card.skills_matched else 'None'}\n"
        f"{card.reasoning}"
    )
    console.print(Panel.fit(details, title="Result"))

    storage.save_candidate(
        db_path,
        {
            "name": candidate_name,
            "email": candidate_email,
            "score": card.score,
            "status": card.status,
            "reasoning": card.reasoning,
        },
    )

    if export_json:
        payload = scorer.structured_output(card) | {
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
        }
        export_json.parent.mkdir(parents=True, exist_ok=True)
        export_json.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        console.print(f"Result saved to {export_json}")

    if card.status == "APPROVED" and not skip_email:
        slots = calendar_client.fetch_available_slots()
        msg = email_sender.build_invite_email(candidate_email, candidate_name, slots)
        email_sender.send_email(msg)
        console.print("Invitation prepared (test mode if EMAIL_TEST_MODE=true).")
    elif card.status == "APPROVED" and skip_email:
        console.print("Approved, but email skipped via --skip-email.")
    else:
        console.print("Profile requires human review. No email sent.")


if __name__ == "__main__":
    app()
