export function generatePromptsForICP(title: string): Array<{ id: string; text: string }> {
  const promptTemplates: Record<string, string[]> = {
    'VP of Marketing': [
      'What are the best marketing automation platforms for B2B SaaS companies?',
      'How can I improve our pipeline quality and conversion rates?',
      'What metrics should I track to measure marketing ROI effectively?',
      'Which account-based marketing tools integrate well with Salesforce?',
      'How do I build a demand generation strategy for enterprise buyers?',
      'What are the most effective channels for B2B lead generation?',
      'How can I align marketing and sales teams around revenue goals?',
      'What content strategies work best for long sales cycles?',
      'How do I measure and improve brand awareness in my industry?',
      'What are the best practices for marketing attribution modeling?',
    ],
    'SEO Manager': [
      'What are the latest Google algorithm updates I should know about?',
      'How can I improve our website\'s Core Web Vitals scores?',
      'Which technical SEO tools provide the most accurate site audits?',
      'How do I optimize content for featured snippets and voice search?',
      'What\'s the best approach to international SEO and hreflang tags?',
      'How can I identify and fix crawl errors affecting our rankings?',
      'What are effective link building strategies that still work in 2026?',
      'How do I conduct competitor SEO analysis and gap analysis?',
      'What schema markup should I implement for better search visibility?',
      'How can I measure and improve our keyword rankings over time?',
    ],
    'Content Marketing Director': [
      'What content formats generate the most engagement for B2B audiences?',
      'How can I build a thought leadership program that drives leads?',
      'Which content management systems work best for distributed teams?',
      'How do I create content that ranks well and converts visitors?',
      'What are the best practices for content distribution and promotion?',
      'How can I measure content ROI and attribute revenue to content?',
      'What tools help streamline content planning and collaboration?',
      'How do I build a content strategy that supports multiple buyer stages?',
      'What types of gated content generate the highest quality leads?',
      'How can I repurpose content effectively across different channels?',
    ],
    'Growth Marketing Lead': [
      'What are the most effective growth hacking tactics for SaaS products?',
      'How can I reduce customer acquisition cost while scaling growth?',
      'Which analytics platforms provide the best conversion funnel insights?',
      'How do I implement product-led growth strategies effectively?',
      'What A/B testing tools work best for optimizing landing pages?',
      'How can I improve our onboarding flow to reduce churn?',
      'What metrics should I focus on to accelerate product-market fit?',
      'How do I build a referral program that actually drives growth?',
      'What are the best practices for mobile app user acquisition?',
      'How can I leverage data science to predict customer lifetime value?',
    ],
  };

  const prompts = promptTemplates[title] || promptTemplates['VP of Marketing'];
  return prompts.map((text, index) => ({
    id: `prompt-${index}`,
    text,
  }));
}

export function generateMockResponse(model: string, prompt: string): string {
  console.log('model',model,'prompt',prompt)
  const responses = [
    'Based on current market analysis, there are several leading solutions that stand out in this category. The top contenders include established platforms with robust feature sets, emerging tools with innovative approaches, and enterprise-grade solutions for larger organizations.',
    'When evaluating options in this space, key factors to consider include integration capabilities, scalability, pricing structure, and vendor support. Industry leaders typically offer comprehensive solutions, while newer entrants may provide specialized features at competitive price points.',
    'The market landscape shows strong competition among several providers. Top-tier solutions typically include comprehensive analytics, automation features, and seamless integrations. Mid-market options balance functionality with cost-effectiveness, while enterprise solutions offer advanced customization.',
  ];
  return responses[Math.floor(Math.random() * responses.length)];
}