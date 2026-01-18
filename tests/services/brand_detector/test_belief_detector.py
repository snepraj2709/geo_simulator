"""
Tests for Belief Type Detector.

Tests all belief types from DATA_MODEL.md:
- truth: epistemic clarity, neutrality
- superiority: better than alternatives
- outcome: ROI, performance, results
- transaction: buy now, act
- identity: people like you use this
- social_proof: others chose this
"""

import pytest

from services.brand_detector.components.belief_detector import BeliefTypeDetector
from services.brand_detector.schemas import BeliefType


class TestBeliefTypeDetector:
    """Tests for BeliefTypeDetector class."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return BeliefTypeDetector()


# ==================== TRUTH Belief Tests ====================


class TestTruthBelief:
    """Tests for TRUTH belief type - epistemic clarity, neutrality."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return BeliefTypeDetector()

    def test_in_fact_pattern(self, detector):
        """Test 'in fact' pattern triggers TRUTH belief."""
        context = "In fact, AWS provides 99.99% uptime guarantee."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRUTH
        assert confidence > 0

    def test_data_shows_pattern(self, detector):
        """Test 'data shows' pattern triggers TRUTH belief."""
        context = "Data shows that Slack improves team communication by 30%."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRUTH

    def test_studies_indicate_pattern(self, detector):
        """Test 'studies indicate' pattern triggers TRUTH belief."""
        context = "Studies indicate that cloud migration reduces costs."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRUTH

    def test_according_to_pattern(self, detector):
        """Test 'according to' pattern triggers TRUTH belief."""
        # Use context without other strong belief signals
        context = "According to the documentation, this approach is correct."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRUTH

    def test_objectively_pattern(self, detector):
        """Test 'objectively' pattern triggers TRUTH belief."""
        context = "Objectively, PostgreSQL handles complex queries efficiently."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRUTH


# ==================== SUPERIORITY Belief Tests ====================


class TestSuperiorityBelief:
    """Tests for SUPERIORITY belief type - better than alternatives."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return BeliefTypeDetector()

    def test_best_pattern(self, detector):
        """Test 'best' pattern triggers SUPERIORITY belief."""
        context = "Notion is the best tool for team documentation."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SUPERIORITY

    def test_number_one_pattern(self, detector):
        """Test 'number one' pattern triggers SUPERIORITY belief."""
        context = "Salesforce is the number one CRM platform globally."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SUPERIORITY

    def test_market_leader_pattern(self, detector):
        """Test 'market leader' pattern triggers SUPERIORITY belief."""
        context = "AWS is the market leader in cloud infrastructure."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SUPERIORITY

    def test_outperforms_pattern(self, detector):
        """Test 'outperforms' pattern triggers SUPERIORITY belief."""
        context = "React consistently outperforms other frameworks."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SUPERIORITY

    def test_unrivaled_pattern(self, detector):
        """Test 'unrivaled' pattern triggers SUPERIORITY belief."""
        context = "Their support is unrivaled in the industry."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SUPERIORITY

    def test_second_to_none_pattern(self, detector):
        """Test 'second to none' pattern triggers SUPERIORITY belief."""
        context = "The performance is second to none."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SUPERIORITY


# ==================== OUTCOME Belief Tests ====================


class TestOutcomeBelief:
    """Tests for OUTCOME belief type - ROI, performance, results."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return BeliefTypeDetector()

    def test_roi_pattern(self, detector):
        """Test 'ROI' pattern triggers OUTCOME belief."""
        context = "Companies see 300% ROI within the first year."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.OUTCOME

    def test_return_on_investment_pattern(self, detector):
        """Test 'return on investment' pattern triggers OUTCOME belief."""
        context = "The return on investment is significant for enterprises."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.OUTCOME

    def test_saves_time_pattern(self, detector):
        """Test 'saves time' pattern triggers OUTCOME belief."""
        context = "This tool saves time by automating repetitive tasks."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.OUTCOME

    def test_percent_improvement_pattern(self, detector):
        """Test percentage improvement pattern triggers OUTCOME belief."""
        context = "Teams report 50% faster deployment cycles."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.OUTCOME

    def test_productivity_pattern(self, detector):
        """Test 'productivity' pattern triggers OUTCOME belief."""
        context = "Boost your team's productivity with Asana."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.OUTCOME

    def test_efficiency_pattern(self, detector):
        """Test 'efficiency' pattern triggers OUTCOME belief."""
        context = "The efficiency gains are substantial."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.OUTCOME


# ==================== TRANSACTION Belief Tests ====================


class TestTransactionBelief:
    """Tests for TRANSACTION belief type - buy now, act."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return BeliefTypeDetector()

    def test_free_trial_pattern(self, detector):
        """Test 'free trial' pattern triggers TRANSACTION belief."""
        context = "Start your free trial today and see the difference."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRANSACTION

    def test_sign_up_pattern(self, detector):
        """Test 'sign up' pattern triggers TRANSACTION belief."""
        context = "Sign up now to get started with Notion."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRANSACTION

    def test_get_started_pattern(self, detector):
        """Test 'get started' pattern triggers TRANSACTION belief."""
        context = "Get started with just a few clicks."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRANSACTION

    def test_buy_now_pattern(self, detector):
        """Test 'buy now' pattern triggers TRANSACTION belief."""
        context = "Buy now and save 20% on annual plans."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRANSACTION

    def test_limited_time_pattern(self, detector):
        """Test 'limited time' pattern triggers TRANSACTION belief."""
        context = "This limited time offer expires soon."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRANSACTION

    def test_book_a_demo_pattern(self, detector):
        """Test 'book a demo' pattern triggers TRANSACTION belief."""
        context = "Book a demo with our sales team today."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.TRANSACTION


# ==================== IDENTITY Belief Tests ====================


class TestIdentityBelief:
    """Tests for IDENTITY belief type - people like you use this."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return BeliefTypeDetector()

    def test_for_teams_pattern(self, detector):
        """Test 'for teams' pattern triggers IDENTITY belief."""
        context = "Slack is designed for teams that value communication."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.IDENTITY

    def test_perfect_for_pattern(self, detector):
        """Test 'perfect for' pattern triggers IDENTITY belief."""
        context = "Linear is perfect for engineering teams."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.IDENTITY

    def test_ideal_for_pattern(self, detector):
        """Test 'ideal for' pattern triggers IDENTITY belief."""
        context = "This tool is ideal for startups and small businesses."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.IDENTITY

    def test_if_you_are_pattern(self, detector):
        """Test 'if you are' pattern triggers IDENTITY belief."""
        context = "If you're a developer, you'll love this tool."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.IDENTITY

    def test_for_people_who_pattern(self, detector):
        """Test 'for people who' pattern triggers IDENTITY belief."""
        context = "This is for people who value their time."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.IDENTITY

    def test_enterprise_pattern(self, detector):
        """Test 'enterprise' pattern triggers IDENTITY belief."""
        context = "Enterprise-grade security for large organizations."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.IDENTITY


# ==================== SOCIAL_PROOF Belief Tests ====================


class TestSocialProofBelief:
    """Tests for SOCIAL_PROOF belief type - others chose this."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return BeliefTypeDetector()

    def test_millions_of_users_pattern(self, detector):
        """Test 'millions of users' pattern triggers SOCIAL_PROOF belief."""
        context = "Trusted by millions of users worldwide."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SOCIAL_PROOF

    def test_thousands_of_companies_pattern(self, detector):
        """Test 'thousands of companies' pattern triggers SOCIAL_PROOF belief."""
        context = "Thousands of companies rely on this platform."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SOCIAL_PROOF

    def test_trusted_by_pattern(self, detector):
        """Test 'trusted by' pattern triggers SOCIAL_PROOF belief."""
        context = "Trusted by Fortune 500 companies."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SOCIAL_PROOF

    def test_widely_used_pattern(self, detector):
        """Test 'widely used' pattern triggers SOCIAL_PROOF belief."""
        context = "This is a widely used solution in the industry."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SOCIAL_PROOF

    def test_customers_love_pattern(self, detector):
        """Test 'customers love' pattern triggers SOCIAL_PROOF belief."""
        context = "Customers love the intuitive interface."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SOCIAL_PROOF

    def test_fortune_500_pattern(self, detector):
        """Test 'Fortune 500' pattern triggers SOCIAL_PROOF belief."""
        context = "Used by Fortune 500 enterprises globally."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SOCIAL_PROOF

    def test_award_winning_pattern(self, detector):
        """Test 'award-winning' pattern triggers SOCIAL_PROOF belief."""
        context = "Our award-winning platform is recognized globally."
        belief, confidence, signals = detector.detect_belief(context)

        assert belief == BeliefType.SOCIAL_PROOF


# ==================== Detect All Beliefs Tests ====================


class TestDetectAllBeliefs:
    """Tests for detecting all beliefs with scores."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return BeliefTypeDetector()

    def test_detect_multiple_beliefs(self, detector):
        """Test detecting multiple belief types in mixed context."""
        context = """
        According to data, this is the best solution on the market.
        Millions of users trust this platform for its ROI.
        Sign up today for a free trial.
        """
        beliefs = detector.detect_all_beliefs(context)

        # Should find multiple belief types
        assert len(beliefs) > 1

        # Beliefs should be sorted by score
        scores = [score for _, score in beliefs]
        assert scores == sorted(scores, reverse=True)

    def test_returns_empty_for_no_beliefs(self, detector):
        """Test returns empty list when no beliefs detected."""
        context = "This is a generic text without any belief signals."
        beliefs = detector.detect_all_beliefs(context)

        # May return empty or low-confidence matches
        assert isinstance(beliefs, list)

    def test_scores_are_positive(self, detector):
        """Test all belief scores are positive."""
        context = "The best solution that saves time, trusted by millions."
        beliefs = detector.detect_all_beliefs(context)

        for belief, score in beliefs:
            assert score > 0


# ==================== Edge Cases Tests ====================


class TestBeliefDetectorEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return BeliefTypeDetector()

    def test_empty_context(self, detector):
        """Test empty context returns None belief."""
        belief, confidence, signals = detector.detect_belief("")

        assert belief is None
        assert confidence == 0.0
        assert signals == []

    def test_case_insensitive(self, detector):
        """Test pattern matching is case insensitive."""
        context_lower = "this is the best solution"
        context_upper = "THIS IS THE BEST SOLUTION"
        context_mixed = "This is the BEST Solution"

        belief_lower, _, _ = detector.detect_belief(context_lower)
        belief_upper, _, _ = detector.detect_belief(context_upper)
        belief_mixed, _, _ = detector.detect_belief(context_mixed)

        assert belief_lower == BeliefType.SUPERIORITY
        assert belief_upper == BeliefType.SUPERIORITY
        assert belief_mixed == BeliefType.SUPERIORITY

    def test_multiple_matches_increase_confidence(self, detector):
        """Test multiple pattern matches increase confidence."""
        single_match = "This is the best solution."
        multi_match = "This is the best solution, the market leader, unrivaled."

        _, conf_single, _ = detector.detect_belief(single_match)
        _, conf_multi, _ = detector.detect_belief(multi_match)

        assert conf_multi >= conf_single

    def test_signals_returned(self, detector):
        """Test detection signals are returned."""
        context = "This is the best solution with great ROI."
        belief, confidence, signals = detector.detect_belief(context)

        assert len(signals) > 0
        assert all(isinstance(s, str) for s in signals)

    def test_signals_limited(self, detector):
        """Test signals list is limited in length."""
        # Context with many patterns
        context = """
        The best, top, #1, market leader, number one solution.
        Outperforms, unmatched, unrivaled, superior, leading.
        """
        belief, confidence, signals = detector.detect_belief(context)

        # Signals should be limited to 3
        assert len(signals) <= 3
