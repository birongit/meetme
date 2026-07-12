import json
import logging
import os
import random
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain.output_parsers import PydanticOutputParser

from app.core.config import settings
from app.models.schemas import SlotList
from app.services.preferences import PreferencesService
from app.services.calendar import CalendarService

logger = logging.getLogger(__name__)

def _langfuse_enabled() -> bool:
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))

# SDK 3.x only reads LANGFUSE_HOST and silently falls back to the EU
# endpoint; accept the LANGFUSE_BASE_URL name from newer docs too
if os.environ.get("LANGFUSE_BASE_URL") and not os.environ.get("LANGFUSE_HOST"):
    os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]

if _langfuse_enabled():
    from langfuse import observe, get_client
    from langfuse.langchain import CallbackHandler
else:
    # No-op stand-ins so the module works without Langfuse credentials
    def observe(**okwargs):
        def deco(fn):
            return fn
        return deco
    get_client = None
    CallbackHandler = None

def get_langfuse_handler():
    """Returns a Langfuse callback handler, or None if credentials aren't configured."""
    if CallbackHandler is None:
        return None
    try:
        return CallbackHandler()
    except Exception as e:
        logger.warning("Langfuse tracing disabled: %s", e)
        return None

def _lf():
    """Returns the Langfuse client, or None if disabled."""
    return get_client() if get_client else None

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
    @observe(name="rank-slots", capture_input=False, capture_output=False)
    def rank_slots(legal_slots: List[Dict[str, str]], user_feedback: str = None, user_tz: str = None, session_id: str = None) -> Dict[str, Any]:
        """
        Uses LLM to rank and select the best slots based on user feedback and preferences.
        """
        base_tags = [
            "feedback-round" if user_feedback else "initial-round",
            f"model:{settings.GEMINI_MODEL}",
        ]
        lf = _lf()
        if lf:
            # capture_input=False above: the raw args include the full slot
            # list; set a readable trace input explicitly instead
            lf.update_current_trace(
                session_id=session_id,
                tags=base_tags,
                input={
                    "user_feedback": user_feedback,
                    "user_tz": user_tz,
                    "num_legal_slots": len(legal_slots),
                },
            )
        # Collect any extra slots fetched by the agent tool
        extra_fetched_slots: List[Dict[str, str]] = []

        @tool
        def fetch_available_slots(start_date: str, end_date: str) -> str:
            """Fetch available 1-hour meeting slots for any date range, including weeks or months in the future.
            The range between start_date and end_date can be up to 14 days per call.
            Args:
                start_date: Start date in YYYY-MM-DD format (can be any future date)
                end_date: End date in YYYY-MM-DD format (up to 14 days after start_date)
            Returns:
                A text list of available slots in the requested range.
            """
            slots = CalendarService.get_available_slots(user_tz, start_date, end_date)
            extra_fetched_slots.extend(slots)
            if not slots:
                return "No available slots found in that date range."
            return "\n".join(f"- {s['start']} to {s['end']}" for s in slots)

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
        json_hint = 'Return JSON: {"slots": [{"start": "...", "end": "..."}], "message": "..."}'

        user_request_str = "User Request (The user is asking for this):\n"
        if user_feedback:
            user_request_str += f"- '{user_feedback}'\n"
        else:
            user_request_str += "- (No specific request)\n"

        if user_feedback:
            # Round 2: bare-bones — just fetch and return slots
            prompt = (
                f"Today is {datetime.now().strftime('%Y-%m-%d (%A)')}.\n\n"
                f"{user_request_str}\n"
                "Call fetch_available_slots for the relevant date range, then select 5-10 of the best options and return them as JSON: "
                '{"slots": [{"start": "...", "end": "..."}], "message": "..."}'
            )
        else:
            # Round 1: Provide pre-loaded slots for quick selection
            prompt = (
                f"Today is {datetime.now().strftime('%Y-%m-%d (%A)')}.\n\n"
                f"{user_request_str}\n"
                f"{owner_prefs_str}\n"
                f"Available slots:\n"
                f"{slot_list_str}\n\n"
                "Select and rank 5-10 diverse options. Address the user directly in the message field, explain why the slots match their request, and be friendly.\n"
                f"{json_hint}"
            )

        tools = [get_days_of_week, fetch_available_slots]

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful booking assistant. Use your tools to find information you need. Return the result as a JSON object matching the specified format."),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        def run_agent(temperature: float, attempt: int):
            llm = ChatGoogleGenerativeAI(
                google_api_key=settings.GOOGLE_AI_API_KEY,
                model=settings.GEMINI_MODEL,
                temperature=temperature,
                # Fail fast: default retry backoff (~62s) exceeds Heroku's 30s router timeout
                max_retries=2,
            )
            agent = create_tool_calling_agent(llm, tools, prompt_template)
            agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)
            invoke_config = {"run_name": f"agent-attempt-{attempt}"}
            langfuse_handler = get_langfuse_handler()
            if langfuse_handler:
                invoke_config["callbacks"] = [langfuse_handler]
            return agent_executor.invoke({"input": prompt}, config=invoke_config)

        result = run_agent(temperature=0, attempt=1)
        if not str(result.get("output", "")).strip():
            # Known gemini-2.5-flash-lite regression: empty completion after a
            # tool result. Retry with temperature to escape the deterministic
            # failure for this exact input.
            logger.warning("LLM returned empty output; retrying with temperature=0.7")
            if lf:
                lf.update_current_trace(tags=base_tags + ["retry-empty-output"])
            result = run_agent(temperature=0.7, attempt=2)

        response_content = result["output"]
        intermediate_steps = result.get("intermediate_steps", [])

        # Log intermediate steps for debugging
        agent_steps = []
        for step in intermediate_steps:
            action, observation = step
            step_info = {"tool": action.tool, "input": action.tool_input, "output": str(observation)}
            agent_steps.append(step_info)
            logger.info("Agent tool call: %s(%s) -> %s", action.tool, action.tool_input, str(observation)[:200])

        try:
            # Clean up response content
            cleaned_response = response_content.strip()
            if "```json" in cleaned_response:
                cleaned_response = cleaned_response.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_response:
                cleaned_response = cleaned_response.split("```")[1].split("```")[0].strip()

            try:
                parsed_result = parser.parse(cleaned_response)
            except Exception:
                # Some models prefix the JSON with prose; extract the first
                # parseable JSON object from the response instead
                json_start = cleaned_response.find('{')
                if json_start == -1:
                    raise
                obj, _ = json.JSONDecoder().raw_decode(cleaned_response[json_start:])
                parsed_result = SlotList(**obj)

            # Post-validation: Ensure returned slots are actually in the legal_slots list
            # Include any extra slots fetched by the agent tool
            all_legal_slots = legal_slots + extra_fetched_slots
            legal_signatures = {f"{s['start']}|{s['end']}" for s in all_legal_slots}

            # Determine the boundary of pre-loaded slots
            preloaded_max = max(s['start'] for s in legal_slots) if legal_slots else ""

            validated_slots = []
            out_of_range_dates = set()
            for slot in parsed_result.slots:
                sig = f"{slot.start}|{slot.end}"
                if sig in legal_signatures:
                    validated_slots.append(slot.model_dump())
                elif slot.start > preloaded_max:
                    # Slot is beyond the 7-day window — collect its date for fetching
                    out_of_range_dates.add(slot.start[:10])
                else:
                    logger.warning("LLM hallucinated or modified a slot: %s", sig)

            # Fetch and validate any out-of-range slots the LLM suggested
            if out_of_range_dates:
                sorted_dates = sorted(out_of_range_dates)
                start_date = sorted_dates[0]
                end_date = (datetime.strptime(sorted_dates[-1], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                logger.info("Fetching slots for LLM-suggested range: %s to %s", start_date, end_date)
                fetched = CalendarService.get_available_slots(user_tz, start_date, end_date)
                all_legal_slots = all_legal_slots + fetched

                # Build a set of (start_dt, end_dt) for datetime-based comparison
                # to avoid timezone offset mismatches (e.g. LLM says -08:00 but DST means -07:00)
                fetched_dt = {
                    (datetime.fromisoformat(s['start']), datetime.fromisoformat(s['end']))
                    for s in fetched
                }

                for slot in parsed_result.slots:
                    if slot.start[:10] in out_of_range_dates:
                        llm_start = datetime.fromisoformat(slot.start)
                        llm_end = datetime.fromisoformat(slot.end)
                        if (llm_start, llm_end) in fetched_dt:
                            validated_slots.append(slot.model_dump())
                        else:
                            # Find the closest matching slot by start time
                            for fs, fe in fetched_dt:
                                if fs.date() == llm_start.date() and fs.hour == llm_start.hour:
                                    validated_slots.append({"start": fs.isoformat(), "end": fe.isoformat()})
                                    break

            # If LLM failed completely, fallback to top legal slots
            if not validated_slots:
                logger.warning("No valid slots returned by LLM. Falling back to raw legal slots.")
                validated_slots = all_legal_slots[:5]
                parsed_result.message += " (Note: I had trouble finding exact matches for your request, so here are the next available times.)"

            if lf:
                lf.score_current_trace(name="llm_success", value=1, data_type="BOOLEAN")
                lf.update_current_trace(output={"num_slots": len(validated_slots), "fallback": False})
            return {
                "suggested_slots": validated_slots,
                "ai_message": parsed_result.message,
                "llm_input": prompt,
                "llm_output": response_content,
                "agent_steps": agent_steps
            }
        except Exception as e:
            # The LLM is a ranking enhancement, not a dependency: if its output
            # is unusable even after the retry, serve a random sample of legal
            # slots so the visitor can still book. Marked llm_fallback for
            # log/trace searching — the user sees a normal response.
            logger.error(
                "LLM_FALLBACK: unusable LLM output after retry (%s); serving random slot sample. Raw output: %r",
                e, str(response_content)[:500],
            )
            if lf:
                reason = "empty_output" if not str(response_content).strip() else "unparseable_output"
                comment = f"{e}; raw output: {str(response_content)[:300]!r}"
                lf.score_current_trace(name="llm_success", value=0, data_type="BOOLEAN", comment=comment)
                lf.score_current_trace(name="llm_failure_reason", value=reason, data_type="CATEGORICAL", comment=comment)
                lf.update_current_trace(output={"num_slots": None, "fallback": True, "reason": reason})
            all_legal_slots = legal_slots + extra_fetched_slots
            sample = random.sample(all_legal_slots, min(7, len(all_legal_slots)))
            sample.sort(key=lambda s: s['start'])
            return {
                "suggested_slots": sample,
                "ai_message": "Here are some available times — pick whichever works best for you!",
                "llm_input": prompt,
                "llm_output": response_content,
                "agent_steps": agent_steps,
                "llm_fallback": str(e),
            }
