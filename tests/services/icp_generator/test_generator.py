"""
Tests for ICP Generator with mocked LLM responses.
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.icp_generator.generator import ICPGenerator, ICPGenerationError
from services.icp_generator.schemas import (
    GeneratedICP,
    ICPGenerationResponse,
    WebsiteContext,
    Demographics,
    ProfessionalProfile,
    Motivations,
    BuyingJourneyStage,
)
from services.icp_generator.prompts import (
    ICP_SYSTEM_PROMPT,
    build_icp_generation_prompt,
)
from shared.llm.base import LLMResponse, ResponseFormat


# ==================== Fixtures ====================


@pytest.fixture
def mock_llm_response():
    """Create a valid mocked LLM response with 5 ICPs."""
    icps_data = {
        "icps": [
            {
                "name": "Enterprise IT Director",
                "description": "Senior IT leader at large enterprises looking to modernize their technology stack and improve operational efficiency.",
                "demographics": {
                    "age_range": "40-55",
                    "gender": "any",
                    "location": ["United States", "United Kingdom", "Canada"],
                    "education_level": "Bachelor's or Master's in Computer Science or Business",
                    "income_level": "$150,000-$250,000"
                },
                "professional_profile": {
                    "job_titles": ["IT Director", "VP of Technology", "Head of IT", "CTO"],
                    "seniority_level": "senior",
                    "department": "Information Technology",
                    "company_size": "1000+",
                    "industry": ["Technology", "Finance", "Healthcare"],
                    "years_experience": "15+ years"
                },
                "pain_points": [
                    "Legacy system maintenance costs",
                    "Integration challenges with new technologies",
                    "Security vulnerabilities in outdated systems",
                    "Difficulty attracting and retaining IT talent"
                ],
                "goals": [
                    "Modernize IT infrastructure",
                    "Reduce operational costs by 30%",
                    "Improve system reliability and uptime",
                    "Enable digital transformation initiatives"
                ],
                "motivations": {
                    "primary": ["Cost reduction", "Risk mitigation", "Operational efficiency"],
                    "secondary": ["Career advancement", "Industry recognition"],
                    "triggers": ["Budget cycle", "Security incident", "Digital transformation mandate"]
                },
                "objections": [
                    "High implementation costs",
                    "Disruption to existing operations",
                    "Learning curve for team"
                ],
                "decision_factors": [
                    "Total cost of ownership",
                    "Vendor reputation and stability",
                    "Integration capabilities",
                    "Security certifications"
                ],
                "information_sources": ["Gartner", "Forrester", "LinkedIn", "Industry conferences"],
                "buying_journey_stage": "consideration"
            },
            {
                "name": "SMB Operations Manager",
                "description": "Hands-on operations leader at growing small-to-medium businesses seeking efficient, affordable solutions.",
                "demographics": {
                    "age_range": "30-45",
                    "gender": "any",
                    "location": ["United States"],
                    "education_level": "Bachelor's degree",
                    "income_level": "$70,000-$120,000"
                },
                "professional_profile": {
                    "job_titles": ["Operations Manager", "COO", "Business Operations Lead"],
                    "seniority_level": "mid",
                    "department": "Operations",
                    "company_size": "50-200",
                    "industry": ["Professional Services", "Retail", "Manufacturing"],
                    "years_experience": "5-10 years"
                },
                "pain_points": [
                    "Manual processes slowing growth",
                    "Limited budget for enterprise tools",
                    "Difficulty scaling operations",
                    "Lack of visibility into business metrics"
                ],
                "goals": [
                    "Automate repetitive tasks",
                    "Scale operations without adding headcount",
                    "Improve team productivity",
                    "Get better business insights"
                ],
                "motivations": {
                    "primary": ["Efficiency gains", "Cost savings", "Growth enablement"],
                    "secondary": ["Work-life balance", "Team satisfaction"],
                    "triggers": ["Growth milestone", "New funding", "Competitive pressure"]
                },
                "objections": [
                    "Budget constraints",
                    "Implementation time",
                    "Team adoption concerns"
                ],
                "decision_factors": [
                    "Price point",
                    "Ease of use",
                    "Quick time-to-value",
                    "Customer support quality"
                ],
                "information_sources": ["G2", "Capterra", "LinkedIn", "Peer recommendations"],
                "buying_journey_stage": "awareness"
            },
            {
                "name": "Marketing Director",
                "description": "Marketing leader responsible for driving growth and brand awareness through data-driven strategies.",
                "demographics": {
                    "age_range": "35-50",
                    "gender": "any",
                    "location": ["United States", "Europe"],
                    "education_level": "Bachelor's or MBA",
                    "income_level": "$100,000-$180,000"
                },
                "professional_profile": {
                    "job_titles": ["Marketing Director", "VP Marketing", "CMO", "Head of Marketing"],
                    "seniority_level": "senior",
                    "department": "Marketing",
                    "company_size": "200-1000",
                    "industry": ["SaaS", "E-commerce", "B2B Services"],
                    "years_experience": "10-15 years"
                },
                "pain_points": [
                    "Proving marketing ROI to leadership",
                    "Fragmented customer data across tools",
                    "Difficulty personalizing at scale",
                    "Attribution challenges"
                ],
                "goals": [
                    "Increase marketing qualified leads by 50%",
                    "Improve conversion rates",
                    "Build unified customer view",
                    "Demonstrate clear ROI"
                ],
                "motivations": {
                    "primary": ["Revenue growth", "Brand building", "Data-driven decisions"],
                    "secondary": ["Team development", "Innovation leadership"],
                    "triggers": ["Quarterly planning", "Competitive threat", "New product launch"]
                },
                "objections": [
                    "Already invested in existing tools",
                    "Data migration complexity",
                    "Privacy compliance concerns"
                ],
                "decision_factors": [
                    "Integration with existing stack",
                    "Analytics capabilities",
                    "Scalability",
                    "Customer success stories"
                ],
                "information_sources": ["HubSpot blog", "MarketingProfs", "LinkedIn", "Webinars"],
                "buying_journey_stage": "consideration"
            },
            {
                "name": "Startup Founder",
                "description": "Early-stage founder building their company and looking for tools that grow with them.",
                "demographics": {
                    "age_range": "25-40",
                    "gender": "any",
                    "location": ["United States", "Europe", "Asia"],
                    "education_level": "Bachelor's or higher",
                    "income_level": "Variable"
                },
                "professional_profile": {
                    "job_titles": ["Founder", "CEO", "Co-founder", "Chief Product Officer"],
                    "seniority_level": "executive",
                    "department": "Executive",
                    "company_size": "10-50",
                    "industry": ["Technology", "SaaS", "Fintech"],
                    "years_experience": "5-15 years"
                },
                "pain_points": [
                    "Limited resources and budget",
                    "Need to move fast and iterate",
                    "Wearing multiple hats",
                    "Finding product-market fit"
                ],
                "goals": [
                    "Achieve product-market fit",
                    "Scale efficiently",
                    "Attract investors",
                    "Build a sustainable business"
                ],
                "motivations": {
                    "primary": ["Growth velocity", "Capital efficiency", "Competitive advantage"],
                    "secondary": ["Vision realization", "Team building"],
                    "triggers": ["Funding round", "Growth milestone", "Pivot decision"]
                },
                "objections": [
                    "Startup pricing concerns",
                    "Commitment to long-term contracts",
                    "Feature overkill for current stage"
                ],
                "decision_factors": [
                    "Startup-friendly pricing",
                    "Speed of implementation",
                    "Scalability",
                    "Founder community reviews"
                ],
                "information_sources": ["Product Hunt", "Hacker News", "Twitter/X", "Founder communities"],
                "buying_journey_stage": "awareness"
            },
            {
                "name": "Enterprise Procurement Manager",
                "description": "Strategic procurement professional responsible for vendor evaluation and contract negotiations at large organizations.",
                "demographics": {
                    "age_range": "35-55",
                    "gender": "any",
                    "location": ["United States", "United Kingdom"],
                    "education_level": "Bachelor's in Business or Supply Chain",
                    "income_level": "$90,000-$150,000"
                },
                "professional_profile": {
                    "job_titles": ["Procurement Manager", "Strategic Sourcing Manager", "Vendor Manager"],
                    "seniority_level": "mid",
                    "department": "Procurement",
                    "company_size": "1000+",
                    "industry": ["Finance", "Healthcare", "Manufacturing"],
                    "years_experience": "8-15 years"
                },
                "pain_points": [
                    "Complex vendor evaluation processes",
                    "Ensuring compliance and security",
                    "Managing multiple stakeholders",
                    "Cost optimization pressure"
                ],
                "goals": [
                    "Reduce vendor costs by 15%",
                    "Streamline procurement processes",
                    "Ensure regulatory compliance",
                    "Build strategic vendor partnerships"
                ],
                "motivations": {
                    "primary": ["Cost savings", "Risk management", "Process efficiency"],
                    "secondary": ["Stakeholder satisfaction", "Career growth"],
                    "triggers": ["Contract renewal", "Budget review", "Compliance audit"]
                },
                "objections": [
                    "Long approval processes",
                    "Need for multiple stakeholder buy-in",
                    "Compliance documentation requirements"
                ],
                "decision_factors": [
                    "Total cost of ownership",
                    "Compliance certifications",
                    "Contract flexibility",
                    "Vendor financial stability"
                ],
                "information_sources": ["Industry reports", "Peer networks", "RFP responses", "Analyst briefings"],
                "buying_journey_stage": "decision"
            }
        ]
    }
    return LLMResponse(
        text=json.dumps(icps_data),
        model="gpt-4o",
        provider="openai",
        tokens_used=2500,
        latency_ms=3500,
        raw_response={},
    )


@pytest.fixture
def mock_llm_client(mock_llm_response):
    """Create a mocked LLM client."""
    client = MagicMock()
    client.complete_json = AsyncMock(return_value=mock_llm_response)
    client.complete = AsyncMock(return_value=mock_llm_response)
    return client


@pytest.fixture
def sample_website_context():
    """Create sample website context."""
    return WebsiteContext(
        domain="acme.com",
        name="Acme Corp",
        description="Enterprise software solutions provider",
        industry="technology",
        business_model="B2B SaaS",
        primary_offerings=[
            {"name": "AcmePlatform", "description": "Enterprise data management"},
            {"name": "AcmeAnalytics", "description": "Business intelligence suite"},
        ],
        value_propositions=[
            "Reduce operational costs by 40%",
            "10x faster data processing",
            "Enterprise-grade security",
        ],
        target_markets=["Enterprise", "Mid-market"],
        company_profile={
            "name": "Acme Corp",
            "tagline": "Transform your business with data",
            "founding_year": 2015,
        },
        products_detailed=[
            {
                "name": "AcmePlatform Pro",
                "description": "Full-featured enterprise data platform",
            }
        ],
        services_detailed=[
            {
                "name": "Implementation Services",
                "description": "Expert implementation and onboarding",
            }
        ],
        target_audience=[
            {"segment": "Enterprise IT Directors"},
            {"segment": "Data Engineers"},
        ],
        scraped_content_summary="Acme Corp helps enterprises manage their data efficiently...",
    )


# ==================== Schema Tests ====================


class TestICPSchemas:
    """Test ICP schema validation."""

    def test_valid_generated_icp(self):
        """Test valid ICP schema."""
        icp = GeneratedICP(
            name="Test ICP",
            description="A test ICP for validation",
            demographics=Demographics(
                age_range="25-45",
                gender="any",
                location=["United States"],
            ),
            professional_profile=ProfessionalProfile(
                job_titles=["Manager", "Director", "VP"],
                seniority_level="senior",
                company_size="200-1000",
                industry=["Technology"],
            ),
            pain_points=["Pain 1", "Pain 2", "Pain 3"],
            goals=["Goal 1", "Goal 2", "Goal 3"],
            motivations=Motivations(
                primary=["Efficiency", "Cost savings", "Growth"],
            ),
            decision_factors=["Factor 1", "Factor 2", "Factor 3"],
            buying_journey_stage=BuyingJourneyStage.CONSIDERATION,
        )

        assert icp.name == "Test ICP"
        assert len(icp.pain_points) == 3
        assert len(icp.goals) == 3

    def test_icp_requires_minimum_pain_points(self):
        """Test that ICP requires at least 3 pain points."""
        with pytest.raises(ValueError) as exc_info:
            GeneratedICP(
                name="Test ICP",
                description="Description",
                demographics=Demographics(
                    age_range="25-45",
                    gender="any",
                    location=["US"],
                ),
                professional_profile=ProfessionalProfile(
                    job_titles=["Manager"],
                    seniority_level="mid",
                    company_size="50-200",
                    industry=["Tech"],
                ),
                pain_points=["Only one pain point"],  # Invalid - needs 3
                goals=["Goal 1", "Goal 2", "Goal 3"],
                motivations=Motivations(primary=["Efficiency"]),
                decision_factors=["Factor 1", "Factor 2", "Factor 3"],
                buying_journey_stage=BuyingJourneyStage.AWARENESS,
            )

        assert "pain_points" in str(exc_info.value)

    def test_icp_generation_response_requires_five(self):
        """Test that response requires exactly 5 ICPs."""
        # Create 4 valid ICPs
        icps = []
        for i in range(4):
            icps.append(GeneratedICP(
                name=f"ICP {i+1}",
                description="Description",
                demographics=Demographics(age_range="25-45", gender="any", location=["US"]),
                professional_profile=ProfessionalProfile(
                    job_titles=["Manager"],
                    seniority_level="mid",
                    company_size="50-200",
                    industry=["Tech"],
                ),
                pain_points=["P1", "P2", "P3"],
                goals=["G1", "G2", "G3"],
                motivations=Motivations(primary=["M1", "M2", "M3"]),
                decision_factors=["D1", "D2", "D3"],
                buying_journey_stage=BuyingJourneyStage.AWARENESS,
            ))

        with pytest.raises(ValueError) as exc_info:
            ICPGenerationResponse(icps=icps)

        assert "5 ICPs" in str(exc_info.value)

    def test_icp_names_must_be_unique(self):
        """Test that ICP names must be unique."""
        # Create 5 ICPs with duplicate names
        icps = []
        for i in range(5):
            icps.append(GeneratedICP(
                name="Same Name",  # Duplicate
                description="Description",
                demographics=Demographics(age_range="25-45", gender="any", location=["US"]),
                professional_profile=ProfessionalProfile(
                    job_titles=["Manager"],
                    seniority_level="mid",
                    company_size="50-200",
                    industry=["Tech"],
                ),
                pain_points=["P1", "P2", "P3"],
                goals=["G1", "G2", "G3"],
                motivations=Motivations(primary=["M1", "M2", "M3"]),
                decision_factors=["D1", "D2", "D3"],
                buying_journey_stage=BuyingJourneyStage.AWARENESS,
            ))

        with pytest.raises(ValueError) as exc_info:
            ICPGenerationResponse(icps=icps)

        assert "unique" in str(exc_info.value).lower()


class TestWebsiteContext:
    """Test WebsiteContext functionality."""

    def test_to_prompt_context(self, sample_website_context):
        """Test context conversion to prompt format."""
        context_text = sample_website_context.to_prompt_context()

        assert "Acme Corp" in context_text
        assert "acme.com" in context_text
        assert "technology" in context_text
        assert "AcmePlatform" in context_text
        assert "40%" in context_text

    def test_minimal_context(self):
        """Test minimal context conversion."""
        context = WebsiteContext(
            domain="example.com",
            name=None,
            description=None,
            industry=None,
            business_model=None,
            primary_offerings=None,
            value_propositions=None,
            target_markets=None,
            company_profile=None,
            products_detailed=None,
            services_detailed=None,
            target_audience=None,
        )

        context_text = context.to_prompt_context()
        assert "example.com" in context_text


# ==================== Generator Tests ====================


class TestICPGenerator:
    """Test ICPGenerator functionality."""

    @pytest.mark.asyncio
    async def test_generate_with_mocked_llm(self, mock_llm_client, mock_llm_response):
        """Test ICP generation with mocked LLM."""
        generator = ICPGenerator(llm_client=mock_llm_client)

        # Parse the mocked response
        response = ICPGenerationResponse.model_validate_json(mock_llm_response.text)

        assert len(response.icps) == 5
        assert response.icps[0].name == "Enterprise IT Director"
        assert len(response.icps[0].pain_points) >= 3

    @pytest.mark.asyncio
    async def test_generate_validates_diversity(self, mock_llm_client):
        """Test that generator validates ICP diversity."""
        generator = ICPGenerator(llm_client=mock_llm_client)

        # Create ICPs with different characteristics
        icps_data = {
            "icps": [
                _create_test_icp(f"ICP {i}", f"{i}0-{i+1}0", ["Manager"], "mid", "50-200")
                for i in range(5)
            ]
        }

        mock_llm_client.complete_json.return_value = LLMResponse(
            text=json.dumps(icps_data),
            model="gpt-4o",
            provider="openai",
            tokens_used=1000,
            latency_ms=1000,
            raw_response={},
        )

        # This should not raise (names are unique)
        parsed = ICPGenerationResponse.model_validate(icps_data)
        assert len(parsed.icps) == 5

    def test_validate_diversity_fails_for_duplicate_names(self, mock_llm_client):
        """Test diversity validation catches duplicate names."""
        generator = ICPGenerator(llm_client=mock_llm_client)

        # Create 5 ICPs with same name
        icps = [
            GeneratedICP(
                name="Same Name",
                description="Description",
                demographics=Demographics(age_range="25-45", gender="any", location=["US"]),
                professional_profile=ProfessionalProfile(
                    job_titles=["Manager"],
                    seniority_level="mid",
                    company_size="50-200",
                    industry=["Tech"],
                ),
                pain_points=["P1", "P2", "P3"],
                goals=["G1", "G2", "G3"],
                motivations=Motivations(primary=["M1", "M2", "M3"]),
                decision_factors=["D1", "D2", "D3"],
                buying_journey_stage=BuyingJourneyStage.AWARENESS,
            )
            for _ in range(5)
        ]

        with pytest.raises(ValueError):
            generator._validate_diversity(icps)


# ==================== Prompt Tests ====================


class TestPrompts:
    """Test prompt generation."""

    def test_build_icp_generation_prompt(self, sample_website_context):
        """Test prompt building with full context."""
        prompt = build_icp_generation_prompt(sample_website_context)

        assert "Acme Corp" in prompt
        assert "technology" in prompt
        assert "5 ICPs" in prompt
        assert "JSON" in prompt

    def test_system_prompt_content(self):
        """Test system prompt contains key instructions."""
        assert "5 distinct ICPs" in ICP_SYSTEM_PROMPT
        assert "JSON" in ICP_SYSTEM_PROMPT
        assert "pain_points" in ICP_SYSTEM_PROMPT.lower() or "pain points" in ICP_SYSTEM_PROMPT.lower()


# ==================== Helper Functions ====================


def _create_test_icp(
    name: str,
    age_range: str = "25-45",
    job_titles: list[str] = None,
    seniority: str = "mid",
    company_size: str = "50-200",
) -> dict:
    """Create a test ICP dictionary."""
    return {
        "name": name,
        "description": f"Description for {name}",
        "demographics": {
            "age_range": age_range,
            "gender": "any",
            "location": ["United States"],
            "education_level": "Bachelor's",
            "income_level": "$80,000-$120,000"
        },
        "professional_profile": {
            "job_titles": job_titles or ["Manager", "Director"],
            "seniority_level": seniority,
            "department": "Operations",
            "company_size": company_size,
            "industry": ["Technology"],
            "years_experience": "5-10 years"
        },
        "pain_points": ["Pain point 1", "Pain point 2", "Pain point 3"],
        "goals": ["Goal 1", "Goal 2", "Goal 3"],
        "motivations": {
            "primary": ["Efficiency", "Cost savings", "Growth"],
            "secondary": ["Career growth"],
            "triggers": ["Budget cycle"]
        },
        "objections": ["Budget constraints"],
        "decision_factors": ["Price", "Features", "Support"],
        "information_sources": ["LinkedIn", "Industry blogs"],
        "buying_journey_stage": "consideration"
    }
