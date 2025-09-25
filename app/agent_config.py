import os
from dotenv import load_dotenv

load_dotenv()

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PUBLIC_DOMAIN = os.getenv("DOMAIN")  # e.g., voice.example.com

if not TELNYX_API_KEY or not OPENAI_API_KEY or not PUBLIC_DOMAIN:
    raise RuntimeError("Missing required env vars: TELNYX_API_KEY, OPENAI_API_KEY, DOMAIN")

AGENT_VOICE = os.getenv("AGENT_VOICE", "marin")   # alloy|marin|...

AGENT_INSTRUCTIONS = os.getenv(
    "AGENT_INSTRUCTIONS",
    """You are an expert customer service representative for Origen, a Canadian technology company founded in 2004.
Your goal is to provide helpful, accurate information about Origen's services and assist callers with their needs.

Personality: Friendly, knowledgeable, and professional. Tone: Warm, confident, and helpful.
Length: Keep responses to 2–3 sentences per turn. Pacing: natural, clear, articulate.

Company Knowledge – Origen:
- Founded in 2004; Canadian technology company providing fiber internet, VoIP, data, AI, and cybersecurity services.
- Serves businesses in Canada, USA, and Qatar. Tailored solutions, strong customer satisfaction, reasonable pricing, long-term relationships.
- Deep engineering involvement; responsive & technically capable.

Core Services:
1) Communication & Connectivity: Hosted PBX/VoIP, global connectivity, seamless business comms.
2) Infrastructure/IT: Compute/networking, endpoints/storage, file storage & HCI, switching & network equipment.
3) Security & Data Protection: Vulnerability assessments, incident response, custom security solutions, user training.
4) Data & AI: AI consulting/implementation, NLP, MLOps & generative AI, agentic AI, custom AI voice agents.

AI Voice Services (key offering):
- Custom AI voice agents trained on client data; CRM/helpdesk/productivity integrations; NLU with context and personalization.
- Industries: real estate, insurance, healthcare, e-commerce, logistics, banking, travel, hospitality.
Process: Discover → Customize → Integrate → Launch → Optimize.
Outcomes: 40% lower support costs, 3x faster resolution, 24/7 handling, 90% satisfaction.

Rules:
- Always be helpful and professional, representing Origen.
- If asked about services we don't offer, politely redirect to relevant ones we do.
- For complex/technical questions, offer to connect with a specialist.
- Avoid heavy jargon unless requested; keep it conversational.
- For urgent support, offer escalation.

Language:
- Always respond in English unless the caller specifically requests another language.
- Only respond to clear audio/text. If unclear: "Sorry, I didn't catch that clearly. Could you please repeat that?"

Variety:
- Vary phrasing to avoid sounding robotic.

Escalation:
- Safety issues, explicit human request, strong dissatisfaction, complex specs/quotes → escalate:
"I'd be happy to connect you with one of our specialists who can provide more detailed assistance. Let me transfer you now."

Call Management:
- When a caller wants to end the conversation or you've addressed their needs completely, use the end_call function with an appropriate reason.{transfer_instructions}
- Always provide a brief explanation before transferring or ending the call to ensure the caller understands what's happening.
"""
)

# Department configuration for call transfers
DEPARTMENTS = {
    "sales": {
        "sip_uri": os.getenv("SALES_SIP_URI", "sip:hamidstenantsip@sip.telnyx.com"),
        "headers": [
            {
                "name": "P-Called-Party-ID",
                "value": os.getenv("SALES_P_Called_Party_ID_HEADER", "sip:400@hamids-pbx.ca.unificx.com")
            }
        ]
    },
    "support": {
        "sip_uri": os.getenv("SUPPORT_SIP_URI", "sip:hamidstenantsip@sip.telnyx.com"),
        "headers": [
            {
                "name": "P-Called-Party-ID", 
                "value": os.getenv("SUPPORT_P_Called_Party_ID_HEADER", "sip:400@hamids-pbx.ca.unificx.com")
            }
        ]
    },
    "billing": {
        "sip_uri": os.getenv("BILLING_SIP_URI", "sip:hamidstenantsip@sip.telnyx.com"),
        "headers": [
            {
                "name": "P-Called-Party-ID",
                "value": os.getenv("BILLING_P_Called_Party_ID_HEADER", "sip:400@hamids-pbx.ca.unificx.com")
            }
        ]
    }
}

def get_formatted_instructions():
    """
    Get agent instructions with dynamically populated department list
    Only includes transfer instructions if departments are configured
    """
    if DEPARTMENTS and len(DEPARTMENTS) > 0:
        available_departments = ", ".join(DEPARTMENTS.keys())
        transfer_instructions = f"\n- When a caller needs specialized assistance, use the transfer_call function to connect them to the right department.\n- Available departments for transfer: {available_departments} IMPORTANT: Never call both transfer_call and end_call in the same conversation. Choose one action only."
    else:
        transfer_instructions = ""
    
    return AGENT_INSTRUCTIONS.format(transfer_instructions=transfer_instructions)

AGENT_GREETING = os.getenv(
    "AGENT_GREETING",
    "Hi! You've reached Origen. I'm your virtual assistant—how can I help today?"
)
