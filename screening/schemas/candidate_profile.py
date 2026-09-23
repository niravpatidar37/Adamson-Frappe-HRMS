"""Pydantic schema for the 23-field candidate profile produced by
`sukhrobnurali/qwen3vl-resume-parser` (system-design.md section 7.5).

Fields map to predefined option lists where noted; unmapped/ambiguous
values must fall back to "Other" rather than being fabricated.
"""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class WorkMode(StrEnum):
    ON_SITE = "on_site"
    REMOTE = "remote"
    HYBRID = "hybrid"
    OTHER = "Other"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    OTHER = "Other"


class EmploymentDuration(StrEnum):
    PERMANENT = "permanent"
    TEMPORARY = "temporary"
    SEASONAL = "seasonal"
    OTHER = "Other"


class Address(BaseModel):
    country_name: str | None = None
    region_name: str | None = None


class Skill(BaseModel):
    name: str
    level: str | None = None


class Experience(BaseModel):
    company: str | None = None
    title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class Education(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class Language(BaseModel):
    name: str
    proficiency: str | None = None


class Certificate(BaseModel):
    name: str
    issuer: str | None = None
    issue_date: date | None = None


class Project(BaseModel):
    name: str
    description: str | None = None


class CandidateProfile(BaseModel):
    """The fixed 23-field schema returned by the resume parser model.

    All enum-mapped fields are model predictions, not verified facts
    (system-design.md 11.7), and must be treated as such downstream.
    """

    # Identity & contact (5)
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None

    # Position & preferences (6)
    desired_position: str | None = None
    about: str | None = None
    job_experience: str | None = None
    job_expectations: str | None = None
    min_salary: float | None = None
    max_salary: float | None = None
    ready_to_relocation: bool | None = None

    # Work mode enums (3)
    work_modes: list[WorkMode] = Field(default_factory=list)
    employment_types: list[EmploymentType] = Field(default_factory=list)
    employment_durations: list[EmploymentDuration] = Field(default_factory=list)

    # Personal (1)
    hobbies: list[str] = Field(default_factory=list)

    # Address (1 object)
    address: Address = Field(default_factory=Address)

    # Structured arrays (6)
    skills: list[Skill] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    educations: list[Education] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    certificates: list[Certificate] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
