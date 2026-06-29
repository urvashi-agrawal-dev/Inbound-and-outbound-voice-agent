"""FAQ detour handler - answers product questions and returns to FSM flow."""

from app.core.fsm.states import ConversationState, STATE_PROMPTS

PRODUCT_KNOWLEDGE = """
Karta SDR is an AI-powered voice sales development platform that:
- Makes and receives inbound/outbound sales calls autonomously
- Qualifies leads using structured conversation flows
- Integrates with CRM systems (Salesforce, HubSpot, Google Sheets)
- Books meetings automatically via calendar integration
- Handles interruptions and barge-in naturally
- Provides real-time analytics and call summaries

Pricing tiers (monthly):
- Starter: $499/mo - up to 1,000 calls, basic qualification
- Growth: $1,999/mo - up to 10,000 calls, CRM integration, custom flows
- Enterprise: $9,999+/mo - unlimited calls, dedicated support, custom AI training

Key differentiators:
- Sub-500ms response latency
- Finite state machine (not free-form chatbot) for reliable qualification
- Human handoff when requested
- SOC 2 compliant infrastructure
"""


class FAQHandler:
    """Handles off-script product/pricing questions during qualification."""

    def build_faq_prompt(self, question: str, return_state: ConversationState) -> str:
        return_state_instruction = STATE_PROMPTS.get(
            return_state, "Continue the qualification conversation."
        )
        return f"""You are Alex, a sales development representative for Karta SDR.

The caller asked an off-script question during qualification. Answer concisely (2-3 sentences max),
then smoothly transition back to the qualification flow.

PRODUCT KNOWLEDGE:
{PRODUCT_KNOWLEDGE}

CALLER QUESTION: {question}

After answering, transition back with something like:
"Now, to make sure I can help you best..." and then: {return_state_instruction}

Keep tone professional, warm, and conversational. Do not be salesy."""

    def should_return_to_flow(self, faq_turn_count: int, max_turns: int) -> bool:
        return faq_turn_count >= max_turns
