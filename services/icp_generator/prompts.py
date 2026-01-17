"""
Prompt engineering for ICP generation.

Contains system prompts and user prompt templates for generating
Ideal Customer Profiles using LLMs.
"""

from services.icp_generator.schemas import WebsiteContext


# System prompt for ICP generation
ICP_SYSTEM_PROMPT = """You are an expert B2B marketing strategist specializing in Ideal Customer Profile (ICP) development. Your task is to analyze website content and business information to generate comprehensive, actionable customer profiles.

You must generate EXACTLY 5 distinct ICPs that represent different customer segments for the business. Each ICP should be:
1. DISTINCT - Clearly different from the other ICPs in terms of demographics, job roles, or use cases
2. REALISTIC - Based on the actual products/services and value propositions
3. ACTIONABLE - Detailed enough to guide marketing and sales strategies
4. DIVERSE - Cover different company sizes, industries, or buyer personas

Guidelines for each ICP:
- Name: A memorable, descriptive title (e.g., "SMB Operations Manager", "Enterprise IT Director")
- Description: 2-3 sentences capturing who this person is and why they need this solution
- Demographics: Realistic age ranges, locations relevant to the business
- Professional Profile: Specific job titles, appropriate seniority, relevant industries
- Pain Points: Real business challenges this person faces (minimum 3, maximum 7)
- Goals: What they're trying to achieve professionally (minimum 3, maximum 7)
- Motivations: Primary drivers (efficiency, cost savings, growth, compliance, etc.)
- Objections: Common concerns or hesitations they might have
- Decision Factors: What influences their purchasing decisions (minimum 3, maximum 7)
- Information Sources: Where they research solutions (LinkedIn, industry publications, etc.)
- Buying Journey Stage: Where they typically enter the funnel (awareness, consideration, decision)

IMPORTANT: Your response must be valid JSON matching the exact schema provided. Do not include any explanatory text outside the JSON structure."""


# User prompt template for ICP generation
ICP_USER_PROMPT_TEMPLATE = """Based on the following business information, generate exactly 5 distinct Ideal Customer Profiles (ICPs).

## Business Context

{context}

## Output Requirements

Generate a JSON response with exactly 5 ICPs. Each ICP must include all required fields.

The response must match this exact JSON schema:
{{
  "icps": [
    {{
      "name": "string - descriptive name for the ICP",
      "description": "string - 2-3 sentence description",
      "demographics": {{
        "age_range": "string (e.g., '25-45')",
        "gender": "string ('male', 'female', 'any')",
        "location": ["array of strings - geographic locations"],
        "education_level": "string or null",
        "income_level": "string or null"
      }},
      "professional_profile": {{
        "job_titles": ["array of 3-5 common job titles"],
        "seniority_level": "string (entry, mid, senior, executive)",
        "department": "string or null",
        "company_size": "string (e.g., '10-50', '50-200', '200-1000', '1000+')",
        "industry": ["array of 1-3 target industries"],
        "years_experience": "string or null (e.g., '5-10 years')"
      }},
      "pain_points": ["array of 3-7 specific pain points"],
      "goals": ["array of 3-7 professional goals"],
      "motivations": {{
        "primary": ["array of 3-5 primary motivators"],
        "secondary": ["array of secondary motivators"],
        "triggers": ["array of buying triggers"]
      }},
      "objections": ["array of common buying objections"],
      "decision_factors": ["array of 3-7 decision factors"],
      "information_sources": ["array of information sources"],
      "buying_journey_stage": "string (awareness, consideration, decision, retention)"
    }}
  ]
}}

Ensure:
1. All 5 ICPs are distinctly different
2. Each ICP name is unique
3. Pain points, goals, and decision factors each have 3-7 items
4. All required fields are present
5. The JSON is valid and properly formatted"""


def build_icp_generation_prompt(context: WebsiteContext) -> str:
    """
    Build the user prompt for ICP generation.

    Args:
        context: Website context information.

    Returns:
        Formatted user prompt string.
    """
    context_text = context.to_prompt_context()
    return ICP_USER_PROMPT_TEMPLATE.format(context=context_text)


# Validation prompt to check and fix ICPs
ICP_VALIDATION_PROMPT = """Review the following ICP data and ensure it meets all requirements:

1. Exactly 5 ICPs
2. Each ICP has a unique, descriptive name
3. Each ICP has at least 3 pain points, 3 goals, and 3 decision factors
4. The ICPs are diverse and represent different customer segments
5. All required fields are present and properly formatted

Current ICP Data:
{icp_data}

If the data is valid, return it unchanged. If there are issues, fix them and return the corrected JSON.

Return only the JSON response, no additional text."""


# Prompt for generating ICP from minimal context
ICP_MINIMAL_CONTEXT_PROMPT = """Generate 5 Ideal Customer Profiles for a business with the following limited information:

Domain: {domain}
Name: {name}
Industry (if known): {industry}

Since we have limited information, make reasonable assumptions based on the domain name and any industry hints. Create diverse profiles that would typically be interested in a {industry_or_general} business.

{schema_instructions}"""


def build_minimal_context_prompt(
    domain: str,
    name: str | None,
    industry: str | None,
) -> str:
    """
    Build prompt for ICP generation with minimal context.

    Args:
        domain: Website domain.
        name: Website name if available.
        industry: Industry if detected.

    Returns:
        Formatted prompt string.
    """
    industry_or_general = industry or "general technology/services"

    return ICP_MINIMAL_CONTEXT_PROMPT.format(
        domain=domain,
        name=name or domain,
        industry=industry or "Unknown",
        industry_or_general=industry_or_general,
        schema_instructions=ICP_USER_PROMPT_TEMPLATE.split("## Output Requirements")[1],
    )


# Prompt for diversity check
DIVERSITY_CHECK_PROMPT = """Analyze these 5 ICPs for diversity. Rate their diversity on a scale of 1-10 and suggest improvements if needed.

ICPs:
{icps_summary}

Consider:
1. Are the job roles/titles sufficiently different?
2. Are company sizes diverse (SMB to Enterprise)?
3. Are there different industries represented?
4. Are the pain points and goals unique to each ICP?
5. Do they represent different stages of the buying journey?

If diversity score is below 7, regenerate the ICPs with better differentiation.

Response format:
{{
  "diversity_score": <1-10>,
  "issues": ["list of diversity issues"],
  "needs_regeneration": <true/false>,
  "suggestions": ["list of improvement suggestions"]
}}"""
