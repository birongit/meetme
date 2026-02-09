import logging
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain.output_parsers import PydanticOutputParser

from app.core.config import settings
from app.models.schemas import SlotList
from app.services.preferences import PreferencesService

logger = logging.getLogger(__name__)

@tool
def get_days_of_week(date_strings: List[str]) -> Dict[str, str]:
    """Returns a dictionary mapping date strings (e.g. '2025-11-30' or ISO format) to their day of the week."""
    results = {}
    for date_str in date_strings:
        try:
            # Handle ISO format with T
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str)
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            results[date_str] = dt.strftime('%A')
        except Exception as e:
            results[date_str] = f"Invalid date format: {str(e)}"
    return results

class AIService:
    @staticmethod
    def rank_slots(legal_slots: List[Dict[str, str]], user_feedback: str = None) -> Dict[str, Any]:
        """
        Uses LLM to rank and select the best slots based on user feedback and preferences.
        """
        # Limit slots to avoid token limits, but sample evenly across days
        # so that later days (e.g. Friday/Saturday) aren't cut off
        max_slots = 50
        if len(legal_slots) <= max_slots:
            legal_slots_subset = legal_slots
        else:
            by_day = defaultdict(list)
            for slot in legal_slots:
                day = slot['start'][:10]
                by_day[day].append(slot)
            per_day = max(1, max_slots // len(by_day))
            legal_slots_subset = []
            for day in sorted(by_day):
                legal_slots_subset.extend(by_day[day][:per_day])

        if not legal_slots_subset:
            return {"error": "No legal slots available."}

        prefs = PreferencesService.get_preferences()
        
        slot_list_str = "\n".join([
            f"- {slot['start']} to {slot['end']}" for slot in legal_slots_subset
        ])
        
        owner_prefs_str = "Calendar Owner Preferences (Internal Guidelines - try to follow these but prioritize User Request if valid):\n"
        if prefs.get('batch_meetings'):
            owner_prefs_str += "- Try to batch meetings together if possible.\n"
        owner_prefs_str += "- Avoid meetings after 21:00 if possible.\n"
        owner_prefs_str += "- Prefer weekends over weekdays, but offer a few weekday options for diversity if the user didn't specify.\n"
        
        parser = PydanticOutputParser(pydantic_object=SlotList)
        format_instructions = parser.get_format_instructions()

        user_request_str = "User Request (The user is asking for this):\n"
        if user_feedback:
            user_request_str += f"- '{user_feedback}'\n"
        else:
            user_request_str += "- (No specific request)\n"

        prompt = (
            f"Here is a list of all legal 1-hour meeting slots for the next 7 days (fully respecting blocked times and busy events):\n"
            f"{slot_list_str}\n\n"
            f"{owner_prefs_str}\n"
            f"{user_request_str}\n"
            "Please select and rank 5-10 diverse options for the user.\n"
            "INSTRUCTIONS FOR 'message' FIELD:\n"
            "- Address the USER directly.\n"
            "- Explain why these slots are good matches for THEIR request.\n"
            "- Ensure your message accurately describes the slots you selected (e.g. do not claim to show weekdays if you only selected weekends).\n"
            "- Do NOT explicitly mention 'Owner Preferences' or 'Internal Guidelines' unless necessary to explain a constraint.\n"
            "- Be friendly and helpful.\n"
            f"{format_instructions}"
        )
        
        llm = ChatGoogleGenerativeAI(
            google_api_key=settings.GOOGLE_AI_API_KEY,
            model="gemini-2.0-flash",
            temperature=0,
        )
        
        tools = [get_days_of_week]
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful booking assistant. You have access to a tool `get_days_of_week` that can tell you the day name for a list of dates. Use it whenever you need to verify dates to answer the user's request (e.g. 'find slots on Friday'). When you have selected the slots, you MUST return the result as a JSON object matching the specified format. Put any friendly message in the 'message' field."),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        agent = create_tool_calling_agent(llm, tools, prompt_template)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
        
        result = agent_executor.invoke({"input": prompt})
        response_content = result["output"]
        
        try:
            # Clean up response content
            cleaned_response = response_content.strip()
            if "```json" in cleaned_response:
                cleaned_response = cleaned_response.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_response:
                cleaned_response = cleaned_response.split("```")[1].split("```")[0].strip()

            parsed_result = parser.parse(cleaned_response)
            
            # Post-validation: Ensure returned slots are actually in the legal_slots list
            # We create a set of signatures "start|end" for O(1) lookup
            legal_signatures = {f"{s['start']}|{s['end']}" for s in legal_slots}
            
            validated_slots = []
            for slot in parsed_result.slots:
                sig = f"{slot.start}|{slot.end}"
                if sig in legal_signatures:
                    validated_slots.append(slot.model_dump())
                else:
                    logger.warning("LLM hallucinated or modified a slot: %s", sig)
            
            # If LLM failed completely, fallback to top legal slots
            if not validated_slots:
                logger.warning("No valid slots returned by LLM. Falling back to raw legal slots.")
                validated_slots = legal_slots[:5]
                parsed_result.message += " (Note: I had trouble finding exact matches for your request, so here are the next available times.)"

            return {
                "suggested_slots": validated_slots,
                "ai_message": parsed_result.message,
                "llm_input": prompt,
                "llm_output": response_content
            }
        except Exception as e:
            logger.error("Failed to parse LLM response: %s", e)
            return {
                "error": "Failed to parse LLM response", 
                "details": str(e),
                "llm_input": prompt,
                "llm_output": response_content
            }
