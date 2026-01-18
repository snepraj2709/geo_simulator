"""
Tests for BeliefClassifier component.

Tests belief type classification from LLM response text.
"""

import pytest

from services.graph_builder.components.belief_classifier import (
    BeliefClassifier,
    BeliefClassification,
    BeliefAnalysis,
)
from services.graph_builder.schemas import (
    BeliefTypeEnum,
    PresenceStateEnum,
    IntentTypeEnum,
)


class TestBeliefClassifierBasicClassification:
    """Tests for basic belief type classification."""

    def test_classify_outcome_belief(self):
        """Test classification of outcome belief."""
        classifier = BeliefClassifier()

        context = "Using Acme Tool will help you achieve better results and reach your productivity goals faster."
        result = classifier.classify_belief(context, brand_name="Acme Tool")

        assert result is not None
        assert result.belief_type == BeliefTypeEnum.OUTCOME
        assert result.confidence > 0

    def test_classify_superiority_belief(self):
        """Test classification of superiority belief."""
        classifier = BeliefClassifier()

        context = "Acme Tool is the best option available and outperforms all competitors in this space."
        result = classifier.classify_belief(context, brand_name="Acme Tool")

        assert result is not None
        assert result.belief_type == BeliefTypeEnum.SUPERIORITY
        assert result.confidence > 0

    def test_classify_truth_belief(self):
        """Test classification of truth/fact belief."""
        classifier = BeliefClassifier()

        context = "Acme Tool is a proven solution with industry-standard features that have been validated."
        result = classifier.classify_belief(context, brand_name="Acme Tool")

        assert result is not None
        assert result.belief_type == BeliefTypeEnum.TRUTH
        assert result.confidence > 0

    def test_classify_transaction_belief(self):
        """Test classification of transaction belief."""
        classifier = BeliefClassifier()

        context = "The free tier of Acme Tool provides excellent value, and upgrading to premium is affordable."
        result = classifier.classify_belief(context, brand_name="Acme Tool")

        assert result is not None
        assert result.belief_type == BeliefTypeEnum.TRANSACTION
        assert result.confidence > 0

    def test_classify_identity_belief(self):
        """Test classification of identity belief."""
        classifier = BeliefClassifier()

        context = "Professionals like you trust Acme Tool because it aligns with enterprise-grade standards."
        result = classifier.classify_belief(context, brand_name="Acme Tool")

        assert result is not None
        assert result.belief_type == BeliefTypeEnum.IDENTITY
        assert result.confidence > 0

    def test_classify_social_proof_belief(self):
        """Test classification of social proof belief."""
        classifier = BeliefClassifier()

        context = "Acme Tool is used by thousands of companies including Fortune 500 enterprises and is widely trusted."
        result = classifier.classify_belief(context, brand_name="Acme Tool")

        assert result is not None
        assert result.belief_type == BeliefTypeEnum.SOCIAL_PROOF
        assert result.confidence > 0

    def test_no_belief_detected(self):
        """Test that no belief is detected for neutral text."""
        classifier = BeliefClassifier()

        context = "The tool exists in the market."
        result = classifier.classify_belief(context, brand_name="Acme")

        # Should return None or very low confidence
        assert result is None or result.confidence < 0.3


class TestBeliefClassifierContextModifiers:
    """Tests for context-aware belief classification."""

    def test_recommended_presence_boosts_outcome(self):
        """Test that recommended presence state boosts outcome belief confidence."""
        classifier = BeliefClassifier()

        context = "This tool will help you achieve your goals."

        # Without presence modifier
        result_neutral = classifier.classify_belief(context)

        # With recommended presence
        result_recommended = classifier.classify_belief(
            context,
            presence_state=PresenceStateEnum.RECOMMENDED
        )

        # Recommended presence should boost confidence for outcome beliefs
        if result_neutral and result_recommended:
            if result_neutral.belief_type == BeliefTypeEnum.OUTCOME:
                assert result_recommended.confidence >= result_neutral.confidence

    def test_evaluation_intent_boosts_superiority(self):
        """Test that evaluation intent boosts superiority belief detection."""
        classifier = BeliefClassifier()

        context = "This tool stands out as the best choice compared to alternatives."

        result_with_intent = classifier.classify_belief(
            context,
            intent_type=IntentTypeEnum.EVALUATION
        )

        assert result_with_intent is not None
        # Evaluation intent should favor superiority beliefs
        assert result_with_intent.belief_type == BeliefTypeEnum.SUPERIORITY

    def test_trusted_presence_boosts_truth(self):
        """Test that trusted presence boosts truth belief detection."""
        classifier = BeliefClassifier()

        context = "This is a proven and reliable solution."

        result = classifier.classify_belief(
            context,
            presence_state=PresenceStateEnum.TRUSTED
        )

        assert result is not None
        assert result.belief_type == BeliefTypeEnum.TRUTH


class TestBeliefClassifierMultipleBeliefs:
    """Tests for detecting multiple beliefs in text."""

    def test_classify_all_beliefs(self):
        """Test classifying all beliefs from text."""
        classifier = BeliefClassifier()

        context = """
        Acme Tool is the industry-leading solution that will help you achieve your goals.
        It's proven technology trusted by thousands of companies. The pricing is excellent value
        and perfect for professionals like you who need reliable tools.
        """

        results = classifier.classify_all_beliefs(context, brand_name="Acme Tool")

        assert len(results) > 0
        belief_types = [r.belief_type for r in results]
        # Should detect multiple belief types
        assert len(set(belief_types)) >= 2

    def test_classify_all_beliefs_with_threshold(self):
        """Test that low-confidence beliefs are filtered."""
        classifier = BeliefClassifier()

        context = "This tool might help with some tasks."

        results = classifier.classify_all_beliefs(
            context,
            min_confidence=0.5
        )

        # All returned results should meet threshold
        for result in results:
            assert result.confidence >= 0.5


class TestBeliefAnalysis:
    """Tests for comprehensive belief analysis."""

    def test_analyze_brand_beliefs_basic(self):
        """Test basic belief analysis."""
        classifier = BeliefClassifier()

        text = "Acme Tool is the best solution that will deliver great results for your team."

        analysis = classifier.analyze_brand_beliefs(text, brand_name="Acme Tool")

        assert isinstance(analysis, BeliefAnalysis)
        assert analysis.brand_name == "Acme Tool"
        assert analysis.primary_belief is not None
        assert len(analysis.all_beliefs) > 0

    def test_analyze_brand_beliefs_with_context(self):
        """Test belief analysis with context modifiers."""
        classifier = BeliefClassifier()

        text = "TestBrand outperforms competitors and is trusted by professionals."

        analysis = classifier.analyze_brand_beliefs(
            text,
            brand_name="TestBrand",
            presence_state=PresenceStateEnum.RECOMMENDED,
            intent_type=IntentTypeEnum.EVALUATION
        )

        assert analysis.primary_belief is not None
        assert analysis.primary_belief.confidence > 0

    def test_analyze_brand_beliefs_brand_not_found(self):
        """Test analysis when brand is not found in text."""
        classifier = BeliefClassifier()

        analysis = classifier.analyze_brand_beliefs("Some generic text", brand_name="NonexistentBrand")

        assert analysis.primary_belief is None
        assert len(analysis.all_beliefs) == 0


class TestBeliefClassificationDataclass:
    """Tests for BeliefClassification dataclass."""

    def test_belief_classification_creation(self):
        """Test creating BeliefClassification."""
        classification = BeliefClassification(
            belief_type=BeliefTypeEnum.OUTCOME,
            confidence=0.85,
            signals=["achieve", "goals"],
            context_snippet="will help achieve goals",
        )

        assert classification.belief_type == BeliefTypeEnum.OUTCOME
        assert classification.confidence == 0.85
        assert len(classification.signals) == 2
        assert classification.context_snippet is not None

    def test_belief_classification_default_signals(self):
        """Test BeliefClassification with default signals."""
        classification = BeliefClassification(
            belief_type=BeliefTypeEnum.TRUTH,
            confidence=0.7,
        )

        assert classification.signals == []
        assert classification.context_snippet is None


class TestBeliefAnalysisDataclass:
    """Tests for BeliefAnalysis dataclass."""

    def test_belief_analysis_creation(self):
        """Test creating BeliefAnalysis."""
        primary = BeliefClassification(
            belief_type=BeliefTypeEnum.OUTCOME,
            confidence=0.9,
        )
        secondary = BeliefClassification(
            belief_type=BeliefTypeEnum.SUPERIORITY,
            confidence=0.6,
        )

        analysis = BeliefAnalysis(
            brand_name="TestBrand",
            primary_belief=primary,
            all_beliefs=[primary, secondary],
            presence_state=PresenceStateEnum.RECOMMENDED,
            intent_type=IntentTypeEnum.EVALUATION,
        )

        assert analysis.brand_name == "TestBrand"
        assert analysis.primary_belief == primary
        assert len(analysis.all_beliefs) == 2
        assert analysis.presence_state == PresenceStateEnum.RECOMMENDED
        assert analysis.intent_type == IntentTypeEnum.EVALUATION

    def test_belief_analysis_defaults(self):
        """Test BeliefAnalysis with default values."""
        analysis = BeliefAnalysis(
            brand_name="TestBrand",
            primary_belief=None,
        )

        assert analysis.brand_name == "TestBrand"
        assert analysis.primary_belief is None
        assert len(analysis.all_beliefs) == 0
        assert analysis.presence_state is None
        assert analysis.intent_type is None


class TestBeliefTypePatterns:
    """Tests for specific belief type pattern recognition."""

    def test_outcome_patterns(self):
        """Test various outcome belief patterns."""
        classifier = BeliefClassifier()

        outcome_texts = [
            "You will achieve better results with this tool",
            "This helps accomplish your business goals",
            "Experience improved productivity and outcomes",
            "Get the benefits of automated workflows",
        ]

        for text in outcome_texts:
            result = classifier.classify_belief(text)
            assert result is not None, f"Failed to classify: {text}"
            assert result.belief_type == BeliefTypeEnum.OUTCOME, f"Wrong type for: {text}"

    def test_superiority_patterns(self):
        """Test various superiority belief patterns."""
        classifier = BeliefClassifier()

        superiority_texts = [
            "This is the best tool on the market",
            "Outperforms all competitors in speed",
            "The leading solution in the industry",
            "Superior to other options available",
        ]

        for text in superiority_texts:
            result = classifier.classify_belief(text)
            assert result is not None, f"Failed to classify: {text}"
            assert result.belief_type == BeliefTypeEnum.SUPERIORITY, f"Wrong type for: {text}"

    def test_truth_patterns(self):
        """Test various truth/fact belief patterns."""
        classifier = BeliefClassifier()

        truth_texts = [
            "This is a proven and reliable platform",
            "Industry-standard compliance is guaranteed",
            "Fact: it has 99.9% uptime guaranteed",
            "Validated by independent testing",
        ]

        for text in truth_texts:
            result = classifier.classify_belief(text)
            assert result is not None, f"Failed to classify: {text}"
            assert result.belief_type == BeliefTypeEnum.TRUTH, f"Wrong type for: {text}"

    def test_social_proof_patterns(self):
        """Test various social proof patterns."""
        classifier = BeliefClassifier()

        social_proof_texts = [
            "Trusted by thousands of companies worldwide",
            "Used by Fortune 500 enterprises",
            "Over 1 million users rely on this tool",
            "Companies like Google and Microsoft use it",
        ]

        for text in social_proof_texts:
            result = classifier.classify_belief(text)
            assert result is not None, f"Failed to classify: {text}"
            assert result.belief_type == BeliefTypeEnum.SOCIAL_PROOF, f"Wrong type for: {text}"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_context(self):
        """Test with empty context string."""
        classifier = BeliefClassifier()
        result = classifier.classify_belief("")
        assert result is None

    def test_whitespace_only(self):
        """Test with whitespace-only context."""
        classifier = BeliefClassifier()
        result = classifier.classify_belief("   \n\t  ")
        assert result is None

    def test_very_long_text(self):
        """Test with very long text."""
        classifier = BeliefClassifier()

        long_text = "This tool delivers great results. " * 100
        result = classifier.classify_belief(long_text)

        # Should still work with long text
        assert result is not None

    def test_special_characters(self):
        """Test with special characters in text."""
        classifier = BeliefClassifier()

        text = "This tool™ will help you achieve 100% of your goals! #1 rated @industry"
        result = classifier.classify_belief(text)

        # Should handle special chars gracefully
        assert result is not None

    def test_mixed_case_brand_name(self):
        """Test with mixed case brand name."""
        classifier = BeliefClassifier()

        text = "ACME TOOL will help you achieve your goals"
        result = classifier.classify_belief(text, brand_name="Acme Tool")

        assert result is not None

    def test_unicode_text(self):
        """Test with unicode characters."""
        classifier = BeliefClassifier()

        text = "This tool helps you achieve goals — it's the best™ solution"
        result = classifier.classify_belief(text)

        assert result is not None


class TestGetBeliefDistribution:
    """Tests for belief distribution calculation."""

    def test_get_belief_distribution_basic(self):
        """Test basic belief distribution calculation."""
        classifier = BeliefClassifier()

        classifications = [
            BeliefClassification(belief_type=BeliefTypeEnum.OUTCOME, confidence=0.8),
            BeliefClassification(belief_type=BeliefTypeEnum.SUPERIORITY, confidence=0.6),
            BeliefClassification(belief_type=BeliefTypeEnum.TRUTH, confidence=0.4),
        ]

        distribution = classifier.get_belief_distribution(classifications)

        assert "outcome" in distribution
        assert "superiority" in distribution
        assert "truth" in distribution
        # Total should be approximately 100%
        total = sum(distribution.values())
        assert 99.5 <= total <= 100.5

    def test_get_belief_distribution_empty(self):
        """Test distribution with empty classifications."""
        classifier = BeliefClassifier()

        distribution = classifier.get_belief_distribution([])

        assert distribution == {}

    def test_get_belief_distribution_single(self):
        """Test distribution with single belief."""
        classifier = BeliefClassifier()

        classifications = [
            BeliefClassification(belief_type=BeliefTypeEnum.SOCIAL_PROOF, confidence=0.9),
        ]

        distribution = classifier.get_belief_distribution(classifications)

        assert distribution["social_proof"] == 100.0
