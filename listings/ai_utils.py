import json
import re

import google.generativeai as genai
from django.conf import settings

DEFAULT_SUGGESTIONS = [
    "What areas in Dhaka are affordable for renters?",
    "How do I compare two listings?",
    "What should I ask the landlord before signing?",
]


def get_gemini_response(prompt):
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return "Connect your API key in settings to see AI insights."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI is resting: {str(e)}"


def get_living_cost_estimate(city, rent):
    prompt = f"""
    Act as a local economic analyst in Bangladesh. 
    A user is planning to rent a home in {city} for ৳{rent}/month.
    
    Provide an estimated "Monthly Living Cost" for a standard household in this area.
    Include estimates for:
    1. Utilities (Electricity/Gas/Water)
    2. High-speed Internet
    3. Basic Groceries (for a family of 3)
    4. Local Transport
    
    Format as a clean breakdown with a 'Total Expected Budget' at the end. Keep it realistic for {city} standards. Under 100 words.
    """
    return get_gemini_response(prompt)


def get_neighborhood_insight(address, city):
    prompt = f"""
    Act as a high-end local lifestyle consultant in Bangladesh. 
    Analyze this specific location: {address}, {city}.
    
    Provide a "Creative Insider Report" for a potential tenant. 
    Use these 3 unique categories:
    1. THE VIBE: (Describe the personality of this specific road/area. Is it posh, artistic, noisy, or green?)
    2. THE COMMUTE TRUTH: (Be honest about the traffic or accessibility in this specific part of {city} during peak hours.)
    3. THE INSIDER SECRET: (Mention a specific type of shop, park, or local convenience that only people living there know about.)

    Keep the tone sophisticated, helpful, and "cool." Use bullet points. Under 120 words.
    """
    return get_gemini_response(prompt)


def generate_property_description(details):
    # (Existing logic kept for the button)
    prompt = f"Write a luxury real estate description for a {details.get('title')} in {details.get('city')}. Highlight {details.get('beds')} beds and amenities like {details.get('ac')}. Professional tone."
    return get_gemini_response(prompt)


def assistant_chat_reply(user_message: str) -> tuple[str, list[str]]:
    """
    Rental-focused assistant reply plus 3 suggested follow-up questions.
    Parses ANSWER / SUGGESTIONS blocks from model output; falls back gracefully.
    """
    prompt = f"""You are "Rental Finder Assistant" - help renters and landlords in Bangladesh with practical,
neutral advice (rent in BDT, neighborhoods, leases, deposits, viewing tips, listing basics).
Do not invent specific listings or prices; suggest users browse the site for properties.

User message:
{user_message}

Reply using EXACTLY this structure:

ANSWER:
(Your reply here - plain paragraphs, no markdown # headings. Under 200 words.)

SUGGESTIONS:
["First short follow-up question?", "Second question?", "Third question?"]

The SUGGESTIONS line must be valid JSON: exactly 3 strings, each under 72 characters.
"""
    raw = get_gemini_response(prompt)
    answer, suggestions = _parse_assistant_blocks(raw)
    if not suggestions:
        suggestions = list(DEFAULT_SUGGESTIONS)
    return answer, suggestions[:3]


def _parse_assistant_blocks(raw: str) -> tuple[str, list[str]]:
    text = (raw or "").strip()
    if not text:
        return "No response from AI.", []

    suggestions: list[str] = []
    answer = text

    if "SUGGESTIONS:" in text:
        parts = text.split("SUGGESTIONS:", 1)
        answer = parts[0].replace("ANSWER:", "").strip()
        tail = parts[1].strip()
        # Try JSON array first
        try:
            # grab first [...] block
            m = re.search(r"\[[\s\S]*?\]", tail)
            if m:
                suggestions = json.loads(m.group())
                if isinstance(suggestions, list):
                    suggestions = [str(s).strip() for s in suggestions if s]
        except (json.JSONDecodeError, TypeError, ValueError):
            suggestions = []

    elif "ANSWER:" in text:
        answer = text.split("ANSWER:", 1)[1].strip()

    # Strip accidental code fences
    answer = re.sub(r"^```[\w]*\n?", "", answer)
    answer = re.sub(r"\n?```$", "", answer).strip()

    return answer or text, suggestions
