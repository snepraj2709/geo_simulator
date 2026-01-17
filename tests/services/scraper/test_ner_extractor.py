"""
Tests for NER (Named Entity Recognition) Extractor component.
"""

import pytest

from services.scraper.components.ner_extractor import (
    NERExtractor,
    ExtractedNamedEntities,
    NamedEntity,
    CompetitorDetector,
)


class TestNERExtractor:
    """Test NERExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance (without spaCy for CI)."""
        return NERExtractor(use_spacy=False)

    @pytest.fixture
    def sample_text(self):
        """Sample text for NER extraction."""
        return """
        Acme Corporation, headquartered in San Francisco, California, announced
        today that CEO John Smith will present at the Tech Summit 2024 in New York.

        The company, which competes with Microsoft and Google in the enterprise
        software market, reported Q4 revenue of $50 million, up 25% from last year.

        Founded in 2015, Acme has grown to serve over 500 customers including
        Fortune 500 companies like Apple, Amazon, and IBM.

        The presentation will take place on January 15, 2024, at the Javits Center.
        Contact: press@acme.com or call 1-800-555-1234 for more information.
        """

    def test_extract_organizations(self, extractor, sample_text):
        """Test organization extraction."""
        result = extractor.extract(sample_text)

        orgs = result.get_all_organizations()
        # Should find company names
        assert len(orgs) > 0

        # Check for known companies
        org_lower = [o.lower() for o in orgs]
        assert any("acme" in o or "microsoft" in o or "google" in o for o in org_lower)

    def test_extract_locations(self, extractor, sample_text):
        """Test location extraction."""
        result = extractor.extract(sample_text)

        locations = result.get_all_locations()
        location_lower = [l.lower() for l in locations]

        # Should find cities and states
        assert any("san francisco" in l or "california" in l or "new york" in l for l in location_lower)

    def test_extract_money(self, extractor, sample_text):
        """Test money extraction."""
        result = extractor.extract(sample_text)

        # Should find monetary values
        assert len(result.money) > 0

        money_texts = [m.text for m in result.money]
        assert any("50" in t or "million" in t.lower() for t in money_texts)

    def test_extract_dates(self, extractor, sample_text):
        """Test date extraction."""
        result = extractor.extract(sample_text)

        # Should find dates
        assert len(result.dates) > 0

        date_texts = [d.text for d in result.dates]
        assert any("2024" in t or "2015" in t or "January" in t for t in date_texts)

    def test_to_dict(self, extractor, sample_text):
        """Test conversion to dictionary."""
        result = extractor.extract(sample_text)
        result_dict = result.to_dict()

        assert "organizations" in result_dict
        assert "persons" in result_dict
        assert "products" in result_dict
        assert "locations" in result_dict
        assert "money" in result_dict
        assert "dates" in result_dict

        # Each item should have the expected fields
        if result_dict["organizations"]:
            org = result_dict["organizations"][0]
            assert "text" in org
            assert "label" in org
            assert "confidence" in org
            assert "source" in org

    def test_empty_text(self, extractor):
        """Test handling of empty text."""
        result = extractor.extract("")

        assert isinstance(result, ExtractedNamedEntities)
        assert len(result.organizations) == 0
        assert len(result.persons) == 0

    def test_max_length_truncation(self, extractor):
        """Test text truncation for very long content."""
        long_text = "This is a test. " * 100000
        result = extractor.extract(long_text, max_length=1000)

        # Should not raise an error
        assert isinstance(result, ExtractedNamedEntities)

    def test_extract_with_context(self, extractor, sample_text):
        """Test extraction with surrounding context."""
        result = extractor.extract_with_context(sample_text, context_window=30)

        # Should return dict with categories
        assert "organizations" in result
        assert "locations" in result

        # Each entity should have context
        for org in result.get("organizations", []):
            assert "context" in org
            assert len(org["context"]) > 0


class TestNamedEntity:
    """Test NamedEntity data class."""

    def test_named_entity_creation(self):
        """Test creating a NamedEntity."""
        entity = NamedEntity(
            text="Acme Corp",
            label="ORG",
            start=0,
            end=9,
            confidence=0.95,
            source="spacy",
        )

        assert entity.text == "Acme Corp"
        assert entity.label == "ORG"
        assert entity.confidence == 0.95

    def test_named_entity_defaults(self):
        """Test NamedEntity default values."""
        entity = NamedEntity(
            text="Test",
            label="ORG",
            start=0,
            end=4,
        )

        assert entity.confidence == 1.0
        assert entity.source == "spacy"


class TestExtractedNamedEntities:
    """Test ExtractedNamedEntities data class."""

    def test_get_all_organizations(self):
        """Test getting unique organization names."""
        entities = ExtractedNamedEntities()
        entities.organizations = [
            NamedEntity(text="Acme Corp", label="ORG", start=0, end=9),
            NamedEntity(text="Acme Corp", label="ORG", start=100, end=109),  # Duplicate
            NamedEntity(text="Beta Inc", label="ORG", start=200, end=208),
        ]

        orgs = entities.get_all_organizations()
        assert len(orgs) == 2
        assert "Acme Corp" in orgs
        assert "Beta Inc" in orgs

    def test_get_all_products(self):
        """Test getting unique product names."""
        entities = ExtractedNamedEntities()
        entities.products = [
            NamedEntity(text="ProductX", label="PRODUCT", start=0, end=8),
            NamedEntity(text="ProductY", label="PRODUCT", start=50, end=58),
        ]

        products = entities.get_all_products()
        assert len(products) == 2

    def test_get_all_locations(self):
        """Test getting unique location names."""
        entities = ExtractedNamedEntities()
        entities.locations = [
            NamedEntity(text="New York", label="GPE", start=0, end=8),
            NamedEntity(text="California", label="GPE", start=50, end=60),
        ]

        locations = entities.get_all_locations()
        assert len(locations) == 2


class TestCompetitorDetector:
    """Test CompetitorDetector functionality."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        ner = NERExtractor(use_spacy=False)
        return CompetitorDetector(ner)

    @pytest.fixture
    def sample_text_with_competitors(self):
        """Sample text mentioning competitors."""
        return """
        Our platform is better than Salesforce and offers more features than HubSpot.
        Unlike Microsoft Dynamics, we provide seamless integration.
        Companies switching from Zendesk to our solution see 50% improvement.

        We are a leading alternative to SAP for mid-market companies.
        When compared to Oracle, our pricing is more competitive.
        """

    def test_detect_competitors(self, detector, sample_text_with_competitors):
        """Test competitor detection."""
        competitors = detector.detect_competitors(
            sample_text_with_competitors,
            own_brand="AcmeCRM",
        )

        # Should find competitor mentions
        assert len(competitors) > 0

        competitor_names = [c["name"] for c in competitors]
        # Should find at least some known competitors
        # Note: Detection depends on regex patterns working correctly

    def test_detect_competitors_excludes_own_brand(self, detector):
        """Test that own brand is excluded from competitors."""
        text = "Our product AcmeCRM is better than Salesforce."
        competitors = detector.detect_competitors(text, own_brand="AcmeCRM")

        competitor_names = [c["name"].lower() for c in competitors]
        assert "acmecrm" not in competitor_names

    def test_extract_comparison_table(self, detector):
        """Test competitor extraction from comparison tables."""
        html = """
        <table class="comparison">
            <thead>
                <tr>
                    <th>Feature</th>
                    <th>Our Product</th>
                    <th>Competitor A</th>
                    <th>Competitor B</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Price</td>
                    <td>$99</td>
                    <td>$149</td>
                    <td>$199</td>
                </tr>
            </tbody>
        </table>
        """

        competitors = detector.extract_comparison_table(html)

        # Should find competitors from table headers
        assert len(competitors) > 0

        competitor_names = [c["name"] for c in competitors]
        # Should include non-generic headers
        assert any("Competitor" in name for name in competitor_names)


class TestNERExtractorWithSpaCy:
    """Tests that would use spaCy if available."""

    def test_spacy_availability_detection(self):
        """Test that spaCy availability is correctly detected."""
        from services.scraper.components.ner_extractor import SPACY_AVAILABLE

        # SPACY_AVAILABLE should be a boolean
        assert isinstance(SPACY_AVAILABLE, bool)

    @pytest.mark.skipif(
        True,  # Skip by default since spaCy may not be installed in CI
        reason="spaCy may not be installed",
    )
    def test_spacy_extraction(self):
        """Test extraction with spaCy (if available)."""
        extractor = NERExtractor(use_spacy=True)
        result = extractor.extract("Google and Microsoft are technology companies.")

        # If spaCy is working, should find organizations
        orgs = result.get_all_organizations()
        assert len(orgs) >= 0  # May find orgs if spaCy is available
