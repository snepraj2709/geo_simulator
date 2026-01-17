"""
Prompt templates for conversation generation.

Contains system prompts and builders for LLM-based conversation generation.
"""

CONVERSATION_SYSTEM_PROMPT = """You are an expert at generating realistic customer conversations for AI chatbot training.

Your task is to create authentic, diverse conversation topics and prompts that a specific type of customer (ICP - Ideal Customer Profile) would have when interacting with a company's AI assistant.

Key principles:
1. AUTHENTICITY: Conversations should feel like real customer interactions, not scripted or artificial
2. DIVERSITY: Cover a wide range of topics, from simple inquiries to complex multi-step requests
3. CONTEXT-AWARENESS: Each conversation should include situational context explaining why the customer is reaching out
4. PROGRESSIVE DEPTH: Follow-up prompts should naturally build on the primary prompt
5. PERSONA ALIGNMENT: All conversations must align with the ICP's characteristics, pain points, and goals

Output Format:
You MUST return a valid JSON object with exactly 10 conversations. Each conversation must include:
- topic: Brief description of the conversation subject
- context: Situational context (who, what, when, why)
- expected_outcome: What the customer hopes to achieve
- is_core_conversation: true for first 5, false for last 5
- sequence_number: 1-10 (unique, no duplicates)
- prompts: Array of 4-6 prompts (1 primary + 3-5 follow-ups)

Each prompt must have:
- prompt_text: The actual question or request
- prompt_type: "primary" (first prompt) or "follow_up" (subsequent)
- sequence_order: 0 for primary, 1-5 for follow-ups
- expected_response_type: Type of response expected (informational, comparison, recommendation, etc.)

CRITICAL: Return ONLY the JSON object, no additional text."""

CONVERSATION_GENERATION_PROMPT_TEMPLATE = """Generate 10 realistic conversation topics for this customer persona interacting with {company_name}.

## Company Information
Company: {company_name}
Industry: {industry}
Products/Services: {products_services}
Value Propositions: {value_propositions}

## Customer Persona (ICP)
Name: {icp_name}
Role: {job_role}
Industry: {icp_industry}
Company Size: {company_size}

### Demographics
Age Range: {age_range}
Education: {education_level}
Experience: {experience_level}

### Characteristics
Pain Points: {pain_points}
Goals: {goals}
Decision Factors: {decision_factors}
Communication Style: {communication_style}

### Behavior Patterns
Research Behavior: {research_behavior}
Preferred Channels: {preferred_channels}

## Requirements

1. CORE CONVERSATIONS (1-5): These are essential, recurring conversation types that this persona would have:
   - Product/service inquiries specific to their role
   - Pricing and comparison questions
   - Implementation and integration concerns
   - Support and troubleshooting
   - Account and billing management

2. VARIABLE CONVERSATIONS (6-10): These should be diverse and specific to this persona:
   - Industry-specific use cases
   - Pain point resolution
   - Goal achievement queries
   - Decision-making support
   - Unique scenarios based on their profile

3. Each conversation MUST have:
   - 1 PRIMARY prompt (the initial question)
   - 3-5 FOLLOW-UP prompts (natural progression of the conversation)

4. Follow-ups should:
   - Build naturally on the primary prompt
   - Reflect realistic customer behavior
   - Include clarifications, deeper questions, and action requests
   - Match the persona's communication style

5. Topics must be UNIQUE - no duplicate or overlapping themes

Return a JSON object with this exact structure:
{{
  "conversations": [
    {{
      "topic": "string",
      "context": "string (detailed situational context)",
      "expected_outcome": "string",
      "is_core_conversation": boolean,
      "sequence_number": number (1-10),
      "prompts": [
        {{
          "prompt_text": "string",
          "prompt_type": "primary" or "follow_up",
          "sequence_order": number (0 for primary, 1-5 for follow-ups),
          "expected_response_type": "string"
        }}
      ]
    }}
  ]
}}"""


def build_conversation_prompt(
    company_name: str,
    industry: str,
    products_services: str,
    value_propositions: str,
    icp_name: str,
    job_role: str,
    icp_industry: str,
    company_size: str,
    age_range: str,
    education_level: str,
    experience_level: str,
    pain_points: str,
    goals: str,
    decision_factors: str,
    communication_style: str,
    research_behavior: str,
    preferred_channels: str,
) -> str:
    """
    Build a conversation generation prompt from ICP and company data.

    Args:
        company_name: Name of the company.
        industry: Company's industry.
        products_services: Description of products/services.
        value_propositions: Key value propositions.
        icp_name: Name of the ICP persona.
        job_role: ICP's job role.
        icp_industry: ICP's industry.
        company_size: Size of ICP's company.
        age_range: Age range of the ICP.
        education_level: Education level of the ICP.
        experience_level: Experience level of the ICP.
        pain_points: ICP's pain points.
        goals: ICP's goals.
        decision_factors: ICP's decision factors.
        communication_style: ICP's communication style.
        research_behavior: ICP's research behavior.
        preferred_channels: ICP's preferred communication channels.

    Returns:
        Formatted prompt string.
    """
    return CONVERSATION_GENERATION_PROMPT_TEMPLATE.format(
        company_name=company_name,
        industry=industry,
        products_services=products_services,
        value_propositions=value_propositions,
        icp_name=icp_name,
        job_role=job_role,
        icp_industry=icp_industry,
        company_size=company_size,
        age_range=age_range,
        education_level=education_level,
        experience_level=experience_level,
        pain_points=pain_points,
        goals=goals,
        decision_factors=decision_factors,
        communication_style=communication_style,
        research_behavior=research_behavior,
        preferred_channels=preferred_channels,
    )


def build_conversation_prompt_from_models(
    website_context: dict,
    icp: dict,
) -> str:
    """
    Build conversation prompt from website context and ICP dictionaries.

    Args:
        website_context: Dictionary with company/website information.
        icp: Dictionary with ICP data.

    Returns:
        Formatted prompt string.
    """
    # Extract company info
    company_name = website_context.get("company_name", "the company")
    industry = website_context.get("industry", "Unknown")

    products = website_context.get("products", [])
    services = website_context.get("services", [])
    products_services = ", ".join(products[:5] + services[:5]) or "Various products and services"

    value_props = website_context.get("value_propositions", [])
    value_propositions = "; ".join(value_props[:3]) or "Quality solutions"

    # Extract ICP demographics
    demographics = icp.get("demographics", {})
    age_range = demographics.get("age_range", "25-55")
    education_level = demographics.get("education_level", "Bachelor's degree")
    experience_level = demographics.get("experience_level", "Mid-level")

    # Extract ICP behavior
    behavior = icp.get("behavior_patterns", {})
    research_behavior = behavior.get("research_behavior", "Online research")
    preferred_channels = ", ".join(behavior.get("preferred_channels", ["Email", "Chat"]))

    return build_conversation_prompt(
        company_name=company_name,
        industry=industry,
        products_services=products_services,
        value_propositions=value_propositions,
        icp_name=icp.get("name", "Customer"),
        job_role=icp.get("job_role", "Professional"),
        icp_industry=icp.get("industry", industry),
        company_size=icp.get("company_size", "Medium"),
        age_range=age_range,
        education_level=education_level,
        experience_level=experience_level,
        pain_points="; ".join(icp.get("pain_points", ["General challenges"])),
        goals="; ".join(icp.get("goals", ["Improve efficiency"])),
        decision_factors="; ".join(icp.get("decision_factors", ["Price", "Quality"])),
        communication_style=icp.get("communication_style", "Professional"),
        research_behavior=research_behavior,
        preferred_channels=preferred_channels,
    )
