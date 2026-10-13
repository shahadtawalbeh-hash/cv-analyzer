import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.analysis import MATCH_THRESHOLD, run_cv_analysis
from app.database import Base, SessionLocal, engine, get_db
from app.embedded_key import resolve_openai_api_key
from app.employer import router as employer_router
from app.keycheck import ping_openai_key
from app.mailout import send_summary_email
from app.models import AnalysisRun, Category, Job
from app.pdf_gate import PdfRejected, validate_pdf_upload
from app.pdf_text import extract_pdf_text
from app.seed import seed_if_empty

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="CV Fitboard", version="0.1.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "local-dev-secret-replace-me"),
    session_cookie="cv_matchbench_session",
    same_site="lax",
    https_only=False,
)

ILLUSTRATION_DIR = BASE_DIR / "static" / "illustrations"
ILLUSTRATION_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(employer_router)


def _migrate_db() -> None:
    from sqlalchemy import inspect, text

    try:
        insp = inspect(engine)
        if "jobs" not in insp.get_table_names():
            return
        existing_cols = [c["name"] for c in insp.get_columns("jobs")]
        if "employer_id" not in existing_cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN employer_id INTEGER"))
                conn.commit()
    except Exception:
        pass


def startup():
    Base.metadata.create_all(bind=engine)
    _migrate_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    startup()


def illustration_files() -> list[str]:
    if not ILLUSTRATION_DIR.exists():
        return []
    out: list[str] = []
    for p in sorted(ILLUSTRATION_DIR.glob("*.svg")):
        out.append(f"/static/illustrations/{p.name}")
    return out


def _recent_runs_view(db: Session) -> list[dict]:
    rows = db.query(AnalysisRun).order_by(AnalysisRun.id.desc()).limit(30).all()
    out: list[dict] = []
    for r in rows:
        top = 0
        try:
            arr = json.loads(r.matches_json)
            if arr:
                top = max(int(x.get("score", 0)) for x in arr)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        out.append(
            {
                "id": r.id,
                "filename": r.filename or "upload.pdf",
                "when": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                "top_score": top,
            }
        )
    return out


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    ills = illustration_files()
    rows = (
        db.query(Job, Category)
        .join(Category, Job.category_id == Category.id)
        .order_by(Category.name, Job.title)
        .all()
    )
    jobs_view = [
        {
            "id": job.id,
            "title": job.title,
            "company": job.company_hint,
            "category": cat.name,
            "requirements": job.requirements,
        }
        for job, cat in rows
    ]
    has_key = bool(resolve_openai_api_key(request))
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "request": request,
            "has_key": has_key,
            "threshold": MATCH_THRESHOLD,
            "jobs": jobs_view,
            "illustrations": ills,
            "recent_runs": _recent_runs_view(db),
        },
    )


@app.post("/actions/save-key")
async def save_key(request: Request, api_key: str = Form("")):
    ok, msg = ping_openai_key(api_key.strip())
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    request.session["openai_api_key"] = api_key.strip()
    return JSONResponse({"ok": True, "message": msg})


@app.post("/actions/logout")
async def logout(request: Request):
    request.session.pop("openai_api_key", None)
    return RedirectResponse("/", status_code=303)


@app.get("/api/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    row = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found.")
    return JSONResponse(
        {
            "run_id": row.id,
            "threshold": row.threshold,
            "profile": json.loads(row.profile_json or "{}"),
            "matches": json.loads(row.matches_json or "[]"),
            "training": json.loads(row.training_json or "[]"),
            "text_length": row.text_length,
            "extracted_preview": row.extracted_preview or "",
            "filename": row.filename,
        }
    )


def _email_body_for_run(row: AnalysisRun) -> str:
    lines: list[str] = []
    lines.append(f"File: {row.filename or 'upload.pdf'}")
    lines.append(f"Pass line: {row.threshold}%")
    lines.append("")
    lines.append("Profile:")
    lines.append(row.profile_json or "{}")
    lines.append("")
    lines.append("Scores:")
    lines.append(row.matches_json or "[]")
    lines.append("")
    lines.append("Courses:")
    lines.append(row.training_json or "[]")
    return "\n".join(lines)


@app.post("/actions/email-run")
async def email_run(
    run_id: int = Form(),
    to_email: str = Form(""),
    db: Session = Depends(get_db),
):
    row = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found.")
    try:
        send_summary_email(
            to_email.strip(),
            f"CV Fitboard run #{run_id}",
            _email_body_for_run(row),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=502, detail=f"Mail failed: {exc}") from exc
    return JSONResponse({"ok": True})


@app.post("/actions/analyze")
async def analyze(
    request: Request,
    db: Session = Depends(get_db),
    cv_file: UploadFile = File(...),
):
    api_key = resolve_openai_api_key(request)
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="No API key available.",
        )
    name = Path(cv_file.filename or "").name
    raw = await cv_file.read()
    try:
        validate_pdf_upload(name, raw)
    except PdfRejected as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    try:
        text = extract_pdf_text(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read that PDF: {exc}",
        ) from exc

    jobs = db.query(Job).order_by(Job.id).all()
    cats = {c.id: c for c in db.query(Category).all()}
    payload = [
        {
            "id": j.id,
            "title": j.title,
            "company_hint": j.company_hint,
            "requirements": j.requirements,
            "category": cats[j.category_id].name,
        }
        for j in jobs
    ]

    try:
        result = run_cv_analysis(api_key, text, payload)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not finish scoring ({exc}).",
        ) from exc

    jobs_by_id = {j.id: j for j in jobs}
    enriched = []
    for row in result.matches:
        jid = row["job_id"]
        job = jobs_by_id.get(jid)
        if not job:
            continue
        cat = cats.get(job.category_id)
        enriched.append(
            {
                "job_id": jid,
                "title": job.title,
                "company": job.company_hint,
                "category": cat.name if cat else "",
                "score": row["score"],
                "summary": row["summary"],
                "ready": row["score"] >= MATCH_THRESHOLD,
            }
        )

    enriched.sort(key=lambda row: row["score"], reverse=True)

    preview = text[:2800] + ("..." if len(text) > 2800 else "")

    record = AnalysisRun(
        filename=name,
        text_length=len(text),
        threshold=MATCH_THRESHOLD,
        profile_json=json.dumps(result.raw_profile, ensure_ascii=False),
        matches_json=json.dumps(enriched, ensure_ascii=False),
        training_json=json.dumps(result.training, ensure_ascii=False),
        extracted_preview=preview,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return JSONResponse(
        {
            "run_id": record.id,
            "threshold": MATCH_THRESHOLD,
            "profile": result.raw_profile,
            "matches": enriched,
            "training": result.training,
            "text_length": len(text),
            "extracted_preview": preview,
        }
    )
