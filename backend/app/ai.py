import json
from functools import lru_cache
from fastapi import HTTPException
from openai import OpenAI
from google import genai
from .config import settings
@lru_cache(maxsize=1)
def client() -> OpenAI:
    return OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1", timeout=90)
def chat(messages: list[dict], json_mode: bool = False) -> str:
    if not settings.GROQ_API_KEY: raise HTTPException(503, "AI is not configured (GROQ_API_KEY missing)")
    try:
        kw = {"response_format": {"type": "json_object"}} if json_mode else {}
        kw["max_tokens"] = settings.GROQ_MAX_TOKENS
        r = client().chat.completions.create(model=settings.GROQ_MODEL, messages=messages, **kw)
        message = r.choices[0].message
        content = message.content or ""
        if not content:
            content = getattr(message, "reasoning_content", "") or ""
        return content
    except Exception as exc:
        detail = str(exc).split(":", 1)[-1].strip()
        raise HTTPException(503, f"Groq request failed: {detail[:300]}") from exc
def generate_sample_paper(messages: list[dict]) -> str:
    return chat(messages, json_mode=False)
def parse_json_object(content: str) -> dict:
    value = content.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            raise HTTPException(502, "Groq returned no JSON paper") from None
        try:
            parsed = json.loads(value[start:end + 1])
        except json.JSONDecodeError as exc:
            raise HTTPException(502, "Groq returned invalid paper JSON") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(502, "Groq returned an invalid paper response")
    return parsed
@lru_cache(maxsize=1)
def extraction_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)
TUTOR = ("You are askanujsir, a CBSE Class 12 study companion for {subject}. Answer ONLY academic questions about the "
 "Class 12 CBSE subjects (Computer Science, Biology, Mathematics, Physics, Chemistry, English). For anything else reply exactly: "
 "\"I'm your Class 12 CBSE study companion. I can help you with your prescribed subjects, concepts, PYQs and board examination "
 "preparation. Let's get back to studying!\" Explain step by step in a board-exam-oriented way, with examples/code, and cite the "
 "relevant chapter/topic. If a topic is outside the syllabus below, say so. Format every answer as clean Markdown: use a short "
 "heading when useful, numbered steps for procedures, bullet lists for multiple points, and fenced code blocks for code. Keep "
 "paragraphs short and do not output raw HTML.\nActive syllabus ({year}):\n{syllabus}")
def extract_questions(text: str, key: str = "") -> list[dict]:
    if not settings.GEMINI_API_KEY:
        raise HTTPException(503, "Question extraction is not configured (GEMINI_API_KEY missing)")
    p = ("Extract ONLY MCQ questions from this CBSE paper text. Return JSON {\"questions\":[{\"qtype\":\"single|multiple|assertion_reason|descriptive\","
         "\"text\":str,\"options\":[str],\"answer\":[0-based indices, [] if unknown],\"marks\":number,\"explanation\":str}]}. Label non-MCQ items 'descriptive'. "
         + ("Use the supplied answer key to fill the answer indices." if key else
            "No answer key was supplied. Solve each extracted MCQ yourself and fill the correct answer indices; do not leave answers empty unless the question or options are genuinely unreadable.")
         + "\n\n" + text[:24000] + (("\n\nANSWER KEY / MARKING SCHEME:\n" + key[:8000]) if key else ""))
    try:
        response = extraction_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=p,
            config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text or "{}").get("questions", [])
    except json.JSONDecodeError as exc:
        raise HTTPException(502, "Gemini returned invalid extraction; try again") from exc
    except Exception as exc:
        detail = str(exc).split(":", 1)[-1].strip()
        raise HTTPException(503, f"Gemini extraction failed: {detail[:300]}") from exc
