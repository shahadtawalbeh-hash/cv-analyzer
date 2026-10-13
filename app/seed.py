from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import Category, Employer, Job


def seed_if_empty(db: Session) -> None:
    if not db.query(Category).first():
        cats = [
            ("Engineering", "engineering"),
            ("Data & Analytics", "data"),
            ("Design & Product", "design"),
            ("Operations", "operations"),
        ]
        mapping: dict[str, Category] = {}
        for name, slug in cats:
            c = Category(name=name, slug=slug)
            db.add(c)
            db.flush()
            mapping[slug] = c

        jobs_spec = [
            (
                "engineering",
                "Backend Engineer",
                "Internal stack",
                "Python or Node. REST APIs, SQL, authentication, logging. Comfort with Git and code review.",
            ),
            (
                "engineering",
                "Frontend Engineer",
                "Partner studio",
                "TypeScript, React, semantic HTML and accessible components. Experience with performance basics.",
            ),
            (
                "data",
                "Junior Data Analyst",
                "Retail partner",
                "SQL, spreadsheets, basics of statistics. Dashboards and clear written summaries for stakeholders.",
            ),
            (
                "data",
                "Machine Learning Assistant",
                "R&D lab",
                "Python, notebooks, clean data prep. Familiarity with scikit-learn or similar libraries.",
            ),
            (
                "design",
                "UX Designer",
                "Consulting team",
                "Figma workflows, usability testing, information architecture. Portfolio with case studies.",
            ),
            (
                "operations",
                "IT Support Specialist",
                "City campus",
                "Windows and Office troubleshooting, ticketing systems, calm communication under load.",
            ),
        ]

        for slug, title, company, req in jobs_spec:
            db.add(
                Job(
                    title=title,
                    company_hint=company,
                    requirements=req,
                    category_id=mapping[slug].id,
                )
            )

        db.commit()

    if not db.query(Employer).first():
        db.add(
            Employer(
                name="Demo Company",
                email="employer@demo.com",
                password_hash=hash_password("employer123"),
            )
        )
        db.commit()
