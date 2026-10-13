from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.analysis import MATCH_THRESHOLD
from app.auth import hash_password, verify_password
from app.database import get_db
from app.models import AnalysisRun, Category, CandidateShortlist, Employer, Job

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/employer")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _current_employer(request: Request, db: Session) -> Employer | None:
    eid = request.session.get("employer_id")
    if not isinstance(eid, int):
        return None
    return db.query(Employer).filter(Employer.id == eid).first()


def _candidates_for_job(job_id: int, employer_id: int, db: Session) -> list[dict]:
    runs = db.query(AnalysisRun).order_by(AnalysisRun.id.desc()).all()
    shortlisted = {
        s.run_id
        for s in db.query(CandidateShortlist).filter(
            CandidateShortlist.employer_id == employer_id,
            CandidateShortlist.job_id == job_id,
        )
    }
    out: list[dict] = []
    for run in runs:
        try:
            matches = json.loads(run.matches_json or "[]")
        except json.JSONDecodeError:
            continue
        for m in matches:
            if int(m.get("job_id", 0)) == job_id:
                score = int(m.get("score", 0))
                out.append(
                    {
                        "run_id": run.id,
                        "filename": run.filename or "upload.pdf",
                        "when": run.created_at.strftime("%Y-%m-%d %H:%M") if run.created_at else "",
                        "score": score,
                        "summary": m.get("summary", ""),
                        "ready": score >= MATCH_THRESHOLD,
                        "shortlisted": run.id in shortlisted,
                    }
                )
                break
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


@router.get("", response_class=HTMLResponse)
def employer_root(request: Request, db: Session = Depends(get_db)):
    if _current_employer(request, db):
        return RedirectResponse("/employer/dashboard", status_code=303)
    return RedirectResponse("/employer/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def employer_login_page(request: Request, db: Session = Depends(get_db)):
    if _current_employer(request, db):
        return RedirectResponse("/employer/dashboard", status_code=303)
    return TEMPLATES.TemplateResponse("employer_login.html", {"request": request, "error": None})


@router.post("/login")
async def employer_login(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    emp = db.query(Employer).filter(Employer.email == email.strip().lower()).first()
    if not emp or not verify_password(password, emp.password_hash):
        return TEMPLATES.TemplateResponse(
            "employer_login.html",
            {"request": request, "error": "Incorrect email or password."},
            status_code=401,
        )
    request.session["employer_id"] = emp.id
    return RedirectResponse("/employer/dashboard", status_code=303)


@router.get("/register", response_class=HTMLResponse)
def employer_register_page(request: Request, db: Session = Depends(get_db)):
    if _current_employer(request, db):
        return RedirectResponse("/employer/dashboard", status_code=303)
    return TEMPLATES.TemplateResponse(
        "employer_register.html", {"request": request, "error": None}
    )


@router.post("/register")
async def employer_register(
    request: Request,
    company_name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    company_name = company_name.strip()
    email = email.strip().lower()
    password = password.strip()

    if not company_name or not email or not password:
        return TEMPLATES.TemplateResponse(
            "employer_register.html",
            {"request": request, "error": "All fields are required."},
            status_code=400,
        )
    if not _EMAIL_RE.match(email):
        return TEMPLATES.TemplateResponse(
            "employer_register.html",
            {"request": request, "error": "Enter a valid email address."},
            status_code=400,
        )
    if len(password) < 8:
        return TEMPLATES.TemplateResponse(
            "employer_register.html",
            {"request": request, "error": "Password must be at least 8 characters."},
            status_code=400,
        )
    if db.query(Employer).filter(Employer.email == email).first():
        return TEMPLATES.TemplateResponse(
            "employer_register.html",
            {"request": request, "error": "An account with that email already exists."},
            status_code=400,
        )

    emp = Employer(name=company_name, email=email, password_hash=hash_password(password))
    db.add(emp)
    db.commit()
    db.refresh(emp)
    request.session["employer_id"] = emp.id
    return RedirectResponse("/employer/dashboard", status_code=303)


@router.post("/logout")
async def employer_logout(request: Request):
    request.session.pop("employer_id", None)
    return RedirectResponse("/employer/login", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
def employer_dashboard(request: Request, db: Session = Depends(get_db)):
    emp = _current_employer(request, db)
    if not emp:
        return RedirectResponse("/employer/login", status_code=303)

    rows = (
        db.query(Job, Category)
        .join(Category, Job.category_id == Category.id)
        .filter(Job.employer_id == emp.id)
        .order_by(Job.id.desc())
        .all()
    )

    all_runs = db.query(AnalysisRun).all()
    emp_job_ids = {j.id for j, _ in rows}

    qualified_by_job: dict[int, int] = {j.id: 0 for j, _ in rows}
    for run in all_runs:
        try:
            matches = json.loads(run.matches_json or "[]")
        except json.JSONDecodeError:
            continue
        for m in matches:
            jid = int(m.get("job_id", 0))
            if jid in emp_job_ids and int(m.get("score", 0)) >= MATCH_THRESHOLD:
                qualified_by_job[jid] = qualified_by_job.get(jid, 0) + 1

    shortlisted_by_job: dict[int, int] = {}
    for j, _ in rows:
        shortlisted_by_job[j.id] = (
            db.query(CandidateShortlist)
            .filter(
                CandidateShortlist.employer_id == emp.id,
                CandidateShortlist.job_id == j.id,
            )
            .count()
        )

    jobs_view = [
        {
            "id": j.id,
            "title": j.title,
            "category": cat.name,
            "requirements": j.requirements,
            "qualified": qualified_by_job.get(j.id, 0),
            "shortlisted": shortlisted_by_job.get(j.id, 0),
        }
        for j, cat in rows
    ]

    categories = db.query(Category).order_by(Category.name).all()

    return TEMPLATES.TemplateResponse(
        "employer_dashboard.html",
        {
            "request": request,
            "employer": emp,
            "jobs": jobs_view,
            "categories": categories,
            "total_qualified": sum(qualified_by_job.values()),
            "total_shortlisted": sum(shortlisted_by_job.values()),
        },
    )


@router.post("/jobs/new")
async def employer_post_job(
    request: Request,
    title: str = Form(""),
    category_id: int = Form(0),
    requirements: str = Form(""),
    db: Session = Depends(get_db),
):
    emp = _current_employer(request, db)
    if not emp:
        return RedirectResponse("/employer/login", status_code=303)

    title = title.strip()
    requirements = requirements.strip()
    if not title or not requirements or not category_id:
        return RedirectResponse("/employer/dashboard?err=fill_all", status_code=303)

    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        return RedirectResponse("/employer/dashboard?err=bad_cat", status_code=303)

    db.add(
        Job(
            title=title,
            company_hint=emp.name,
            requirements=requirements,
            category_id=category_id,
            employer_id=emp.id,
        )
    )
    db.commit()
    return RedirectResponse("/employer/dashboard", status_code=303)


@router.post("/jobs/{job_id}/delete")
async def employer_delete_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    emp = _current_employer(request, db)
    if not emp:
        return RedirectResponse("/employer/login", status_code=303)

    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == emp.id).first()
    if job:
        db.query(CandidateShortlist).filter(
            CandidateShortlist.employer_id == emp.id,
            CandidateShortlist.job_id == job_id,
        ).delete()
        db.delete(job)
        db.commit()
    return RedirectResponse("/employer/dashboard", status_code=303)


@router.get("/jobs/{job_id}/candidates", response_class=HTMLResponse)
def employer_candidates(job_id: int, request: Request, db: Session = Depends(get_db)):
    emp = _current_employer(request, db)
    if not emp:
        return RedirectResponse("/employer/login", status_code=303)

    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == emp.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    cat = db.query(Category).filter(Category.id == job.category_id).first()
    candidates = _candidates_for_job(job_id, emp.id, db)

    return TEMPLATES.TemplateResponse(
        "employer_candidates.html",
        {
            "request": request,
            "employer": emp,
            "job": job,
            "category": cat,
            "candidates": candidates,
            "threshold": MATCH_THRESHOLD,
        },
    )


@router.post("/jobs/{job_id}/candidates/{run_id}/shortlist")
async def toggle_shortlist(
    job_id: int,
    run_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    emp = _current_employer(request, db)
    if not emp:
        raise HTTPException(status_code=401, detail="Not logged in.")

    if not db.query(Job).filter(Job.id == job_id, Job.employer_id == emp.id).first():
        raise HTTPException(status_code=404, detail="Job not found.")

    if not db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first():
        raise HTTPException(status_code=404, detail="Run not found.")

    existing = (
        db.query(CandidateShortlist)
        .filter(
            CandidateShortlist.employer_id == emp.id,
            CandidateShortlist.run_id == run_id,
            CandidateShortlist.job_id == job_id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        return JSONResponse({"shortlisted": False})

    db.add(CandidateShortlist(employer_id=emp.id, run_id=run_id, job_id=job_id))
    db.commit()
    return JSONResponse({"shortlisted": True})
