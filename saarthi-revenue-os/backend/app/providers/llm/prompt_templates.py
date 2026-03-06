"""
Centralized AI prompt architecture for all LLM operations.
Do not define inline prompts in services. Always import from here.
"""

# GLOBAL SYSTEM PROMPT
SYSTEM_PROMPT = """
You are an expert B2B sales assistant working inside a Revenue OS platform.

Your job is to help generate, classify, and analyze professional B2B communication.

You must follow these principles:

• Write concise professional messages  
• Avoid spam-like phrases  
• Never fabricate information  
• Focus on business value and clarity  
• Keep responses short and natural  
"""

# PROMPT 1 — LEAD SCORING AI
LEAD_SCORING_PROMPT = """
Evaluate if this lead fits a B2B SaaS outbound target.

Return a score between 0 and 100.

Scoring rules:

+30 if verified LinkedIn profile  
+20 if professional website exists  
+20 if job title is decision maker  
+20 if company size between 10 and 500 employees  
+10 if email domain matches company domain  

Reject if score < 50.

Return JSON only:

{
 "score": number,
 "reason": "short explanation"
}

Lead data:
{lead_data}
"""

# PROMPT 2 — EMAIL GENERATION
EMAIL_GENERATION_PROMPT = """
Write a short personalized cold email.

Constraints:

• max 90 words  
• conversational tone  
• no spam trigger phrases  
• no exaggeration  
• no emojis  
• no markdown  

Structure:

1. Personal intro
2. Value statement
3. Soft CTA

Lead data:
{lead_data}

Campaign data:
{campaign_data}
"""

# PROMPT 3 — FOLLOWUP GENERATION
FOLLOWUP_GENERATION_PROMPT = """
Write a polite follow-up email.

Constraints:

• max 60 words  
• conversational  
• not pushy  
• reference previous email  
"""

# PROMPT 4 — REPLY CLASSIFICATION
REPLY_CLASSIFICATION_PROMPT = """
Classify the following email reply.

Return ONLY one label from:

POSITIVE
NEGATIVE
MEETING_REQUEST
OUT_OF_OFFICE
UNSUBSCRIBE
NEUTRAL

Reply:

{email_text}
"""

# PROMPT 5 — AI REPLY GENERATOR
AI_REPLY_GENERATOR_PROMPT = """
Write a reply to a prospect who showed interest.

Goal:

Move conversation toward booking a meeting.

Constraints:

• under 80 words
• friendly
• professional
• include meeting link

Meeting link:

{calendar_link}
"""

# PROMPT 6 — WEBSITE LEAD EXTRACTION
WEBSITE_LEAD_EXTRACTION_PROMPT = """
Extract potential lead contacts from the following website content.

Return JSON array:

[
{{
"name": "",
"title": "",
"email": "",
"linkedin": ""
}}
]

If none exist return [].

Website content:
{website_content}
"""

# PROMPT 7 — DEAL PIPELINE INSIGHTS
DEAL_PIPELINE_INSIGHTS_PROMPT = """
Analyze the following sales metrics and summarize insights.

Metrics:

Open rate: {open_rate} 
Reply rate: {reply_rate}
Meeting rate: {meeting_rate}
Closed deals: {closed_deals}

Provide:

• top insight
• biggest bottleneck
• improvement suggestion

Max 120 words.
"""
