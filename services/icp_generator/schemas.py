"""
Pydantic schemas for the ICP Generator service.

Defines structured output schemas for LLM-generated ICPs.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BuyingJourneyStage(str, Enum):
    """Stage in the buying journey."""
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    DECISION = "decision"
    RETENTION = "retention"


class Demographics(BaseModel):
    """Demographic information for an ICP."""
    age_range: str = Field(..., description="Age range (e.g., '25-45')")
    gender: str = Field(default="any", description="Target gender ('male', 'female', 'any')")
    location: list[str] = Field(..., description="Target geographic locations")
    education_level: str | None = Field(default=None, description="Education level")
    income_level: str | None = Field(default=None, description="Income level/bracket")


class ProfessionalProfile(BaseModel):
    """Professional/job-related information for an ICP."""
    job_titles: list[str] = Field(..., description="Common job titles")
    seniority_level: str = Field(..., description="Seniority level (entry, mid, senior, executive)")
    department: str | None = Field(default=None, description="Department/function")
    company_size: str = Field(..., description="Target company size (e.g., '10-50', '50-200', '200-1000', '1000+')")
    industry: list[str] = Field(..., description="Target industries")
    years_experience: str | None = Field(default=None, description="Years of experience range")


class Motivations(BaseModel):
    """Motivations driving the ICP."""
    primary: list[str] = Field(..., description="Primary motivators (3-5)")
    secondary: list[str] = Field(default_factory=list, description="Secondary motivators")
    triggers: list[str] = Field(default_factory=list, description="Events that trigger buying interest")


class GeneratedICP(BaseModel):
    """A single generated Ideal Customer Profile."""
    name: str = Field(..., description="Descriptive name for the ICP (e.g., 'Enterprise Decision Maker')")
    description: str = Field(..., description="2-3 sentence description of this persona")
    demographics: Demographics
    professional_profile: ProfessionalProfile
    pain_points: list[str] = Field(..., min_length=3, max_length=7, description="Key pain points (3-7)")
    goals: list[str] = Field(..., min_length=3, max_length=7, description="Primary goals (3-7)")
    motivations: Motivations
    objections: list[str] = Field(default_factory=list, description="Common buying objections")
    decision_factors: list[str] = Field(..., min_length=3, max_length=7, description="Key decision factors")
    information_sources: list[str] = Field(default_factory=list, description="Where they research solutions")
    buying_journey_stage: BuyingJourneyStage = Field(..., description="Typical entry point in buying journey")

    @field_validator("pain_points", "goals", "decision_factors")
    @classmethod
    def validate_list_length(cls, v, info):
        if len(v) < 3:
            raise ValueError(f"{info.field_name} must have at least 3 items")
        return v


class ICPGenerationResponse(BaseModel):
    """Response schema for ICP generation from LLM."""
    icps: list[GeneratedICP] = Field(..., min_length=5, max_length=5, description="Exactly 5 ICPs")

    @field_validator("icps")
    @classmethod
    def validate_exactly_five(cls, v):
        if len(v) != 5:
            raise ValueError(f"Must have exactly 5 ICPs, got {len(v)}")
        return v

    @field_validator("icps")
    @classmethod
    def validate_unique_names(cls, v):
        names = [icp.name.lower() for icp in v]
        if len(names) != len(set(names)):
            raise ValueError("ICP names must be unique")
        return v


# ==================== API Request/Response Schemas ====================


class ICPGenerateRequest(BaseModel):
    """Request to generate ICPs for a website."""
    force_regenerate: bool = Field(
        default=False,
        description="Force regeneration even if ICPs already exist"
    )
    llm_provider: str | None = Field(
        default=None,
        description="LLM provider to use (openai, anthropic). Uses default if not specified."
    )


class ICPGenerateResponse(BaseModel):
    """Response for ICP generation request."""
    job_id: uuid.UUID
    website_id: uuid.UUID
    status: str = Field(description="queued, running, completed, failed")
    message: str | None = None


class ICPGenerationStatus(BaseModel):
    """Status of an ICP generation job."""
    job_id: uuid.UUID
    website_id: uuid.UUID
    status: str
    progress: float = Field(ge=0.0, le=100.0)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class ICPResponse(BaseModel):
    """Response schema for a single ICP."""
    id: uuid.UUID
    website_id: uuid.UUID
    name: str
    description: str | None
    sequence_number: int
    demographics: dict[str, Any]
    professional_profile: dict[str, Any]
    pain_points: list[str]
    goals: list[str]
    motivations: dict[str, Any]
    objections: list[str] | None
    decision_factors: list[str] | None
    information_sources: list[str] | None
    buying_journey_stage: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ICPListResponse(BaseModel):
    """Response for listing ICPs for a website."""
    website_id: uuid.UUID
    icps: list[ICPResponse]
    total: int


# ==================== Internal Schemas ====================


class WebsiteContext(BaseModel):
    """Context about a website for ICP generation."""
    domain: str
    name: str | None
    description: str | None
    industry: str | None
    business_model: str | None
    primary_offerings: list[dict[str, Any]] | None
    value_propositions: list[str] | None
    target_markets: list[str] | None
    company_profile: dict[str, Any] | None
    products_detailed: list[dict[str, Any]] | None
    services_detailed: list[dict[str, Any]] | None
    target_audience: list[dict[str, Any]] | None
    scraped_content_summary: str | None = None

    def to_prompt_context(self) -> str:
        """Convert to a text context for LLM prompts."""
        parts = []

        if self.name:
            parts.append(f"Company Name: {self.name}")
        parts.append(f"Domain: {self.domain}")

        if self.description:
            parts.append(f"Description: {self.description}")

        if self.industry:
            parts.append(f"Industry: {self.industry}")

        if self.business_model:
            parts.append(f"Business Model: {self.business_model}")

        if self.primary_offerings:
            offerings = [o.get("name", str(o)) for o in self.primary_offerings[:10]]
            parts.append(f"Products/Services: {', '.join(offerings)}")

        if self.value_propositions:
            parts.append(f"Value Propositions: {', '.join(self.value_propositions[:5])}")

        if self.target_markets:
            parts.append(f"Target Markets: {', '.join(self.target_markets[:5])}")

        if self.company_profile:
            cp = self.company_profile
            if cp.get("tagline"):
                parts.append(f"Tagline: {cp['tagline']}")
            if cp.get("founding_year"):
                parts.append(f"Founded: {cp['founding_year']}")

        if self.products_detailed:
            prods = []
            for p in self.products_detailed[:5]:
                name = p.get("name", "")
                desc = p.get("description", "")
                if name:
                    prods.append(f"- {name}: {desc[:100]}..." if len(desc) > 100 else f"- {name}: {desc}")
            if prods:
                parts.append("Detailed Products:\n" + "\n".join(prods))

        if self.services_detailed:
            servs = []
            for s in self.services_detailed[:5]:
                name = s.get("name", "")
                desc = s.get("description", "")
                if name:
                    servs.append(f"- {name}: {desc[:100]}..." if len(desc) > 100 else f"- {name}: {desc}")
            if servs:
                parts.append("Detailed Services:\n" + "\n".join(servs))

        if self.target_audience:
            audiences = [a.get("segment", str(a)) for a in self.target_audience[:5]]
            parts.append(f"Identified Target Audiences: {', '.join(audiences)}")

        if self.scraped_content_summary:
            parts.append(f"Content Summary:\n{self.scraped_content_summary[:2000]}")

        return "\n\n".join(parts)
