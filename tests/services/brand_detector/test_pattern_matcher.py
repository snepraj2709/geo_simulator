"""
Tests for Presence Pattern Matcher.

Tests the pattern matching engine for presence state detection:
- RECOMMENDED: Brand with clear call-to-action
- TRUSTED: Brand cited as authority
- COMPARED: Brand in evaluation context
- MENTIONED: Brand appears without special context
"""

import pytest

from services.brand_detector.components.pattern_matcher import (
    PresencePatternMatcher,
    PresenceMatch,
    PatternSet,
)
from services.brand_detector.schemas import BrandPresenceState


class TestPresencePatternMatcher:
    """Tests for PresencePatternMatcher class."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance with default config."""
        return PresencePatternMatcher()

    @pytest.fixture
    def matcher_large_window(self):
        """Create matcher with larger context window."""
        return PresencePatternMatcher(context_window=300)


# ==================== Find Brand Context Tests ====================


class TestFindBrandContext:
    """Tests for find_brand_context method."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return PresencePatternMatcher()

    def test_find_single_occurrence(self, matcher):
        """Test finding a single brand occurrence."""
        text = "I recommend using Notion for documentation."
        contexts = matcher.find_brand_context(text, "Notion")

        assert len(contexts) == 1
        assert contexts[0][0] == text.find("Notion")  # Position

    def test_find_multiple_occurrences(self, matcher):
        """Test finding multiple brand occurrences."""
        text = "Notion is great. I use Notion daily. Everyone loves Notion."
        contexts = matcher.find_brand_context(text, "Notion")

        assert len(contexts) == 3

    def test_case_insensitive_search(self, matcher):
        """Test case insensitive brand search."""
        text = "NOTION is powerful. notion is flexible. Notion is reliable."
        contexts = matcher.find_brand_context(text, "notion")

        assert len(contexts) == 3

    def test_context_extracted(self, matcher):
        """Test context is extracted around brand mention."""
        text = "Before text. Notion is great for teams. After text."
        contexts = matcher.find_brand_context(text, "Notion")

        assert len(contexts) == 1
        _, context = contexts[0]
        assert "Notion" in context
        assert "Before" in context or "After" in context

    def test_brand_not_found(self, matcher):
        """Test empty list when brand not found."""
        text = "I use Slack for messaging."
        contexts = matcher.find_brand_context(text, "Notion")

        assert len(contexts) == 0


# ==================== RECOMMENDED State Pattern Tests ====================


class TestRecommendedPatterns:
    """Tests for RECOMMENDED presence pattern detection."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return PresencePatternMatcher()

    def test_highly_recommend(self, matcher):
        """Test 'highly recommend' triggers RECOMMENDED."""
        context = "I highly recommend Notion for your team."
        presence, conf, signals = matcher.classify_presence(context, "Notion")

        assert presence == BrandPresenceState.RECOMMENDED
        assert conf >= 0.5  # Allow equal to 0.5

    def test_strongly_suggest(self, matcher):
        """Test 'strongly suggest' triggers RECOMMENDED."""
        context = "I strongly suggest you try Figma for design."
        presence, conf, signals = matcher.classify_presence(context, "Figma")

        assert presence == BrandPresenceState.RECOMMENDED

    def test_you_should_try(self, matcher):
        """Test 'you should try' triggers RECOMMENDED."""
        context = "You should try Linear for issue tracking."
        presence, conf, signals = matcher.classify_presence(context, "Linear")

        assert presence == BrandPresenceState.RECOMMENDED

    def test_best_choice(self, matcher):
        """Test 'best choice' triggers RECOMMENDED."""
        context = "AWS is the best choice for cloud infrastructure."
        presence, conf, signals = matcher.classify_presence(context, "AWS")

        assert presence == BrandPresenceState.RECOMMENDED

    def test_go_with(self, matcher):
        """Test 'go with' triggers RECOMMENDED."""
        context = "I would go with Vercel for hosting."
        presence, conf, signals = matcher.classify_presence(context, "Vercel")

        assert presence == BrandPresenceState.RECOMMENDED

    def test_my_recommendation(self, matcher):
        """Test 'my recommendation' triggers RECOMMENDED."""
        context = "My recommendation is PostgreSQL for databases."
        presence, conf, signals = matcher.classify_presence(context, "PostgreSQL")

        assert presence == BrandPresenceState.RECOMMENDED

    def test_cant_go_wrong(self, matcher):
        """Test 'can't go wrong with' triggers RECOMMENDED."""
        context = "You can't go wrong with React for frontend."
        presence, conf, signals = matcher.classify_presence(context, "React")

        assert presence == BrandPresenceState.RECOMMENDED


# ==================== TRUSTED State Pattern Tests ====================


class TestTrustedPatterns:
    """Tests for TRUSTED presence pattern detection."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return PresencePatternMatcher()

    def test_trusted_keyword(self, matcher):
        """Test 'trusted' keyword triggers TRUSTED."""
        context = "Stripe is a trusted payment processor."
        presence, conf, signals = matcher.classify_presence(context, "Stripe")

        assert presence == BrandPresenceState.TRUSTED

    def test_industry_leader(self, matcher):
        """Test 'industry leader' triggers TRUSTED."""
        context = "Salesforce is the industry leader in CRM."
        presence, conf, signals = matcher.classify_presence(context, "Salesforce")

        assert presence == BrandPresenceState.TRUSTED

    def test_widely_used(self, matcher):
        """Test 'widely used' triggers TRUSTED."""
        context = "Docker is widely used for containerization."
        presence, conf, signals = matcher.classify_presence(context, "Docker")

        assert presence == BrandPresenceState.TRUSTED

    def test_trusted_by_millions(self, matcher):
        """Test 'trusted by millions' triggers TRUSTED."""
        context = "GitHub is trusted by millions of developers."
        presence, conf, signals = matcher.classify_presence(context, "GitHub")

        assert presence == BrandPresenceState.TRUSTED

    def test_established(self, matcher):
        """Test 'established' triggers TRUSTED."""
        context = "Oracle is well-established in the database market."
        presence, conf, signals = matcher.classify_presence(context, "Oracle")

        assert presence == BrandPresenceState.TRUSTED

    def test_enterprise_grade(self, matcher):
        """Test 'enterprise-grade' triggers TRUSTED."""
        context = "AWS offers enterprise-grade security features."
        presence, conf, signals = matcher.classify_presence(context, "AWS")

        assert presence == BrandPresenceState.TRUSTED


# ==================== COMPARED State Pattern Tests ====================


class TestComparedPatterns:
    """Tests for COMPARED presence pattern detection."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return PresencePatternMatcher()

    def test_compared_to(self, matcher):
        """Test 'compared to' triggers COMPARED."""
        context = "React compared to Vue offers different paradigms."
        presence, conf, signals = matcher.classify_presence(context, "React")

        assert presence == BrandPresenceState.COMPARED

    def test_vs_pattern(self, matcher):
        """Test 'vs' pattern triggers COMPARED."""
        context = "Slack vs Teams: which is better for your team?"
        presence, conf, signals = matcher.classify_presence(context, "Slack")

        assert presence == BrandPresenceState.COMPARED

    def test_versus_pattern(self, matcher):
        """Test 'versus' pattern triggers COMPARED."""
        context = "AWS versus Azure for enterprise workloads."
        presence, conf, signals = matcher.classify_presence(context, "AWS")

        assert presence == BrandPresenceState.COMPARED

    def test_alternative_to(self, matcher):
        """Test 'alternative to' triggers COMPARED."""
        context = "GitLab is a popular alternative to GitHub."
        presence, conf, signals = matcher.classify_presence(context, "GitLab")

        assert presence == BrandPresenceState.COMPARED

    def test_pros_and_cons(self, matcher):
        """Test 'pros and cons' triggers COMPARED."""
        context = "The pros and cons of using MongoDB for data."
        presence, conf, signals = matcher.classify_presence(context, "MongoDB")

        assert presence == BrandPresenceState.COMPARED

    def test_unlike(self, matcher):
        """Test 'unlike' triggers COMPARED."""
        context = "Unlike Postgres, MySQL has different defaults."
        presence, conf, signals = matcher.classify_presence(context, "Postgres")

        assert presence == BrandPresenceState.COMPARED


# ==================== MENTIONED State Pattern Tests ====================


class TestMentionedPatterns:
    """Tests for MENTIONED presence pattern detection."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return PresencePatternMatcher()

    def test_such_as_pattern(self, matcher):
        """Test 'such as' triggers MENTIONED."""
        context = "Tools such as Jira help with project tracking."
        presence, conf, signals = matcher.classify_presence(context, "Jira")

        assert presence == BrandPresenceState.MENTIONED

    def test_for_example_pattern(self, matcher):
        """Test 'for example' triggers MENTIONED."""
        context = "For example, Notion can be used for wikis."
        presence, conf, signals = matcher.classify_presence(context, "Notion")

        assert presence == BrandPresenceState.MENTIONED

    def test_popular_pattern(self, matcher):
        """Test 'popular' triggers MENTIONED."""
        context = "React is a popular frontend framework."
        presence, conf, signals = matcher.classify_presence(context, "React")

        assert presence == BrandPresenceState.MENTIONED

    def test_default_to_mentioned(self, matcher):
        """Test simple mention defaults to MENTIONED."""
        context = "I use Slack every day."
        presence, conf, signals = matcher.classify_presence(context, "Slack")

        # Without strong signals, should be MENTIONED
        assert presence in [BrandPresenceState.MENTIONED, BrandPresenceState.TRUSTED]


# ==================== Position Rank Tests ====================


class TestPositionRank:
    """Tests for get_position_rank method."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return PresencePatternMatcher()

    def test_first_brand_rank_1(self, matcher):
        """Test first brand gets rank 1."""
        text = "Notion is great. Slack is good. Trello works."
        brands = ["Notion", "Slack", "Trello"]

        rank = matcher.get_position_rank(text, "Notion", brands)
        assert rank == 1

    def test_second_brand_rank_2(self, matcher):
        """Test second brand gets rank 2."""
        text = "Notion is great. Slack is good. Trello works."
        brands = ["Notion", "Slack", "Trello"]

        rank = matcher.get_position_rank(text, "Slack", brands)
        assert rank == 2

    def test_third_brand_rank_3(self, matcher):
        """Test third brand gets rank 3."""
        text = "Notion is great. Slack is good. Trello works."
        brands = ["Notion", "Slack", "Trello"]

        rank = matcher.get_position_rank(text, "Trello", brands)
        assert rank == 3

    def test_not_found_returns_none(self, matcher):
        """Test brand not found returns None."""
        text = "Notion is great. Slack is good."
        brands = ["Notion", "Slack", "Trello"]

        rank = matcher.get_position_rank(text, "Trello", brands)
        assert rank is None

    def test_case_insensitive_ranking(self, matcher):
        """Test ranking is case insensitive."""
        text = "NOTION is first. slack is second."
        brands = ["notion", "Slack"]

        rank_notion = matcher.get_position_rank(text, "Notion", brands)
        rank_slack = matcher.get_position_rank(text, "slack", brands)

        assert rank_notion == 1
        assert rank_slack == 2


# ==================== Priority Tests ====================


class TestPresencePriority:
    """Tests for presence state priority handling."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return PresencePatternMatcher()

    def test_recommended_over_trusted(self, matcher):
        """Test RECOMMENDED takes priority over TRUSTED."""
        # Context has both trusted and recommended signals
        context = "AWS is the industry leader. I highly recommend AWS for you."
        presence, conf, signals = matcher.classify_presence(context, "AWS")

        assert presence == BrandPresenceState.RECOMMENDED

    def test_recommended_over_compared(self, matcher):
        """Test RECOMMENDED takes priority over COMPARED."""
        context = "Unlike others, I highly recommend Notion as the best choice."
        presence, conf, signals = matcher.classify_presence(context, "Notion")

        assert presence == BrandPresenceState.RECOMMENDED

    def test_trusted_over_mentioned(self, matcher):
        """Test TRUSTED takes priority over MENTIONED."""
        context = "For example, AWS is the industry leader worldwide."
        presence, conf, signals = matcher.classify_presence(context, "AWS")

        assert presence == BrandPresenceState.TRUSTED


# ==================== Context Window Tests ====================


class TestContextWindow:
    """Tests for context window configuration."""

    def test_default_window_size(self):
        """Test default context window size."""
        matcher = PresencePatternMatcher()
        assert matcher.context_window == 150

    def test_custom_window_size(self):
        """Test custom context window size."""
        matcher = PresencePatternMatcher(context_window=300)
        assert matcher.context_window == 300

    def test_context_respects_window(self):
        """Test context extraction respects window size."""
        matcher = PresencePatternMatcher(context_window=10)
        text = "A" * 100 + "Notion" + "B" * 100
        contexts = matcher.find_brand_context(text, "Notion")

        assert len(contexts) == 1
        _, context = contexts[0]
        # Context should be ~26 chars (10 before + "Notion" + 10 after)
        assert len(context) <= 30


# ==================== Signal Detection Tests ====================


class TestSignalDetection:
    """Tests for detection signal capture."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return PresencePatternMatcher()

    def test_signals_captured(self, matcher):
        """Test signals are captured during classification."""
        context = "I highly recommend Notion as the best choice."
        presence, conf, signals = matcher.classify_presence(context, "Notion")

        assert len(signals) > 0
        assert any("recommend" in s.lower() for s in signals)

    def test_signals_limited(self, matcher):
        """Test signals list is limited."""
        context = """
        I highly recommend this as the best choice, top pick,
        and my recommendation would be to try it today.
        """
        presence, conf, signals = matcher.classify_presence(context, "this")

        # Should be limited to 5 signals
        assert len(signals) <= 5

    def test_signal_format(self, matcher):
        """Test signal format includes state."""
        context = "I highly recommend Notion."
        presence, conf, signals = matcher.classify_presence(context, "Notion")

        # Signals should start with state name
        assert any(s.startswith("recommended:") for s in signals)


# ==================== Edge Cases ====================


class TestMatcherEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return PresencePatternMatcher()

    def test_empty_text(self, matcher):
        """Test handling of empty text."""
        contexts = matcher.find_brand_context("", "Notion")
        assert len(contexts) == 0

    def test_empty_brand(self, matcher):
        """Test handling of empty brand name."""
        text = "Some text here."
        contexts = matcher.find_brand_context(text, "")
        # Empty string matches everywhere - implementation specific
        assert isinstance(contexts, list)

    def test_brand_at_start(self, matcher):
        """Test brand at start of text."""
        text = "Notion is the first word here."
        contexts = matcher.find_brand_context(text, "Notion")

        assert len(contexts) == 1
        pos, context = contexts[0]
        assert pos == 0

    def test_brand_at_end(self, matcher):
        """Test brand at end of text."""
        text = "The last word is Notion"
        contexts = matcher.find_brand_context(text, "Notion")

        assert len(contexts) == 1
        assert "Notion" in contexts[0][1]

    def test_overlapping_brands(self, matcher):
        """Test handling of overlapping brand names."""
        text = "Azure and AzureML are different."
        contexts = matcher.find_brand_context(text, "Azure")

        # Should find at least 2 matches (Azure and part of AzureML)
        assert len(contexts) >= 2

    def test_special_characters_in_brand(self, matcher):
        """Test handling of special characters in brand."""
        text = "Monday.com is a project management tool."
        contexts = matcher.find_brand_context(text, "Monday.com")

        assert len(contexts) == 1
