from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)

    jobs: Mapped[list["Job"]] = relationship(back_populates="category")


class Employer(Base):
    __tablename__ = "employers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="employer", foreign_keys="[Job.employer_id]"
    )
    shortlists: Mapped[list["CandidateShortlist"]] = relationship(back_populates="employer")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    company_hint: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    requirements: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    employer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employers.id"), nullable=True)

    category: Mapped["Category"] = relationship(back_populates="jobs")
    employer: Mapped[Optional["Employer"]] = relationship(
        "Employer", back_populates="jobs", foreign_keys="[Job.employer_id]"
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    text_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    profile_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    matches_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    training_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    extracted_preview: Mapped[str] = mapped_column(Text, default="", nullable=False)


class CandidateShortlist(Base):
    __tablename__ = "candidate_shortlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), nullable=False)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False)

    employer: Mapped["Employer"] = relationship(back_populates="shortlists")
    run: Mapped["AnalysisRun"] = relationship()
