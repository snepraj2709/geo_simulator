"""
Minimal FastAPI application - no auth, synchronous, fake LLM responses.
Run with: uvicorn main:app --reload
"""

import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.db.postgres import AsyncSessionLocal, Base, engine
from shared.models import (
    Brand,
    ConversationSequence,
    ICP,
    LLMBrandState,
    LLMResponse,
    Organization,
    Prompt,
    PromptClassification,
    SimulationRun,
    Website,
)
from shared.models.enums import (
    BeliefType,
    BrandPresence,
    FunnelStage,
    IntentType,
    LLMProviderEnum,
    PromptType,
    QueryIntent,
    SimulationStatus,
    WebsiteStatus,
)

from services.api.llm_simulator import simulate_response, LLMSimulator

# Default organization ID for minimal API (no auth)
DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# --- Pydantic Schemas ---

class WebsiteCreate(BaseModel):
    url: HttpUrl
    name: str | None = Field(default=None, max_length=255)


class WebsiteResponse(BaseModel):
    id: uuid.UUID
    domain: str
    url: str
    name: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class WebsiteListResponse(BaseModel):
    websites: list[WebsiteResponse]
    total: int


class BootstrapResponse(BaseModel):
    website_id: uuid.UUID
    icps_created: int
    conversations_created: int
    prompts_created: int
    message: str


class SimulationResponse(BaseModel):
    simulation_run_id: uuid.UUID
    website_id: uuid.UUID
    total_prompts: int
    responses_generated: int
    providers: list[str]
    status: str


class BrandSummary(BaseModel):
    brand_name: str
    mention_count: int
    recommendation_count: int
    avg_position: float | None


class SummaryResponse(BaseModel):
    website_id: uuid.UUID
    total_simulations: int
    total_responses: int
    total_mentions: int
    total_recommendations: int
    top_competitors: list[BrandSummary]
    by_provider: dict[str, dict[str, int]]


# --- Fake Data Generators (deterministic with seeded random) ---

ICP_TEMPLATES = [
    {
        "name": "Enterprise Decision Maker",
        "description": "C-level executives at large enterprises seeking strategic solutions",
        "demographics": {"age_range": "40-55", "location": "US/EU", "income_level": "high"},
        "professional_profile": {"job_titles": ["CEO", "CTO", "VP Engineering"], "company_size": "500+", "seniority": "executive"},
        "pain_points": ["Scaling operations", "Digital transformation", "Talent retention"],
        "goals": ["Increase revenue", "Improve efficiency", "Stay competitive"],
        "motivations": {"primary": "Growth", "secondary": "Innovation"},
    },
    {
        "name": "Tech-Savvy Startup Founder",
        "description": "Startup founders looking for modern, scalable solutions",
        "demographics": {"age_range": "25-40", "location": "Global", "income_level": "variable"},
        "professional_profile": {"job_titles": ["Founder", "CEO", "Technical Co-founder"], "company_size": "1-50", "seniority": "founder"},
        "pain_points": ["Limited budget", "Time constraints", "Finding product-market fit"],
        "goals": ["Launch MVP", "Acquire customers", "Raise funding"],
        "motivations": {"primary": "Innovation", "secondary": "Impact"},
    },
    {
        "name": "IT Manager",
        "description": "IT managers responsible for technology decisions in mid-size companies",
        "demographics": {"age_range": "30-50", "location": "US/EU", "income_level": "middle-upper"},
        "professional_profile": {"job_titles": ["IT Manager", "IT Director", "Systems Admin"], "company_size": "50-500", "seniority": "mid-senior"},
        "pain_points": ["Legacy system maintenance", "Security concerns", "Vendor management"],
        "goals": ["Reduce downtime", "Improve security", "Streamline operations"],
        "motivations": {"primary": "Reliability", "secondary": "Efficiency"},
    },
    {
        "name": "Marketing Professional",
        "description": "Marketing professionals seeking tools to improve campaign performance",
        "demographics": {"age_range": "25-45", "location": "Global", "income_level": "middle"},
        "professional_profile": {"job_titles": ["Marketing Manager", "Growth Lead", "CMO"], "company_size": "10-500", "seniority": "mid-senior"},
        "pain_points": ["Attribution tracking", "Budget optimization", "Content creation at scale"],
        "goals": ["Increase ROI", "Build brand awareness", "Generate leads"],
        "motivations": {"primary": "Results", "secondary": "Creativity"},
    },
    {
        "name": "Small Business Owner",
        "description": "Small business owners looking for affordable, easy-to-use solutions",
        "demographics": {"age_range": "30-60", "location": "Local/Regional", "income_level": "middle"},
        "professional_profile": {"job_titles": ["Owner", "Founder", "General Manager"], "company_size": "1-20", "seniority": "owner"},
        "pain_points": ["Limited resources", "Wearing many hats", "Competition with larger players"],
        "goals": ["Grow revenue", "Save time", "Improve customer experience"],
        "motivations": {"primary": "Independence", "secondary": "Growth"},
    },
]

CONVERSATION_TOPICS = [
    "Best solutions for {industry}",
    "How to choose a {product_type} provider",
    "Comparing {product_type} alternatives",
    "What is the best {product_type} for {use_case}",
    "Reviews of {product_type} tools",
    "{product_type} pricing comparison",
    "Enterprise vs SMB {product_type} solutions",
    "Free {product_type} alternatives",
    "How to implement {product_type}",
    "ROI of using {product_type}",
]

PROMPT_TEMPLATES = [
    "What are the best {topic}?",
    "Can you recommend a good {topic}?",
    "I'm looking for {topic}, what should I consider?",
    "Compare the top options for {topic}",
    "What do experts say about {topic}?",
]

def classify_prompt(seed: int, prompt_text: str) -> dict[str, Any]:
    """Generate deterministic prompt classification."""
    rng = random.Random(seed)

    intent_types = list(IntentType)
    funnel_stages = list(FunnelStage)
    query_intents = list(QueryIntent)

    return {
        "intent_type": rng.choice(intent_types).value,
        "funnel_stage": rng.choice(funnel_stages).value,
        "buying_signal": round(rng.uniform(0.2, 0.9), 2),
        "trust_need": round(rng.uniform(0.3, 0.95), 2),
        "query_intent": rng.choice(query_intents).value,
        "confidence_score": round(rng.uniform(0.7, 0.98), 2),
    }


# --- Application Lifespan ---

async def ensure_default_organization(db: AsyncSession) -> None:
    """Ensure a default organization exists for the minimal API."""
    result = await db.execute(select(Organization).where(Organization.id == DEFAULT_ORG_ID))
    if result.scalar_one_or_none() is None:
        org = Organization(
            id=DEFAULT_ORG_ID,
            name="Default Organization",
            slug="default",
            plan_type="free",
        )
        db.add(org)
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default organization
    async with AsyncSessionLocal() as session:
        await ensure_default_organization(session)

    yield
    # Cleanup
    await engine.dispose()


# --- FastAPI App ---

app = FastAPI(
    title="GEO Simulator API",
    description="Minimal API for LLM Brand Influence simulation",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Dependency ---

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Type alias for cleaner dependency injection
DBSession = AsyncSession


# --- Helper Functions ---

async def get_or_create_brand(db: AsyncSession, name: str, domain: str | None = None, is_tracked: bool = False) -> Brand:
    """Get existing brand or create new one."""
    normalized = name.lower().strip()
    result = await db.execute(select(Brand).where(Brand.normalized_name == normalized))
    brand = result.scalar_one_or_none()

    if brand is None:
        brand = Brand(
            name=name,
            normalized_name=normalized,
            domain=domain,
            is_tracked=is_tracked,
        )
        db.add(brand)
        await db.flush()

    return brand


# --- Endpoints ---

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/websites", response_model=WebsiteResponse, status_code=status.HTTP_201_CREATED)
async def create_website(
    request: WebsiteCreate,
    db: DBSession = Depends(get_db_session),
):
    """Create a new website for tracking."""
    parsed = urlparse(str(request.url))
    domain = parsed.netloc.lower()

    # Check if domain already exists
    result = await db.execute(select(Website).where(Website.domain == domain))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Website with domain '{domain}' already exists",
        )

    # Create website with default organization
    website = Website(
        organization_id=DEFAULT_ORG_ID,
        domain=domain,
        url=str(request.url),
        name=request.name or domain,
        status=WebsiteStatus.PENDING.value,
    )
    db.add(website)
    await db.flush()
    await db.refresh(website)

    return WebsiteResponse.model_validate(website)


@app.get("/websites", response_model=WebsiteListResponse)
async def list_websites(
    db: DBSession = Depends(get_db_session),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List all tracked websites."""
    offset = (page - 1) * limit

    # Get total count
    total_result = await db.execute(select(func.count()).select_from(Website))
    total = total_result.scalar() or 0

    # Get websites
    result = await db.execute(
        select(Website)
        .offset(offset)
        .limit(limit)
        .order_by(Website.created_at.desc())
    )
    websites = result.scalars().all()

    return WebsiteListResponse(
        websites=[WebsiteResponse.model_validate(w) for w in websites],
        total=total,
    )


@app.post("/websites/{website_id}/bootstrap", response_model=BootstrapResponse)
async def bootstrap_website(
    website_id: uuid.UUID,
    db: DBSession = Depends(get_db_session),
):
    """
    Bootstrap a website with fake data:
    - Fake scrape
    - Generate 5 ICPs
    - Generate 10 conversations per ICP
    - Classify all prompts
    """
    # Get website
    result = await db.execute(select(Website).where(Website.id == website_id))
    website = result.scalar_one_or_none()

    if website is None:
        raise HTTPException(status_code=404, detail="Website not found")

    # Use domain as seed for deterministic generation
    seed_base = hash(website.domain)
    rng = random.Random(seed_base)

    # Update website status to "completed" (fake scrape done)
    website.status = WebsiteStatus.COMPLETED.value
    website.last_scraped_at = datetime.now(timezone.utc)

    # Determine industry/product type from domain
    industry = rng.choice(["SaaS", "E-commerce", "FinTech", "HealthTech", "EdTech"])
    product_type = rng.choice(["software", "platform", "service", "tool", "solution"])
    use_case = rng.choice(["teams", "businesses", "enterprises", "startups", "developers"])

    # Create 5 ICPs
    icps_created = 0
    conversations_created = 0
    prompts_created = 0

    for i, icp_template in enumerate(ICP_TEMPLATES):
        icp = ICP(
            website_id=website.id,
            name=icp_template["name"],
            description=icp_template["description"],
            sequence_number=i + 1,
            demographics=icp_template["demographics"],
            professional_profile=icp_template["professional_profile"],
            pain_points=icp_template["pain_points"],
            goals=icp_template["goals"],
            motivations=icp_template["motivations"],
        )
        db.add(icp)
        await db.flush()
        icps_created += 1

        # Create 10 conversations per ICP
        for j, topic_template in enumerate(CONVERSATION_TOPICS):
            topic = topic_template.format(
                industry=industry,
                product_type=product_type,
                use_case=use_case,
            )

            conversation = ConversationSequence(
                website_id=website.id,
                icp_id=icp.id,
                topic=topic,
                context=f"User is a {icp_template['name']} looking for {product_type}",
                expected_outcome=f"Understanding of {product_type} options",
                is_core_conversation=(j < 5),
                sequence_number=j + 1,
            )
            db.add(conversation)
            await db.flush()
            conversations_created += 1

            # Create prompts for each conversation (1-3 prompts)
            num_prompts = rng.randint(1, 3)
            for k in range(num_prompts):
                prompt_template = rng.choice(PROMPT_TEMPLATES)
                prompt_text = prompt_template.format(topic=topic)

                prompt = Prompt(
                    conversation_id=conversation.id,
                    prompt_text=prompt_text,
                    prompt_type=PromptType.PRIMARY.value if k == 0 else PromptType.FOLLOW_UP.value,
                    sequence_order=k + 1,
                )
                db.add(prompt)
                await db.flush()
                prompts_created += 1

                # Create classification
                classification_data = classify_prompt(seed_base + hash(prompt_text), prompt_text)
                classification = PromptClassification(
                    prompt_id=prompt.id,
                    intent_type=classification_data["intent_type"],
                    funnel_stage=classification_data["funnel_stage"],
                    buying_signal=Decimal(str(classification_data["buying_signal"])),
                    trust_need=Decimal(str(classification_data["trust_need"])),
                    query_intent=classification_data["query_intent"],
                    confidence_score=Decimal(str(classification_data["confidence_score"])),
                    classifier_version="fake-v1.0",
                )
                db.add(classification)

    return BootstrapResponse(
        website_id=website.id,
        icps_created=icps_created,
        conversations_created=conversations_created,
        prompts_created=prompts_created,
        message="Website bootstrapped successfully with fake data",
    )


@app.post("/websites/{website_id}/simulate", response_model=SimulationResponse)
async def simulate_website(
    website_id: uuid.UUID,
    db: DBSession = Depends(get_db_session),
):
    """
    Run a simulation for a website:
    - Creates a simulation_run
    - Generates fake LLM responses for OpenAI, Google, Anthropic
    - Uses llm_simulator for deterministic, keyword-based responses
    - Populates brand states with realistic belief + presence data
    """
    # Get website
    result = await db.execute(select(Website).where(Website.id == website_id))
    website = result.scalar_one_or_none()

    if website is None:
        raise HTTPException(status_code=404, detail="Website not found")

    # Get all prompts with their classifications for this website
    prompt_query = (
        select(Prompt)
        .options(selectinload(Prompt.classification))
        .join(ConversationSequence)
        .where(ConversationSequence.website_id == website_id)
    )
    result = await db.execute(prompt_query)
    prompts = result.scalars().all()

    if not prompts:
        raise HTTPException(
            status_code=400,
            detail="No prompts found. Run /bootstrap first.",
        )

    # Create simulation run
    simulation_run = SimulationRun(
        website_id=website.id,
        status=SimulationStatus.RUNNING.value,
        total_prompts=len(prompts),
        started_at=datetime.now(timezone.utc),
    )
    db.add(simulation_run)
    await db.flush()

    # Get tracked brand info
    brand_name = website.name or website.domain

    # Get or create the tracked brand
    tracked_brand = await get_or_create_brand(db, brand_name, website.domain, is_tracked=True)

    # Initialize the LLM simulator with tracked brand context
    simulator = LLMSimulator(tracked_brand=brand_name, tracked_domain=website.domain)

    # LLM providers and models
    providers = [
        (LLMProviderEnum.OPENAI.value, "gpt-4"),
        (LLMProviderEnum.GOOGLE.value, "gemini-pro"),
        (LLMProviderEnum.ANTHROPIC.value, "claude-3-opus"),
    ]

    responses_generated = 0

    for prompt in prompts:
        # Get classification data if available
        classification_data = None
        if prompt.classification:
            classification_data = {
                "intent_type": prompt.classification.intent_type,
                "funnel_stage": prompt.classification.funnel_stage,
                "buying_signal": float(prompt.classification.buying_signal),
                "trust_need": float(prompt.classification.trust_need),
            }

        for provider, model in providers:
            # Generate response using the new simulator
            sim_response = simulator.simulate_response(
                prompt=prompt.prompt_text,
                provider=provider,
                classification=classification_data,
            )

            llm_response = LLMResponse(
                simulation_run_id=simulation_run.id,
                prompt_id=prompt.id,
                llm_provider=provider,
                llm_model=model,
                response_text=sim_response.response_text,
                response_tokens=sim_response.response_tokens,
                latency_ms=sim_response.latency_ms,
                brands_mentioned=sim_response.brands_mentioned,
            )
            db.add(llm_response)
            await db.flush()
            responses_generated += 1

            # Create brand states from the simulator's detailed brand info
            for brand_detail in sim_response.brand_details:
                # Skip ignored brands (they won't be in brands_mentioned anyway)
                if brand_detail.presence == BrandPresence.IGNORED:
                    continue

                brand = await get_or_create_brand(
                    db,
                    brand_detail.name,
                    is_tracked=(brand_detail.name.lower() == brand_name.lower()),
                )

                brand_state = LLMBrandState(
                    llm_response_id=llm_response.id,
                    brand_id=brand.id,
                    presence=brand_detail.presence.value,
                    position_rank=brand_detail.position,
                    belief_sold=brand_detail.belief_sold.value if brand_detail.belief_sold else None,
                )
                db.add(brand_state)

    # Update simulation run
    simulation_run.status = SimulationStatus.COMPLETED.value
    simulation_run.completed_prompts = len(prompts)
    simulation_run.completed_at = datetime.now(timezone.utc)

    return SimulationResponse(
        simulation_run_id=simulation_run.id,
        website_id=website.id,
        total_prompts=len(prompts),
        responses_generated=responses_generated,
        providers=[p[0] for p in providers],
        status=SimulationStatus.COMPLETED.value,
    )


@app.get("/websites/{website_id}/summary", response_model=SummaryResponse)
async def get_website_summary(
    website_id: uuid.UUID,
    db: DBSession = Depends(get_db_session),
):
    """
    Get aggregated summary for a website:
    - Total mentions
    - Total recommendations
    - Top competitors
    - Breakdown by provider
    """
    # Get website
    result = await db.execute(select(Website).where(Website.id == website_id))
    website = result.scalar_one_or_none()

    if website is None:
        raise HTTPException(status_code=404, detail="Website not found")

    # Get simulation count
    sim_count_result = await db.execute(
        select(func.count())
        .select_from(SimulationRun)
        .where(SimulationRun.website_id == website_id)
    )
    total_simulations = sim_count_result.scalar() or 0

    # Get total responses
    response_query = (
        select(func.count())
        .select_from(LLMResponse)
        .join(SimulationRun)
        .where(SimulationRun.website_id == website_id)
    )
    response_count_result = await db.execute(response_query)
    total_responses = response_count_result.scalar() or 0

    if total_responses == 0:
        return SummaryResponse(
            website_id=website_id,
            total_simulations=total_simulations,
            total_responses=0,
            total_mentions=0,
            total_recommendations=0,
            top_competitors=[],
            by_provider={},
        )

    # Get brand statistics
    brand_stats_query = (
        select(
            Brand.name,
            func.count(LLMBrandState.id).label("mention_count"),
            func.sum(
                func.cast(LLMBrandState.presence == BrandPresence.RECOMMENDED.value, Integer)
            ).label("recommendation_count"),
            func.avg(LLMBrandState.position_rank).label("avg_position"),
        )
        .join(LLMBrandState, Brand.id == LLMBrandState.brand_id)
        .join(LLMResponse, LLMBrandState.llm_response_id == LLMResponse.id)
        .join(SimulationRun, LLMResponse.simulation_run_id == SimulationRun.id)
        .where(SimulationRun.website_id == website_id)
        .group_by(Brand.id, Brand.name)
        .order_by(func.count(LLMBrandState.id).desc())
        .limit(10)
    )

    brand_stats_result = await db.execute(brand_stats_query)
    brand_stats = brand_stats_result.all()

    # Calculate totals
    total_mentions = sum(row.mention_count for row in brand_stats)
    total_recommendations = sum(row.recommendation_count or 0 for row in brand_stats)

    top_competitors = [
        BrandSummary(
            brand_name=row.name,
            mention_count=row.mention_count,
            recommendation_count=row.recommendation_count or 0,
            avg_position=round(float(row.avg_position), 2) if row.avg_position else None,
        )
        for row in brand_stats
    ]

    # Get stats by provider
    provider_stats_query = (
        select(
            LLMResponse.llm_provider,
            func.count(LLMBrandState.id).label("mentions"),
            func.sum(
                func.cast(LLMBrandState.presence == BrandPresence.RECOMMENDED.value, Integer)
            ).label("recommendations"),
        )
        .join(LLMBrandState, LLMResponse.id == LLMBrandState.llm_response_id)
        .join(SimulationRun, LLMResponse.simulation_run_id == SimulationRun.id)
        .where(SimulationRun.website_id == website_id)
        .group_by(LLMResponse.llm_provider)
    )

    provider_stats_result = await db.execute(provider_stats_query)
    provider_stats = provider_stats_result.all()

    by_provider = {
        row.llm_provider: {
            "mentions": row.mentions,
            "recommendations": row.recommendations or 0,
        }
        for row in provider_stats
    }

    return SummaryResponse(
        website_id=website_id,
        total_simulations=total_simulations,
        total_responses=total_responses,
        total_mentions=total_mentions,
        total_recommendations=total_recommendations,
        top_competitors=top_competitors,
        by_provider=by_provider,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
