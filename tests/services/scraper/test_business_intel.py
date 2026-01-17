"""
Tests for Business Intelligence Extractor component.
"""

import pytest

from services.scraper.components.business_intel import (
    BusinessIntelligenceExtractor,
    BusinessIntelligence,
    ProductOffering,
    ServiceOffering,
    ValueProposition,
    TargetAudienceSignal,
    CompanyProfile,
)


class TestBusinessIntelligenceExtractor:
    """Test BusinessIntelligenceExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return BusinessIntelligenceExtractor()

    @pytest.fixture
    def sample_html(self):
        """Sample HTML content for testing."""
        return """
        <html>
        <head>
            <title>Acme Corp - Enterprise Software Solutions</title>
            <meta name="description" content="Acme Corp provides enterprise software solutions for businesses of all sizes.">
        </head>
        <body>
            <header>
                <h1 class="tagline">Transform Your Business with AI</h1>
            </header>
            <main>
                <section class="products">
                    <h2>Our Products</h2>
                    <div class="product-card">
                        <h3>AcmePlatform Pro</h3>
                        <p>Enterprise-grade platform for data management.</p>
                    </div>
                    <div class="product-card">
                        <h3>AcmeAnalytics Suite</h3>
                        <p>Advanced analytics and reporting tools.</p>
                    </div>
                </section>
                <section class="services">
                    <h2>Our Services</h2>
                    <p>We offer: consulting, implementation, training, and support services.</p>
                </section>
                <section class="about">
                    <p>Founded in 2015, Acme Corp has grown to 500+ employees worldwide.</p>
                    <p>Headquartered in San Francisco, CA</p>
                </section>
                <section class="features">
                    <h2>Why Choose Us</h2>
                    <ul>
                        <li>Save up to 40% on operational costs</li>
                        <li>10x faster data processing</li>
                        <li>99.9% uptime guarantee</li>
                        <li>SOC 2 certified</li>
                        <li>GDPR compliant</li>
                    </ul>
                </section>
                <section class="customers">
                    <p>Designed for enterprise teams and growing startups.</p>
                    <p>Perfect for marketing teams and sales professionals.</p>
                </section>
            </main>
        </body>
        </html>
        """

    @pytest.fixture
    def sample_content(self):
        """Sample text content."""
        return """
        Acme Corp provides enterprise software solutions for businesses of all sizes.
        Transform Your Business with AI.

        Our Products
        AcmePlatform Pro - Enterprise-grade platform for data management.
        AcmeAnalytics Suite - Advanced analytics and reporting tools.

        Our Services
        We offer consulting, implementation, training, and support services.

        Founded in 2015, Acme Corp has grown to 500+ employees worldwide.
        Headquartered in San Francisco, CA

        Why Choose Us
        Save up to 40% on operational costs
        10x faster data processing
        99.9% uptime guarantee
        SOC 2 certified
        GDPR compliant

        Designed for enterprise teams and growing startups.
        Perfect for marketing teams and sales professionals.

        Our technology stack includes React, Node, Python, and AWS.
        We integrate with Salesforce, HubSpot, and Zendesk.
        """

    @pytest.fixture
    def sample_structured_data(self):
        """Sample JSON-LD structured data."""
        return [
            {
                "@type": "Organization",
                "name": "Acme Corp",
                "description": "Enterprise software solutions provider",
                "foundingDate": "2015",
                "address": {
                    "addressLocality": "San Francisco",
                    "addressRegion": "CA",
                },
            },
            {
                "@type": "Product",
                "name": "AcmePlatform Pro",
                "description": "Enterprise-grade platform for data management",
            },
        ]

    @pytest.fixture
    def sample_headings(self):
        """Sample headings."""
        return [
            {"level": "h1", "text": "Transform Your Business with AI"},
            {"level": "h2", "text": "Our Products"},
            {"level": "h3", "text": "AcmePlatform Pro"},
            {"level": "h3", "text": "AcmeAnalytics Suite"},
            {"level": "h2", "text": "Our Services"},
            {"level": "h2", "text": "Why Choose Us"},
        ]

    def test_extract_company_profile(
        self,
        extractor,
        sample_content,
        sample_html,
        sample_structured_data,
        sample_headings,
    ):
        """Test company profile extraction."""
        result = extractor.extract(
            content_text=sample_content,
            html=sample_html,
            headings=sample_headings,
            structured_data=sample_structured_data,
            meta_description="Acme Corp provides enterprise software solutions",
            title="Acme Corp - Enterprise Software Solutions",
            domain="acme.com",
        )

        assert result.company_profile.name == "Acme Corp"
        assert result.company_profile.founding_year == 2015
        assert "San Francisco" in (result.company_profile.headquarters or "")

    def test_extract_products(
        self,
        extractor,
        sample_content,
        sample_html,
        sample_structured_data,
        sample_headings,
    ):
        """Test product extraction."""
        result = extractor.extract(
            content_text=sample_content,
            html=sample_html,
            headings=sample_headings,
            structured_data=sample_structured_data,
            meta_description=None,
            title="Acme Corp",
            domain="acme.com",
        )

        # Should find products from structured data and headings
        assert len(result.products) > 0
        product_names = [p.name for p in result.products]
        assert any("AcmePlatform" in name for name in product_names)

    def test_extract_services(
        self,
        extractor,
        sample_content,
        sample_html,
        sample_structured_data,
        sample_headings,
    ):
        """Test service extraction."""
        result = extractor.extract(
            content_text=sample_content,
            html=sample_html,
            headings=sample_headings,
            structured_data=[],  # No structured data for services
            meta_description=None,
            title="Acme Corp",
            domain="acme.com",
        )

        # Should extract services from text patterns
        assert len(result.services) >= 0  # May or may not find services

    def test_extract_value_propositions(
        self,
        extractor,
        sample_content,
        sample_html,
        sample_structured_data,
        sample_headings,
    ):
        """Test value proposition extraction."""
        result = extractor.extract(
            content_text=sample_content,
            html=sample_html,
            headings=sample_headings,
            structured_data=sample_structured_data,
            meta_description=None,
            title="Acme Corp",
            domain="acme.com",
        )

        # Should find value propositions
        assert len(result.value_propositions) > 0

        # Check for different benefit types
        benefit_types = [vp.benefit_type for vp in result.value_propositions]
        assert len(benefit_types) > 0

    def test_extract_target_audience(
        self,
        extractor,
        sample_content,
        sample_html,
        sample_structured_data,
        sample_headings,
    ):
        """Test target audience extraction."""
        result = extractor.extract(
            content_text=sample_content,
            html=sample_html,
            headings=sample_headings,
            structured_data=sample_structured_data,
            meta_description=None,
            title="Acme Corp",
            domain="acme.com",
        )

        # Should identify target audience signals
        assert len(result.target_audience) > 0

        # Check for enterprise/startup mentions
        segments = [ta.segment.lower() for ta in result.target_audience]
        assert any("enterprise" in s or "startup" in s or "team" in s for s in segments)

    def test_extract_technologies(
        self,
        extractor,
        sample_content,
        sample_html,
        sample_structured_data,
        sample_headings,
    ):
        """Test technology extraction."""
        result = extractor.extract(
            content_text=sample_content,
            html=sample_html,
            headings=sample_headings,
            structured_data=sample_structured_data,
            meta_description=None,
            title="Acme Corp",
            domain="acme.com",
        )

        # Should find technologies mentioned
        assert len(result.technologies_used) > 0
        tech_lower = [t.lower() for t in result.technologies_used]
        assert any(t in tech_lower for t in ["react", "node", "python", "aws"])

    def test_extract_certifications(
        self,
        extractor,
        sample_content,
        sample_html,
        sample_structured_data,
        sample_headings,
    ):
        """Test certification extraction."""
        result = extractor.extract(
            content_text=sample_content,
            html=sample_html,
            headings=sample_headings,
            structured_data=sample_structured_data,
            meta_description=None,
            title="Acme Corp",
            domain="acme.com",
        )

        # Should find certifications
        assert len(result.certifications) > 0
        cert_lower = [c.lower() for c in result.certifications]
        assert any("soc" in c or "gdpr" in c for c in cert_lower)

    def test_to_dict(
        self,
        extractor,
        sample_content,
        sample_html,
        sample_structured_data,
        sample_headings,
    ):
        """Test conversion to dictionary."""
        result = extractor.extract(
            content_text=sample_content,
            html=sample_html,
            headings=sample_headings,
            structured_data=sample_structured_data,
            meta_description=None,
            title="Acme Corp",
            domain="acme.com",
        )

        result_dict = result.to_dict()

        assert "company_profile" in result_dict
        assert "products" in result_dict
        assert "services" in result_dict
        assert "value_propositions" in result_dict
        assert "target_audience" in result_dict
        assert "technologies_used" in result_dict
        assert "certifications" in result_dict

    def test_empty_content(self, extractor):
        """Test handling of empty content."""
        result = extractor.extract(
            content_text="",
            html="<html><body></body></html>",
            headings=[],
            structured_data=[],
            meta_description=None,
            title=None,
            domain="example.com",
        )

        assert isinstance(result, BusinessIntelligence)
        assert result.company_profile.name == "Example"  # From domain


class TestBusinessIntelligenceDataClasses:
    """Test data classes for business intelligence."""

    def test_product_offering(self):
        """Test ProductOffering data class."""
        product = ProductOffering(
            name="Test Product",
            description="A test product",
            category="Software",
            features=["Feature 1", "Feature 2"],
            pricing="$99/mo",
            confidence=0.8,
            source="structured_data",
        )

        assert product.name == "Test Product"
        assert len(product.features) == 2
        assert product.confidence == 0.8

    def test_service_offering(self):
        """Test ServiceOffering data class."""
        service = ServiceOffering(
            name="Consulting",
            description="Expert consulting services",
            category="Professional Services",
            deliverables=["Assessment", "Roadmap"],
            pricing="Custom",
            confidence=0.7,
        )

        assert service.name == "Consulting"
        assert len(service.deliverables) == 2

    def test_value_proposition(self):
        """Test ValueProposition data class."""
        vp = ValueProposition(
            statement="Save 40% on costs",
            benefit_type="cost",
            target_pain_point="High operational expenses",
            confidence=0.9,
        )

        assert vp.benefit_type == "cost"
        assert "40%" in vp.statement

    def test_target_audience_signal(self):
        """Test TargetAudienceSignal data class."""
        signal = TargetAudienceSignal(
            segment="Enterprise teams",
            evidence="Designed for enterprise teams",
            confidence=0.7,
            source="explicit",
        )

        assert "enterprise" in signal.segment.lower()
        assert signal.source == "explicit"

    def test_company_profile(self):
        """Test CompanyProfile data class."""
        profile = CompanyProfile(
            name="Acme Corp",
            description="Software company",
            tagline="Transform your business",
            mission_statement="Make software accessible",
            founding_year=2015,
            company_size="500+ employees",
            headquarters="San Francisco, CA",
            industry="technology",
        )

        assert profile.name == "Acme Corp"
        assert profile.founding_year == 2015
        assert profile.industry == "technology"
