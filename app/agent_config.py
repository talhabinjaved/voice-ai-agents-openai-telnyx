import os
from dotenv import load_dotenv

load_dotenv()

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PUBLIC_DOMAIN = os.getenv("DOMAIN")  # e.g., voice.example.com

if not TELNYX_API_KEY or not OPENAI_API_KEY or not PUBLIC_DOMAIN:
    raise RuntimeError("Missing required env vars: TELNYX_API_KEY, OPENAI_API_KEY, DOMAIN")

AGENT_VOICE = os.getenv("AGENT_VOICE", "marin")   # alloy|echo|fable|onyx|nova|shimmer|marin

AGENT_INSTRUCTIONS = os.getenv(
    "AGENT_INSTRUCTIONS",
    """You are a professional AI voice assistant for our company. You're here to help callers with their questions and connect them with the right people when needed.

Your approach:
- Be friendly, professional, and helpful
- Keep responses concise and natural - 2-3 sentences max
- Sound conversational, not robotic
- Listen carefully and ask clarifying questions when needed

What you can help with:
- Answering general questions about our company and services
- Providing basic information about our products or services
- Helping callers understand our business hours and contact information
- Connecting callers to the appropriate department when they need specialized assistance

Your guidelines:
- Always be helpful and represent our company professionally
- If you don't know something specific, offer to connect them with someone who does
- Keep technical explanations simple unless the caller wants more detail
- For urgent matters, prioritize getting them to the right person quickly

Communication:
- Speak clearly and at a comfortable pace
- If you can't hear clearly: "I'm sorry, I didn't catch that. Could you please repeat that?"
- Vary your responses so you don't sound repetitive

When to transfer calls:
- When callers specifically request a department (sales, support, billing, etc.)
- When they need detailed technical assistance beyond your scope
- When they request to speak with a human representative
- For urgent matters that require immediate attention

Call management:
- End calls politely when the conversation is complete
- Always explain what's happening before transferring or ending calls
- Thank callers for their time{transfer_instructions}
"""
)

# Department configuration for call transfers
DEPARTMENTS = {
    "sales": {
        "sip_uri": os.getenv("SALES_SIP_URI", ""),
        "headers": [
            {
                "name": "P-Called-Party-ID",
                "value": os.getenv("SALES_P_Called_Party_ID_HEADER", "")
            }
        ]
    },
    "support": {
        "sip_uri": os.getenv("SUPPORT_SIP_URI", ""),
        "headers": [
            {
                "name": "P-Called-Party-ID", 
                "value": os.getenv("SUPPORT_P_Called_Party_ID_HEADER", "")
            }
        ]
    },
    "billing": {
        "sip_uri": os.getenv("BILLING_SIP_URI", ""),
        "headers": [
            {
                "name": "P-Called-Party-ID",
                "value": os.getenv("BILLING_P_Called_Party_ID_HEADER", "")
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
    "Hello! Thank you for calling. I'm your AI assistant and I'm here to help you today. How can I assist you?"
)
