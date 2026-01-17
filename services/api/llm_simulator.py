"""
LLM Response Simulator - Deterministic fake LLM responses for testing.

This module generates consistent, reproducible fake LLM responses based on:
- Prompt text keywords
- Provider characteristics
- Brand context

Key guarantees:
- Same prompt + provider = same output (deterministic)
- Evaluation prompts produce comparisons
- Decision prompts produce recommendations
- Competitors rotate when tracked brand is missing
"""

import hashlib
import random
import re
from dataclasses import dataclass, field
from typing import Any

from shared.models.enums import BeliefType, BrandPresence, IntentType


# --- Constants ---

# Competitor brands by industry/category
COMPETITOR_POOLS = {
    "default": [
        "Acme Corp", "TechGiant", "InnovateCo", "GlobalSoft", "NextGen Solutions",
        "PrimeServices", "EliteTech", "MegaSystems", "SmartSolutions", "CloudFirst",
    ],
    "saas": [
        "Salesforce", "HubSpot", "Zendesk", "Freshworks", "Monday.com",
        "Asana", "Notion", "Airtable", "Slack", "Zoom",
    ],
    "ecommerce": [
        "Shopify", "BigCommerce", "WooCommerce", "Magento", "Squarespace",
        "Wix", "PrestaShop", "OpenCart", "Volusion", "3dcart",
    ],
    "analytics": [
        "Google Analytics", "Mixpanel", "Amplitude", "Heap", "Pendo",
        "Hotjar", "FullStory", "Segment", "Looker", "Tableau",
    ],
    "marketing": [
        "Mailchimp", "Klaviyo", "ActiveCampaign", "Constant Contact", "SendGrid",
        "Marketo", "Pardot", "Drip", "ConvertKit", "Brevo",
    ],
    "security": [
        "CrowdStrike", "Palo Alto", "Fortinet", "SentinelOne", "Splunk",
        "Okta", "Zscaler", "Cloudflare", "Datadog", "Snyk",
    ],
}

# Provider-specific response characteristics
PROVIDER_PROFILES = {
    "openai": {
        "style": "balanced",
        "brand_mention_rate": 0.7,
        "recommendation_rate": 0.4,
        "verbosity": 1.0,
        "comparison_detail": "moderate",
    },
    "google": {
        "style": "factual",
        "brand_mention_rate": 0.8,
        "recommendation_rate": 0.3,
        "verbosity": 1.2,
        "comparison_detail": "high",
    },
    "anthropic": {
        "style": "cautious",
        "brand_mention_rate": 0.6,
        "recommendation_rate": 0.35,
        "verbosity": 1.1,
        "comparison_detail": "moderate",
    },
    "perplexity": {
        "style": "concise",
        "brand_mention_rate": 0.75,
        "recommendation_rate": 0.5,
        "verbosity": 0.8,
        "comparison_detail": "low",
    },
}

# Keywords that trigger specific intent detection
INTENT_KEYWORDS = {
    IntentType.DECISION: [
        "best", "should i", "recommend", "which one", "buy", "purchase",
        "choose", "pick", "go with", "invest in", "sign up", "subscribe",
    ],
    IntentType.EVALUATION: [
        "compare", "vs", "versus", "difference", "better", "alternative",
        "pros and cons", "review", "comparison", "how does", "stack up",
    ],
    IntentType.INFORMATIONAL: [
        "what is", "how to", "explain", "define", "overview", "guide",
        "tutorial", "learn", "understand", "introduction", "basics",
    ],
}

# Keywords that suggest specific industries
INDUSTRY_KEYWORDS = {
    "saas": ["software", "saas", "app", "platform", "tool", "subscription"],
    "ecommerce": ["shop", "store", "ecommerce", "sell", "commerce", "retail"],
    "analytics": ["analytics", "data", "metrics", "tracking", "insights", "dashboard"],
    "marketing": ["marketing", "email", "campaign", "automation", "crm", "leads"],
    "security": ["security", "protect", "cyber", "firewall", "antivirus", "compliance"],
}

# Belief type triggers based on response context
BELIEF_TRIGGERS = {
    BeliefType.TRUTH: ["factually", "objectively", "research shows", "according to"],
    BeliefType.SUPERIORITY: ["best", "leading", "top-rated", "outperforms", "#1"],
    BeliefType.OUTCOME: ["roi", "results", "performance", "efficiency", "saves"],
    BeliefType.TRANSACTION: ["try", "start", "sign up", "get started", "free trial"],
    BeliefType.IDENTITY: ["teams like yours", "companies similar", "professionals use"],
    BeliefType.SOCIAL_PROOF: ["trusted by", "used by", "customers", "reviews", "ratings"],
}


# --- Data Classes ---

@dataclass
class BrandMention:
    """Represents a brand mentioned in a response."""
    name: str
    position: int  # 1-indexed position in response
    presence: BrandPresence
    belief_sold: BeliefType | None
    context: str  # The sentence/context where mentioned


@dataclass
class SimulatedResponse:
    """Complete simulated LLM response."""
    response_text: str
    brands_mentioned: list[str]
    brand_details: list[BrandMention]
    response_tokens: int
    latency_ms: int
    detected_intent: IntentType
    detected_industry: str


# --- Core Simulator ---

class LLMSimulator:
    """
    Deterministic LLM response simulator.

    Generates consistent fake responses based on prompt content and provider.
    Same inputs always produce same outputs via seeded randomness.
    """

    def __init__(self, tracked_brand: str, tracked_domain: str | None = None):
        """
        Initialize simulator with tracked brand context.

        Args:
            tracked_brand: The user's brand name to track
            tracked_domain: Optional domain for additional context
        """
        self.tracked_brand = tracked_brand
        self.tracked_domain = tracked_domain

    def _get_seed(self, prompt: str, provider: str) -> int:
        """Generate deterministic seed from prompt and provider."""
        content = f"{prompt.lower().strip()}:{provider.lower()}"
        return int(hashlib.sha256(content.encode()).hexdigest()[:8], 16)

    def _detect_intent(self, prompt: str) -> IntentType:
        """Detect user intent from prompt keywords."""
        prompt_lower = prompt.lower()

        # Check decision keywords first (highest priority)
        for keyword in INTENT_KEYWORDS[IntentType.DECISION]:
            if keyword in prompt_lower:
                return IntentType.DECISION

        # Check evaluation keywords
        for keyword in INTENT_KEYWORDS[IntentType.EVALUATION]:
            if keyword in prompt_lower:
                return IntentType.EVALUATION

        # Default to informational
        return IntentType.INFORMATIONAL

    def _detect_industry(self, prompt: str) -> str:
        """Detect industry from prompt keywords."""
        prompt_lower = prompt.lower()

        for industry, keywords in INDUSTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    return industry

        return "default"

    def _select_competitors(
        self,
        rng: random.Random,
        industry: str,
        count: int,
        include_tracked: bool,
    ) -> list[str]:
        """Select competitor brands based on industry and seed."""
        pool = COMPETITOR_POOLS.get(industry, COMPETITOR_POOLS["default"])

        # Sample from pool
        selected = rng.sample(pool, min(count, len(pool)))

        # Maybe include tracked brand
        if include_tracked and self.tracked_brand not in selected:
            # Insert at random position
            insert_pos = rng.randint(0, len(selected))
            selected.insert(insert_pos, self.tracked_brand)
        elif not include_tracked and self.tracked_brand in selected:
            # Remove if present and we don't want it
            selected.remove(self.tracked_brand)

        return selected[:count]  # Ensure count limit

    def _determine_presence(
        self,
        rng: random.Random,
        brand: str,
        position: int,
        intent: IntentType,
        is_tracked: bool,
    ) -> BrandPresence:
        """Determine brand presence state based on context."""

        # Decision intents favor recommendations
        if intent == IntentType.DECISION:
            if position == 1:
                # First position in decision context = recommended
                return BrandPresence.RECOMMENDED
            elif position <= 3:
                return rng.choices(
                    [BrandPresence.RECOMMENDED, BrandPresence.TRUSTED, BrandPresence.MENTIONED],
                    weights=[0.4, 0.35, 0.25],
                    k=1
                )[0]
            else:
                return rng.choices(
                    [BrandPresence.MENTIONED, BrandPresence.TRUSTED],
                    weights=[0.7, 0.3],
                    k=1
                )[0]

        # Evaluation intents favor comparisons
        elif intent == IntentType.EVALUATION:
            if position <= 2:
                return BrandPresence.COMPARED
            else:
                return rng.choices(
                    [BrandPresence.COMPARED, BrandPresence.MENTIONED],
                    weights=[0.6, 0.4],
                    k=1
                )[0]

        # Informational intents are more neutral
        else:
            if position == 1:
                return rng.choices(
                    [BrandPresence.MENTIONED, BrandPresence.TRUSTED],
                    weights=[0.6, 0.4],
                    k=1
                )[0]
            else:
                return rng.choices(
                    [BrandPresence.MENTIONED, BrandPresence.IGNORED],
                    weights=[0.8, 0.2],
                    k=1
                )[0]

    def _determine_belief(
        self,
        rng: random.Random,
        presence: BrandPresence,
        intent: IntentType,
    ) -> BeliefType | None:
        """Determine belief type based on presence and intent."""

        # Ignored brands don't sell beliefs
        if presence == BrandPresence.IGNORED:
            return None

        # Map presence to likely beliefs
        if presence == BrandPresence.RECOMMENDED:
            return rng.choices(
                [BeliefType.SUPERIORITY, BeliefType.OUTCOME, BeliefType.SOCIAL_PROOF],
                weights=[0.4, 0.35, 0.25],
                k=1
            )[0]

        elif presence == BrandPresence.COMPARED:
            return rng.choices(
                [BeliefType.TRUTH, BeliefType.SUPERIORITY, BeliefType.OUTCOME],
                weights=[0.4, 0.3, 0.3],
                k=1
            )[0]

        elif presence == BrandPresence.TRUSTED:
            return rng.choices(
                [BeliefType.SOCIAL_PROOF, BeliefType.OUTCOME, BeliefType.IDENTITY],
                weights=[0.4, 0.35, 0.25],
                k=1
            )[0]

        else:  # MENTIONED
            return rng.choices(
                [BeliefType.TRUTH, BeliefType.OUTCOME, None],
                weights=[0.4, 0.3, 0.3],
                k=1
            )[0]

    def _generate_brand_context(
        self,
        rng: random.Random,
        brand: str,
        presence: BrandPresence,
        belief: BeliefType | None,
        intent: IntentType,
    ) -> str:
        """Generate context sentence for a brand mention."""

        templates = {
            BrandPresence.RECOMMENDED: [
                f"**{brand}** is highly recommended for its excellent features and reliability.",
                f"I would suggest **{brand}** as a top choice in this space.",
                f"**{brand}** stands out as a leading solution for your needs.",
                f"For your use case, **{brand}** would be my top recommendation.",
            ],
            BrandPresence.COMPARED: [
                f"**{brand}** offers competitive features compared to alternatives.",
                f"When comparing options, **{brand}** provides strong value.",
                f"**{brand}** vs competitors shows interesting trade-offs.",
                f"In terms of capabilities, **{brand}** holds its own against rivals.",
            ],
            BrandPresence.TRUSTED: [
                f"**{brand}** is trusted by many organizations in this field.",
                f"**{brand}** has established itself as a reliable option.",
                f"Many teams rely on **{brand}** for their needs.",
                f"**{brand}** has a strong track record in this area.",
            ],
            BrandPresence.MENTIONED: [
                f"**{brand}** is one option worth considering.",
                f"You might also look at **{brand}**.",
                f"**{brand}** is another player in this market.",
                f"Some users have found success with **{brand}**.",
            ],
            BrandPresence.IGNORED: [
                "",  # No context for ignored brands
            ],
        }

        options = templates.get(presence, templates[BrandPresence.MENTIONED])
        return rng.choice(options) if options else ""

    def _generate_response_text(
        self,
        rng: random.Random,
        prompt: str,
        provider: str,
        intent: IntentType,
        brand_details: list[BrandMention],
    ) -> str:
        """Generate full response text."""
        profile = PROVIDER_PROFILES.get(provider, PROVIDER_PROFILES["openai"])

        # Opening based on intent
        openings = {
            IntentType.DECISION: [
                f"Based on your requirements, here are my recommendations:",
                f"For your specific needs, I'd suggest considering these options:",
                f"Here are the top solutions I would recommend:",
            ],
            IntentType.EVALUATION: [
                f"Let me compare the key options for you:",
                f"Here's a comparison of the main alternatives:",
                f"When evaluating your options, consider these factors:",
            ],
            IntentType.INFORMATIONAL: [
                f"Here's an overview of the options in this space:",
                f"Let me provide some information about available solutions:",
                f"There are several notable options to be aware of:",
            ],
        }

        opening = rng.choice(openings[intent])

        # Build response parts
        parts = [opening, ""]

        # Add brand contexts
        for i, brand in enumerate(brand_details, 1):
            if brand.presence != BrandPresence.IGNORED and brand.context:
                parts.append(f"{i}. {brand.context}")

        # Closing based on intent
        closings = {
            IntentType.DECISION: [
                "\nThe best choice depends on your specific requirements, budget, and team size.",
                "\nI'd recommend starting with a trial of your top choice to validate the fit.",
                "\nConsider your key priorities when making the final decision.",
            ],
            IntentType.EVALUATION: [
                "\nEach option has its strengths - the right choice depends on your priorities.",
                "\nConsider running a proof-of-concept with your top 2-3 choices.",
                "\nThe comparison above should help you narrow down your options.",
            ],
            IntentType.INFORMATIONAL: [
                "\nI hope this overview helps you understand the landscape better.",
                "\nFeel free to ask if you'd like more details on any specific option.",
                "\nLet me know if you'd like me to dive deeper into any of these.",
            ],
        }

        parts.append(rng.choice(closings[intent]))

        return "\n".join(parts)

    def simulate_response(
        self,
        prompt: str,
        provider: str,
        classification: dict[str, Any] | None = None,
    ) -> SimulatedResponse:
        """
        Generate a simulated LLM response.

        Args:
            prompt: The user prompt text
            provider: LLM provider name (openai, google, anthropic, perplexity)
            classification: Optional pre-computed prompt classification

        Returns:
            SimulatedResponse with deterministic fake data
        """
        # Get deterministic seed
        seed = self._get_seed(prompt, provider)
        rng = random.Random(seed)

        # Get provider profile
        profile = PROVIDER_PROFILES.get(provider, PROVIDER_PROFILES["openai"])

        # Detect intent (use classification if provided)
        if classification and "intent_type" in classification:
            intent_str = classification["intent_type"]
            try:
                intent = IntentType(intent_str)
            except ValueError:
                intent = self._detect_intent(prompt)
        else:
            intent = self._detect_intent(prompt)

        # Detect industry
        industry = self._detect_industry(prompt)

        # Determine if tracked brand should be included
        include_tracked = rng.random() < profile["brand_mention_rate"]

        # Select number of brands based on intent
        if intent == IntentType.DECISION:
            num_brands = rng.randint(3, 5)
        elif intent == IntentType.EVALUATION:
            num_brands = rng.randint(2, 4)
        else:
            num_brands = rng.randint(2, 3)

        # Select competitors
        competitors = self._select_competitors(rng, industry, num_brands, include_tracked)

        # Generate brand details
        brand_details = []
        for position, brand_name in enumerate(competitors, 1):
            is_tracked = brand_name.lower() == self.tracked_brand.lower()

            presence = self._determine_presence(rng, brand_name, position, intent, is_tracked)
            belief = self._determine_belief(rng, presence, intent)
            context = self._generate_brand_context(rng, brand_name, presence, belief, intent)

            brand_details.append(BrandMention(
                name=brand_name,
                position=position,
                presence=presence,
                belief_sold=belief,
                context=context,
            ))

        # Generate response text
        response_text = self._generate_response_text(rng, prompt, provider, intent, brand_details)

        # Calculate tokens and latency
        base_tokens = len(response_text.split()) * 1.3  # Rough token estimate
        response_tokens = int(base_tokens * profile["verbosity"])
        latency_ms = rng.randint(400, 1500) + (response_tokens * 2)

        return SimulatedResponse(
            response_text=response_text,
            brands_mentioned=[b.name for b in brand_details if b.presence != BrandPresence.IGNORED],
            brand_details=brand_details,
            response_tokens=response_tokens,
            latency_ms=latency_ms,
            detected_intent=intent,
            detected_industry=industry,
        )


# --- Convenience Function ---

def simulate_response(
    prompt: str,
    provider: str,
    tracked_brand: str,
    tracked_domain: str | None = None,
    classification: dict[str, Any] | None = None,
) -> SimulatedResponse:
    """
    Convenience function to simulate an LLM response.

    Args:
        prompt: The user prompt text
        provider: LLM provider name
        tracked_brand: Brand being tracked
        tracked_domain: Optional domain
        classification: Optional prompt classification

    Returns:
        SimulatedResponse with deterministic fake data

    Example:
        >>> response = simulate_response(
        ...     prompt="What's the best CRM for small teams?",
        ...     provider="openai",
        ...     tracked_brand="Acme CRM"
        ... )
        >>> print(response.brands_mentioned)
        ['Salesforce', 'HubSpot', 'Acme CRM', 'Freshworks']
    """
    simulator = LLMSimulator(tracked_brand, tracked_domain)
    return simulator.simulate_response(prompt, provider, classification)


# --- Testing ---

if __name__ == "__main__":
    # Test determinism
    print("Testing determinism...")
    r1 = simulate_response("What's the best CRM?", "openai", "TestBrand")
    r2 = simulate_response("What's the best CRM?", "openai", "TestBrand")
    assert r1.response_text == r2.response_text, "Responses should be identical!"
    assert r1.brands_mentioned == r2.brands_mentioned, "Brands should be identical!"
    print("✓ Determinism test passed")

    # Test different intents
    print("\nTesting intent detection...")
    decision = simulate_response("Which CRM should I buy?", "openai", "TestBrand")
    print(f"Decision intent: {decision.detected_intent}")
    assert decision.detected_intent == IntentType.DECISION

    evaluation = simulate_response("Compare Salesforce vs HubSpot", "openai", "TestBrand")
    print(f"Evaluation intent: {evaluation.detected_intent}")
    assert evaluation.detected_intent == IntentType.EVALUATION

    info = simulate_response("What is a CRM?", "openai", "TestBrand")
    print(f"Informational intent: {info.detected_intent}")
    assert info.detected_intent == IntentType.INFORMATIONAL
    print("✓ Intent detection test passed")

    # Test presence states
    print("\nSample response:")
    sample = simulate_response(
        "What are the best project management tools for startups?",
        "anthropic",
        "MyTool"
    )
    print(f"Intent: {sample.detected_intent}")
    print(f"Industry: {sample.detected_industry}")
    print(f"Brands: {sample.brands_mentioned}")
    print("\nBrand details:")
    for b in sample.brand_details:
        print(f"  {b.position}. {b.name}: {b.presence.value} ({b.belief_sold.value if b.belief_sold else 'none'})")
    print(f"\nResponse:\n{sample.response_text}")
