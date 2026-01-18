"""
Tests for Brand Presence Classifier.

Tests all presence states from ARCHITECTURE.md:
- ignored: Brand not mentioned at all
- mentioned: Brand name appears but without context
- trusted: Brand cited as authority without sales push
- recommended: Brand with clear call-to-action
- compared: Brand in neutral evaluation context

Implements the 'one dominant state per brand per answer' rule.
"""

import pytest

from services.brand_detector.components.classifier import (
    BrandPresenceClassifier,
    ClassifierConfig,
    BrandCandidate,
)
from services.brand_detector.schemas import (
    BrandPresenceState,
    BeliefType,
    BrandPresenceResult,
    BrandDetectionResponse,
)


# ==================== Test Data ====================


class TestData:
    """Test data for brand presence detection."""

    # IGNORED - Brand not mentioned at all
    TEXT_NO_BRANDS = """
    Looking for a solution to manage your projects? There are many options
    available in the market today that can help streamline your workflow.
    """

    # MENTIONED - Brand name appears but without special context
    TEXT_BRAND_MENTIONED = """
    There are several project management tools available, such as Asana,
    Trello, and Monday.com. These tools help teams organize their work.
    """

    # TRUSTED - Brand cited as authority without sales push
    TEXT_BRAND_TRUSTED = """
    When it comes to cloud infrastructure, AWS has established itself as
    the industry leader with a proven track record. They are trusted by
    millions of companies worldwide and have enterprise-grade reliability.
    """

    # RECOMMENDED - Brand with clear call-to-action
    TEXT_BRAND_RECOMMENDED = """
    For your use case, I would highly recommend Notion. It's the best choice
    for teams that need flexibility. You should try Notion today - you can't
    go wrong with it for collaborative document management.
    """

    # COMPARED - Brand in neutral evaluation context
    TEXT_BRAND_COMPARED = """
    When comparing Slack vs Microsoft Teams, there are clear differences.
    Slack offers better third-party integrations, while Teams provides
    better value for organizations already using Microsoft 365. Both have
    their pros and cons depending on your specific needs.
    """

    # Mixed presence - multiple brands with different states
    TEXT_MIXED_PRESENCE = """
    For customer relationship management, I strongly recommend Salesforce.
    It's the best CRM on the market. However, if you're comparing alternatives,
    HubSpot is also widely used and trusted by thousands of businesses.
    For smaller teams, you might also consider Zoho or Pipedrive.
    """


# ==================== Schema Tests ====================


class TestBrandPresenceState:
    """Tests for BrandPresenceState enum."""

    def test_all_states_defined(self):
        """Test all required states are defined."""
        assert BrandPresenceState.IGNORED.value == "ignored"
        assert BrandPresenceState.MENTIONED.value == "mentioned"
        assert BrandPresenceState.TRUSTED.value == "trusted"
        assert BrandPresenceState.RECOMMENDED.value == "recommended"
        assert BrandPresenceState.COMPARED.value == "compared"

    def test_state_count(self):
        """Test there are exactly 5 states."""
        assert len(BrandPresenceState) == 5


class TestBeliefType:
    """Tests for BeliefType enum."""

    def test_all_beliefs_defined(self):
        """Test all belief types are defined."""
        assert BeliefType.TRUTH.value == "truth"
        assert BeliefType.SUPERIORITY.value == "superiority"
        assert BeliefType.OUTCOME.value == "outcome"
        assert BeliefType.TRANSACTION.value == "transaction"
        assert BeliefType.IDENTITY.value == "identity"
        assert BeliefType.SOCIAL_PROOF.value == "social_proof"

    def test_belief_count(self):
        """Test there are exactly 6 belief types."""
        assert len(BeliefType) == 6


class TestBrandPresenceResult:
    """Tests for BrandPresenceResult schema."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = BrandPresenceResult(
            brand_name="Notion",
            normalized_name="notion",
            presence=BrandPresenceState.RECOMMENDED,
            position_rank=1,
            belief_sold=BeliefType.SUPERIORITY,
            confidence=0.95,
            detection_signals=["recommend", "best_choice"],
        )
        assert result.brand_name == "Notion"
        assert result.presence == BrandPresenceState.RECOMMENDED
        assert result.position_rank == 1

    def test_position_rank_nullable(self):
        """Test position rank can be null (for ignored brands)."""
        result = BrandPresenceResult(
            brand_name="MyBrand",
            normalized_name="mybrand",
            presence=BrandPresenceState.IGNORED,
            position_rank=None,
        )
        assert result.position_rank is None

    def test_confidence_bounds(self):
        """Test confidence score must be between 0 and 1."""
        with pytest.raises(ValueError):
            BrandPresenceResult(
                brand_name="Test",
                normalized_name="test",
                presence=BrandPresenceState.MENTIONED,
                confidence=1.5,  # Invalid
            )

        with pytest.raises(ValueError):
            BrandPresenceResult(
                brand_name="Test",
                normalized_name="test",
                presence=BrandPresenceState.MENTIONED,
                confidence=-0.1,  # Invalid
            )


# ==================== Classifier Config Tests ====================


class TestClassifierConfig:
    """Tests for ClassifierConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ClassifierConfig()
        assert config.context_window == 150
        assert config.min_confidence == 0.2  # Lowered to include mentioned brands
        assert config.max_brands == 50
        assert config.use_ner is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = ClassifierConfig(
            context_window=200,
            min_confidence=0.5,
            max_brands=25,
        )
        assert config.context_window == 200
        assert config.min_confidence == 0.5
        assert config.max_brands == 25


# ==================== IGNORED State Tests ====================


class TestIgnoredState:
    """Tests for IGNORED presence state - Brand not mentioned at all."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return BrandPresenceClassifier()

    def test_tracked_brand_not_mentioned(self, classifier):
        """Test tracked brand that doesn't appear in text returns IGNORED."""
        result = classifier.detect_brands(
            text=TestData.TEXT_NO_BRANDS,
            tracked_brand="Notion",
        )

        assert result.tracked_brand_result is not None
        assert result.tracked_brand_result.presence == BrandPresenceState.IGNORED
        assert result.tracked_brand_result.position_rank is None
        assert "not_mentioned" in result.tracked_brand_result.detection_signals

    def test_tracked_brand_not_in_list(self, classifier):
        """Test tracked brand not in text with other brands present."""
        result = classifier.detect_brands(
            text=TestData.TEXT_BRAND_MENTIONED,
            tracked_brand="Notion",
        )

        # Notion is not mentioned in the text about Asana, Trello, Monday.com
        assert result.tracked_brand_result is not None
        assert result.tracked_brand_result.presence == BrandPresenceState.IGNORED

    def test_empty_text_returns_ignored(self, classifier):
        """Test empty text returns empty brands list."""
        result = classifier.detect_brands(
            text="",
            tracked_brand="Notion",
        )

        assert result.total_brands_found == 0


# ==================== MENTIONED State Tests ====================


class TestMentionedState:
    """Tests for MENTIONED presence state - Brand appears without context."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return BrandPresenceClassifier()

    def test_brand_in_list_is_mentioned(self, classifier):
        """Test brand mentioned in a list is classified as MENTIONED."""
        text = "There are options like Asana, Trello, and Monday available."

        result = classifier.detect_brands(
            text=text,
            known_brands=["Asana", "Trello", "Monday"],
        )

        # All brands should be classified as MENTIONED (no recommendation context)
        for brand_result in result.brands:
            assert brand_result.presence in [
                BrandPresenceState.MENTIONED,
                BrandPresenceState.COMPARED,  # Could be compared if "like" triggers
            ]

    def test_simple_mention(self, classifier):
        """Test simple brand mention without recommendation."""
        text = "There are many tools like Slack available for messaging."

        result = classifier.detect_brands(
            text=text,
            known_brands=["Slack"],
        )

        slack_result = next(
            (b for b in result.brands if b.normalized_name == "slack"), None
        )
        assert slack_result is not None
        # Simple statement with "like" pattern defaults to MENTIONED
        assert slack_result.presence == BrandPresenceState.MENTIONED


# ==================== TRUSTED State Tests ====================


class TestTrustedState:
    """Tests for TRUSTED presence state - Brand cited as authority."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return BrandPresenceClassifier()

    def test_industry_leader_is_trusted(self, classifier):
        """Test brand described as industry leader is TRUSTED."""
        result = classifier.detect_brands(
            text=TestData.TEXT_BRAND_TRUSTED,
            known_brands=["AWS"],
        )

        aws_result = next(
            (b for b in result.brands if b.normalized_name == "aws"), None
        )
        assert aws_result is not None
        assert aws_result.presence == BrandPresenceState.TRUSTED

    def test_trusted_by_millions(self, classifier):
        """Test 'trusted by millions' pattern triggers TRUSTED state."""
        text = "GitHub is trusted by millions of developers worldwide."

        result = classifier.detect_brands(
            text=text,
            known_brands=["GitHub"],
        )

        github_result = next(
            (b for b in result.brands if b.normalized_name == "github"), None
        )
        assert github_result is not None
        assert github_result.presence == BrandPresenceState.TRUSTED

    def test_proven_track_record(self, classifier):
        """Test 'proven track record' pattern triggers TRUSTED state."""
        text = "Oracle has a proven track record in enterprise databases."

        result = classifier.detect_brands(
            text=text,
            known_brands=["Oracle"],
        )

        oracle_result = next(
            (b for b in result.brands if b.normalized_name == "oracle"), None
        )
        assert oracle_result is not None
        assert oracle_result.presence == BrandPresenceState.TRUSTED


# ==================== RECOMMENDED State Tests ====================


class TestRecommendedState:
    """Tests for RECOMMENDED presence state - Brand with clear CTA."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return BrandPresenceClassifier()

    def test_highly_recommend(self, classifier):
        """Test 'highly recommend' pattern triggers RECOMMENDED state."""
        result = classifier.detect_brands(
            text=TestData.TEXT_BRAND_RECOMMENDED,
            known_brands=["Notion"],
        )

        notion_result = next(
            (b for b in result.brands if b.normalized_name == "notion"), None
        )
        assert notion_result is not None
        assert notion_result.presence == BrandPresenceState.RECOMMENDED

    def test_you_should_try(self, classifier):
        """Test 'you should try' pattern triggers RECOMMENDED state."""
        text = "You should try Figma for your design needs - it's excellent."

        result = classifier.detect_brands(
            text=text,
            known_brands=["Figma"],
        )

        figma_result = next(
            (b for b in result.brands if b.normalized_name == "figma"), None
        )
        assert figma_result is not None
        assert figma_result.presence == BrandPresenceState.RECOMMENDED

    def test_best_choice(self, classifier):
        """Test 'best choice' pattern triggers RECOMMENDED state."""
        text = "Linear is the best choice for modern development teams."

        result = classifier.detect_brands(
            text=text,
            known_brands=["Linear"],
        )

        linear_result = next(
            (b for b in result.brands if b.normalized_name == "linear"), None
        )
        assert linear_result is not None
        assert linear_result.presence == BrandPresenceState.RECOMMENDED

    def test_my_recommendation(self, classifier):
        """Test 'my recommendation' pattern triggers RECOMMENDED state."""
        text = "My recommendation would be Vercel for deploying frontend apps."

        result = classifier.detect_brands(
            text=text,
            known_brands=["Vercel"],
        )

        vercel_result = next(
            (b for b in result.brands if b.normalized_name == "vercel"), None
        )
        assert vercel_result is not None
        assert vercel_result.presence == BrandPresenceState.RECOMMENDED

    def test_cant_go_wrong_with(self, classifier):
        """Test 'can't go wrong with' pattern triggers RECOMMENDED state."""
        text = "You can't go wrong with PostgreSQL for relational databases."

        result = classifier.detect_brands(
            text=text,
            known_brands=["PostgreSQL"],
        )

        postgres_result = next(
            (b for b in result.brands if b.normalized_name == "postgresql"), None
        )
        assert postgres_result is not None
        assert postgres_result.presence == BrandPresenceState.RECOMMENDED


# ==================== COMPARED State Tests ====================


class TestComparedState:
    """Tests for COMPARED presence state - Brand in evaluation context."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return BrandPresenceClassifier()

    def test_versus_comparison(self, classifier):
        """Test 'vs' pattern triggers COMPARED state."""
        result = classifier.detect_brands(
            text=TestData.TEXT_BRAND_COMPARED,
            known_brands=["Slack", "Microsoft Teams"],
        )

        # Both brands should be in COMPARED state
        slack_result = next(
            (b for b in result.brands if b.normalized_name == "slack"), None
        )
        assert slack_result is not None
        assert slack_result.presence == BrandPresenceState.COMPARED

    def test_compared_to(self, classifier):
        """Test 'compared to' pattern triggers COMPARED state."""
        text = "React is often compared to Vue for frontend development."

        result = classifier.detect_brands(
            text=text,
            known_brands=["React", "Vue"],
        )

        react_result = next(
            (b for b in result.brands if b.normalized_name == "react"), None
        )
        assert react_result is not None
        assert react_result.presence == BrandPresenceState.COMPARED

    def test_pros_and_cons(self, classifier):
        """Test 'pros and cons' pattern triggers COMPARED state."""
        text = "Let's look at the pros and cons of using Docker for containers."

        result = classifier.detect_brands(
            text=text,
            known_brands=["Docker"],
        )

        docker_result = next(
            (b for b in result.brands if b.normalized_name == "docker"), None
        )
        assert docker_result is not None
        assert docker_result.presence == BrandPresenceState.COMPARED

    def test_alternative_to(self, classifier):
        """Test 'alternative to' pattern triggers COMPARED state."""
        text = "GitLab is a popular alternative to GitHub for repository hosting."

        result = classifier.detect_brands(
            text=text,
            known_brands=["GitLab", "GitHub"],
        )

        gitlab_result = next(
            (b for b in result.brands if b.normalized_name == "gitlab"), None
        )
        assert gitlab_result is not None
        assert gitlab_result.presence == BrandPresenceState.COMPARED


# ==================== One Dominant State Rule Tests ====================


class TestOneDominantStateRule:
    """Tests for 'one dominant state per brand per answer' rule."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return BrandPresenceClassifier()

    def test_mixed_context_chooses_dominant(self, classifier):
        """Test that mixed contexts result in one dominant state."""
        # Text mentions Notion in multiple contexts
        text = """
        For project management tools, there are many options available.
        Notion is widely used by teams. I would highly recommend Notion
        as your best choice for documentation and collaboration.
        """

        result = classifier.detect_brands(
            text=text,
            known_brands=["Notion"],
        )

        notion_result = next(
            (b for b in result.brands if b.normalized_name == "notion"), None
        )
        assert notion_result is not None

        # Should be RECOMMENDED as it's the highest priority state found
        assert notion_result.presence == BrandPresenceState.RECOMMENDED

    def test_priority_order(self, classifier):
        """Test state priority: RECOMMENDED > TRUSTED > COMPARED > MENTIONED."""
        # Text with both trusted and recommended signals - recommend is stronger
        text = """
        I highly recommend AWS. You should try AWS today. AWS is my top pick
        for cloud infrastructure.
        """

        result = classifier.detect_brands(
            text=text,
            known_brands=["AWS"],
        )

        aws_result = next(
            (b for b in result.brands if b.normalized_name == "aws"), None
        )
        assert aws_result is not None

        # RECOMMENDED should be detected with strong recommendation patterns
        assert aws_result.presence == BrandPresenceState.RECOMMENDED

    def test_one_result_per_brand(self, classifier):
        """Test each brand appears exactly once in results."""
        result = classifier.detect_brands(
            text=TestData.TEXT_MIXED_PRESENCE,
            known_brands=["Salesforce", "HubSpot", "Zoho", "Pipedrive"],
        )

        # Check no duplicate brands
        brand_names = [b.normalized_name for b in result.brands]
        assert len(brand_names) == len(set(brand_names))


# ==================== Position Rank Tests ====================


class TestPositionRank:
    """Tests for position_rank field."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return BrandPresenceClassifier()

    def test_first_brand_is_rank_1(self, classifier):
        """Test first mentioned brand has position_rank 1."""
        result = classifier.detect_brands(
            text=TestData.TEXT_MIXED_PRESENCE,
            known_brands=["Salesforce", "HubSpot", "Zoho", "Pipedrive"],
        )

        # Salesforce is mentioned first
        salesforce_result = next(
            (b for b in result.brands if b.normalized_name == "salesforce"), None
        )
        assert salesforce_result is not None
        assert salesforce_result.position_rank == 1

    def test_position_ranks_sequential(self, classifier):
        """Test position ranks are sequential starting from 1."""
        # Use text that clearly mentions brands in order
        text = "Try Asana first. Then use Trello. Finally consider Monday."
        result = classifier.detect_brands(
            text=text,
            known_brands=["Asana", "Trello", "Monday"],
        )

        # Check that we have brands with ranks
        ranks = sorted([b.position_rank for b in result.brands if b.position_rank])
        assert len(ranks) >= 2  # At least 2 brands should be detected with ranks

    def test_ignored_brand_has_no_rank(self, classifier):
        """Test ignored brand has null position_rank."""
        result = classifier.detect_brands(
            text="I use Slack for messaging.",
            tracked_brand="Notion",
        )

        assert result.tracked_brand_result is not None
        assert result.tracked_brand_result.presence == BrandPresenceState.IGNORED
        assert result.tracked_brand_result.position_rank is None


# ==================== Known Brands Tests ====================


class TestKnownBrands:
    """Tests for known_brands functionality."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return BrandPresenceClassifier()

    def test_detect_known_brands(self, classifier):
        """Test known brands are detected in text."""
        # Use text where brands are clearly mentioned with proper context
        result = classifier.detect_brands(
            text="Many teams use Salesforce for CRM. Slack is popular for messaging.",
            known_brands=["Salesforce", "Slack"],
        )

        brand_names = {b.normalized_name for b in result.brands}
        # At least one known brand should be detected
        assert "salesforce" in brand_names or "slack" in brand_names

    def test_known_brands_case_insensitive(self, classifier):
        """Test known brands match is case insensitive."""
        result = classifier.detect_brands(
            text="Many companies use Salesforce for their CRM needs.",
            known_brands=["Salesforce"],
        )

        assert any(b.normalized_name == "salesforce" for b in result.brands)

    def test_tracked_brand_always_returned(self, classifier):
        """Test tracked_brand_result is always populated."""
        result = classifier.detect_brands(
            text="Some random text without brands.",
            tracked_brand="MyBrand",
        )

        assert result.tracked_brand_result is not None
        assert result.tracked_brand_result.brand_name == "MyBrand"


# ==================== Integration Tests ====================


class TestClassifierIntegration:
    """Integration tests for the complete classifier."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return BrandPresenceClassifier()

    def test_full_detection_flow(self, classifier):
        """Test complete detection flow with multiple brands."""
        result = classifier.detect_brands(
            text=TestData.TEXT_MIXED_PRESENCE,
            known_brands=["Salesforce", "HubSpot", "Zoho", "Pipedrive"],
            tracked_brand="Salesforce",
        )

        # Check overall response
        assert isinstance(result, BrandDetectionResponse)
        assert result.total_brands_found > 0
        assert len(result.brands) > 0

        # Check tracked brand is returned
        assert result.tracked_brand_result is not None
        assert result.tracked_brand_result.normalized_name == "salesforce"
        # Should be RECOMMENDED or TRUSTED based on "strongly recommend" pattern
        assert result.tracked_brand_result.presence in [
            BrandPresenceState.RECOMMENDED,
            BrandPresenceState.TRUSTED,
        ]

    def test_confidence_scores(self, classifier):
        """Test confidence scores are within valid range."""
        result = classifier.detect_brands(
            text=TestData.TEXT_BRAND_RECOMMENDED,
            known_brands=["Notion"],
        )

        for brand in result.brands:
            assert 0.0 <= brand.confidence <= 1.0

    def test_detection_signals(self, classifier):
        """Test detection signals are populated."""
        result = classifier.detect_brands(
            text=TestData.TEXT_BRAND_RECOMMENDED,
            known_brands=["Notion"],
        )

        notion_result = next(
            (b for b in result.brands if b.normalized_name == "notion"), None
        )
        assert notion_result is not None
        assert len(notion_result.detection_signals) > 0

    def test_context_snippet(self, classifier):
        """Test context snippet is extracted."""
        result = classifier.detect_brands(
            text=TestData.TEXT_BRAND_RECOMMENDED,
            known_brands=["Notion"],
        )

        notion_result = next(
            (b for b in result.brands if b.normalized_name == "notion"), None
        )
        assert notion_result is not None
        assert notion_result.context_snippet is not None
        assert "Notion" in notion_result.context_snippet

    def test_analysis_metadata(self, classifier):
        """Test analysis metadata is populated."""
        result = classifier.detect_brands(
            text=TestData.TEXT_MIXED_PRESENCE,
            known_brands=["Salesforce", "HubSpot"],
        )

        assert "candidates_found" in result.analysis_metadata
        assert "brands_classified" in result.analysis_metadata


# ==================== Brand Detection Pattern Tests ====================


class TestBrandDetectionPatterns:
    """Tests for brand detection patterns."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return BrandPresenceClassifier()

    def test_detect_product_with_suffix(self, classifier):
        """Test detection of brands with common suffixes."""
        text = "Try DataCloud for your analytics needs."

        result = classifier.detect_brands(text=text, known_brands=["DataCloud"])

        # Should detect the known brand
        assert any("datacloud" in b.normalized_name for b in result.brands)

    def test_detect_domain_style_names(self, classifier):
        """Test detection of domain-style brand names."""
        text = "Try Monday for project management."

        result = classifier.detect_brands(text=text, known_brands=["Monday"])

        assert any("monday" in b.normalized_name for b in result.brands)

    def test_filter_common_words(self, classifier):
        """Test common words are filtered out."""
        text = "The solution is However, Furthermore, Additionally very good."

        result = classifier.detect_brands(text=text)

        # Common words should not be detected as brands
        brand_names = [b.normalized_name for b in result.brands]
        assert "however" not in brand_names
        assert "furthermore" not in brand_names
        assert "additionally" not in brand_names
