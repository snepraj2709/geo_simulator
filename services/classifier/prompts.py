"""
Prompt templates for prompt classification.

Contains system prompts and builders for LLM-based intent classification.
"""

CLASSIFICATION_SYSTEM_PROMPT = """You are an expert at analyzing user prompts and classifying their intent, funnel stage, and buying signals.

Your task is to classify each prompt according to these dimensions:

## Intent Type (intent_type)
- **informational**: User is seeking knowledge, learning, or understanding. Questions like "What is...", "How does...", "Explain..."
- **evaluation**: User is comparing options, analyzing alternatives, or assessing fit. Questions like "Which is better...", "Compare...", "Pros and cons of..."
- **decision**: User is ready to make a choice or take action. Questions like "Should I buy...", "How do I get started with...", "Where can I purchase..."

## Funnel Stage (funnel_stage)
- **awareness**: User is discovering a problem or solution category. Early-stage research, general questions.
- **consideration**: User is actively evaluating solutions, comparing specific options, narrowing choices.
- **purchase**: User is ready to buy, implement, or commit. Focused on pricing, implementation, onboarding.

## Buying Signal (buying_signal: 0.0 - 1.0)
How close is the user to making a purchase decision?
- 0.0-0.3: No purchase intent, purely educational
- 0.3-0.5: Some interest, early exploration
- 0.5-0.7: Active consideration, comparing options
- 0.7-0.9: Strong intent, close to decision
- 0.9-1.0: Ready to buy, asking about pricing/implementation

## Trust Need (trust_need: 0.0 - 1.0)
How much authority, proof, or credibility does the user need?
- 0.0-0.3: Low - casual inquiry, doesn't need proof
- 0.3-0.5: Moderate - wants some validation
- 0.5-0.7: Significant - needs expert opinions, case studies
- 0.7-0.9: High - requires strong proof, multiple sources
- 0.9-1.0: Critical - needs extensive evidence, guarantees

## Query Intent (query_intent)
- **Commercial**: User intends to make a purchase (now or later)
- **Informational**: User wants to learn something
- **Navigational**: User is trying to find a specific website/page
- **Transactional**: User wants to complete an action (sign up, download, etc.)

Output Format:
Return a valid JSON object with these exact fields:
{
  "intent_type": "informational" | "evaluation" | "decision",
  "funnel_stage": "awareness" | "consideration" | "purchase",
  "buying_signal": 0.0-1.0,
  "trust_need": 0.0-1.0,
  "query_intent": "Commercial" | "Informational" | "Navigational" | "Transactional",
  "reasoning": "Brief explanation (1-2 sentences)"
}

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting."""


SINGLE_CLASSIFICATION_PROMPT = """Classify the following prompt:

Prompt: "{prompt_text}"

{context_section}
Return a JSON object with the classification."""


BATCH_CLASSIFICATION_PROMPT = """Classify each of the following prompts. Return a JSON array with one classification object per prompt.

Prompts to classify:
{prompts_list}

Return a JSON object with this structure:
{{
  "classifications": [
    {{
      "intent_type": "...",
      "funnel_stage": "...",
      "buying_signal": 0.0-1.0,
      "trust_need": 0.0-1.0,
      "query_intent": "...",
      "reasoning": "..."
    }},
    ...
  ]
}}

IMPORTANT: Return exactly {count} classification objects in the same order as the prompts."""


def build_single_classification_prompt(
    prompt_text: str,
    conversation_topic: str | None = None,
    conversation_context: str | None = None,
    icp_name: str | None = None,
    icp_pain_points: list[str] | None = None,
) -> str:
    """
    Build a prompt for classifying a single user prompt.

    Args:
        prompt_text: The prompt to classify.
        conversation_topic: Topic of the conversation.
        conversation_context: Context of the conversation.
        icp_name: Name of the ICP persona.
        icp_pain_points: Pain points of the ICP.

    Returns:
        Formatted classification prompt.
    """
    context_parts = []

    if conversation_topic:
        context_parts.append(f"Conversation Topic: {conversation_topic}")

    if conversation_context:
        context_parts.append(f"Context: {conversation_context}")

    if icp_name:
        context_parts.append(f"User Persona: {icp_name}")

    if icp_pain_points:
        context_parts.append(f"User Pain Points: {', '.join(icp_pain_points[:3])}")

    context_section = ""
    if context_parts:
        context_section = "\nAdditional Context:\n" + "\n".join(context_parts) + "\n"

    return SINGLE_CLASSIFICATION_PROMPT.format(
        prompt_text=prompt_text,
        context_section=context_section,
    )


def build_batch_classification_prompt(
    prompts: list[dict],
) -> str:
    """
    Build a prompt for batch classification.

    Args:
        prompts: List of prompts with optional context.
                 Each dict should have 'prompt_text' and optionally 'context'.

    Returns:
        Formatted batch classification prompt.
    """
    prompts_list = []

    for i, p in enumerate(prompts, 1):
        prompt_text = p.get("prompt_text", "")
        context = p.get("context", "")

        if context:
            prompts_list.append(f"{i}. \"{prompt_text}\"\n   Context: {context}")
        else:
            prompts_list.append(f"{i}. \"{prompt_text}\"")

    return BATCH_CLASSIFICATION_PROMPT.format(
        prompts_list="\n".join(prompts_list),
        count=len(prompts),
    )


# ==================== Classification Heuristics ====================

# Keywords that indicate specific intents
INTENT_KEYWORDS = {
    "informational": [
        "what is", "what are", "how does", "how do", "explain", "tell me about",
        "describe", "define", "overview", "introduction", "basics", "understand",
        "learn", "meaning of", "difference between", "why is", "when should",
    ],
    "evaluation": [
        "compare", "versus", "vs", "which is better", "pros and cons", "advantages",
        "disadvantages", "review", "alternative", "comparison", "evaluate", "assess",
        "benchmark", "rank", "top", "best", "worst", "recommend", "suggestions",
    ],
    "decision": [
        "should i", "how to buy", "where to buy", "pricing", "cost", "purchase",
        "subscribe", "sign up", "get started", "implement", "integrate", "setup",
        "demo", "trial", "quote", "contact sales", "enterprise plan",
    ],
}

FUNNEL_KEYWORDS = {
    "awareness": [
        "what is", "basics", "introduction", "overview", "beginner", "getting started",
        "learn about", "understand", "meaning", "definition", "types of",
    ],
    "consideration": [
        "compare", "vs", "versus", "alternative", "which", "review", "features",
        "capabilities", "integration", "use case", "case study", "testimonial",
    ],
    "purchase": [
        "pricing", "price", "cost", "buy", "purchase", "subscribe", "plan",
        "enterprise", "quote", "demo", "trial", "discount", "offer", "payment",
    ],
}

QUERY_INTENT_KEYWORDS = {
    "Commercial": [
        "buy", "price", "pricing", "cost", "purchase", "deal", "discount",
        "cheap", "affordable", "best", "top", "review", "compare",
    ],
    "Informational": [
        "what", "how", "why", "when", "who", "explain", "guide", "tutorial",
        "learn", "understand", "definition", "meaning",
    ],
    "Navigational": [
        "login", "sign in", "website", "official", "homepage", "support page",
        "contact", "account", "dashboard",
    ],
    "Transactional": [
        "download", "register", "sign up", "subscribe", "book", "schedule",
        "order", "reserve", "apply", "submit",
    ],
}


def heuristic_classification(prompt_text: str) -> dict:
    """
    Perform heuristic-based classification as a fallback.

    Args:
        prompt_text: The prompt text to classify.

    Returns:
        Classification dictionary.
    """
    text_lower = prompt_text.lower()

    # Determine intent type
    intent_scores = {intent: 0 for intent in INTENT_KEYWORDS}
    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                intent_scores[intent] += 1

    intent_type = max(intent_scores, key=intent_scores.get)
    if intent_scores[intent_type] == 0:
        intent_type = "informational"  # Default

    # Determine funnel stage
    funnel_scores = {stage: 0 for stage in FUNNEL_KEYWORDS}
    for stage, keywords in FUNNEL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                funnel_scores[stage] += 1

    funnel_stage = max(funnel_scores, key=funnel_scores.get)
    if funnel_scores[funnel_stage] == 0:
        funnel_stage = "awareness"  # Default

    # Determine query intent
    query_scores = {qi: 0 for qi in QUERY_INTENT_KEYWORDS}
    for qi, keywords in QUERY_INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                query_scores[qi] += 1

    query_intent = max(query_scores, key=query_scores.get)
    if query_scores[query_intent] == 0:
        query_intent = "Informational"

    # Calculate buying signal based on intent and funnel
    buying_signal_map = {
        ("informational", "awareness"): 0.15,
        ("informational", "consideration"): 0.35,
        ("informational", "purchase"): 0.50,
        ("evaluation", "awareness"): 0.35,
        ("evaluation", "consideration"): 0.60,
        ("evaluation", "purchase"): 0.75,
        ("decision", "awareness"): 0.50,
        ("decision", "consideration"): 0.70,
        ("decision", "purchase"): 0.90,
    }
    buying_signal = buying_signal_map.get((intent_type, funnel_stage), 0.40)

    # Calculate trust need based on complexity and stage
    trust_need_map = {
        "awareness": 0.30,
        "consideration": 0.60,
        "purchase": 0.80,
    }
    trust_need = trust_need_map.get(funnel_stage, 0.50)

    # Adjust trust need based on prompt complexity
    if len(prompt_text.split()) > 20:
        trust_need = min(trust_need + 0.1, 1.0)
    if "enterprise" in text_lower or "company" in text_lower:
        trust_need = min(trust_need + 0.15, 1.0)

    return {
        "intent_type": intent_type,
        "funnel_stage": funnel_stage,
        "buying_signal": round(buying_signal, 2),
        "trust_need": round(trust_need, 2),
        "query_intent": query_intent,
        "reasoning": "Heuristic classification based on keyword analysis",
    }
