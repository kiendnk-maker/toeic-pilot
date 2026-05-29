# backend/llm_generator.py
# Generates similar TOEIC questions using Groq GPT-OSS-120B
# Supports explanations in Traditional Chinese (tw) and Vietnamese (vi)

import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_ID = "openai/gpt-oss-120b"

# Simple in-memory cache: grammar_point -> list of generated questions
_cache: dict[str, list[dict]] = {}
_cache_idx: dict[str, int] = {}

LANG_NAMES = {
    "tw": "繁體中文 (Traditional Chinese)",
    "vi": "Tiếng Việt (Vietnamese)",
}

SYSTEM_PROMPT = """You are a TOEIC Part 5 grammar expert and question writer.
Your task: Given an original TOEIC question and its grammar point, generate a NEW question testing the EXACT SAME grammar rule but with DIFFERENT vocabulary and context.

CRITICAL RULES:
1. The new question MUST test the same grammar rule (e.g., subjunctive mood, subject-verb agreement)
2. Use different nouns, verbs, and context (e.g., different company, different situation)
3. Keep TOEIC business English style
4. The explanation MUST be written in {lang_name}
5. Include a "say_it" sentence — the complete correct sentence for read-aloud practice

You MUST respond with ONLY valid JSON, no markdown, no code blocks:
{{
  "stem": "The committee recommended that the proposal ______ before Friday.",
  "options": ["reviews", "be reviewed", "reviewing", "was reviewed"],
  "correct_idx": 1,
  "explanation_native": "<explanation in {lang_name}>",
  "say_it": "The committee recommended that the proposal be reviewed before Friday.",
  "grammar_point": "<short grammar label in English>"
}}"""


def _extract_grammar_point(explanation: str) -> str:
    """Extract a short grammar label from the explanation text."""
    # Look for patterns like "After *asked that*" or "*Neither...nor*"
    import re
    patterns = re.findall(r'\*([^*]+)\*', explanation)
    if patterns:
        return patterns[0]
    # Fallback: first 50 chars
    return explanation[:50]


def _call_groq(prompt: str, system: str, max_retries: int = 3) -> dict | None:
    """Call Groq chat completions API with retry logic."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }

    delays = [1, 3, 5]
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                GROQ_CHAT_URL, headers=headers,
                json=payload, timeout=30
            )
            if resp.status_code == 429:
                # Rate limited
                wait = delays[min(attempt, len(delays) - 1)]
                print(f"[llm] Rate limited, retrying in {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # Parse JSON from response
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"[llm] JSON parse error: {e}")
            # Try to extract JSON from content
            try:
                import re
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    return json.loads(match.group())
            except Exception:
                pass
            continue
        except Exception as e:
            print(f"[llm] API error (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delays[min(attempt, len(delays) - 1)])
            continue

    return None


def generate_similar_question(
    original_stem: str,
    original_explanation: str,
    original_options: list[str],
    correct_idx: int,
    lang: str = "tw",
) -> dict | None:
    """
    Generate a similar TOEIC question using GPT-OSS-120B.

    Args:
        original_stem: The original question stem
        original_explanation: The original explanation
        original_options: The original answer options
        correct_idx: Index of correct answer
        lang: "tw" for Traditional Chinese, "vi" for Vietnamese

    Returns:
        dict with keys: stem, options, correct_idx, explanation_native, say_it, grammar_point
        or None if generation fails
    """
    if not GROQ_API_KEY:
        print("[llm] No GROQ_API_KEY configured")
        return None

    grammar_point = _extract_grammar_point(original_explanation)
    lang_name = LANG_NAMES.get(lang, LANG_NAMES["tw"])

    # Check cache
    cache_key = f"{grammar_point}_{lang}"
    if cache_key in _cache and _cache_idx.get(cache_key, 0) < len(_cache[cache_key]):
        idx = _cache_idx[cache_key]
        _cache_idx[cache_key] = idx + 1
        print(f"[llm] Cache hit for '{grammar_point}' ({lang}), idx={idx}")
        return _cache[cache_key][idx]

    # Build prompt
    correct_answer = original_options[correct_idx] if correct_idx < len(original_options) else "?"
    system = SYSTEM_PROMPT.replace("{lang_name}", lang_name)

    user_prompt = f"""Original TOEIC Question:
Stem: {original_stem}
Options: {json.dumps(original_options)}
Correct Answer: {correct_answer} (index {correct_idx})
Grammar Point: {grammar_point}
Explanation: {original_explanation}

Generate a NEW question testing the SAME grammar rule ({grammar_point}) with DIFFERENT context.
Write the explanation in {lang_name}."""

    result = _call_groq(user_prompt, system)

    if result:
        # Validate required fields
        required = ["stem", "options", "correct_idx", "explanation_native", "say_it"]
        if all(k in result for k in required):
            # Ensure options is a list of 4
            if isinstance(result["options"], list) and len(result["options"]) >= 4:
                result["options"] = result["options"][:4]
            else:
                return None

            # Ensure correct_idx is valid
            if not isinstance(result["correct_idx"], int) or result["correct_idx"] not in range(4):
                result["correct_idx"] = 0

            # Add grammar_point if missing
            if "grammar_point" not in result:
                result["grammar_point"] = grammar_point

            # Cache it
            if cache_key not in _cache:
                _cache[cache_key] = []
                _cache_idx[cache_key] = 0
            _cache[cache_key].append(result)
            # Keep cache bounded
            if len(_cache[cache_key]) > 20:
                _cache[cache_key] = _cache[cache_key][-10:]
                _cache_idx[cache_key] = 0

            return result

    print(f"[llm] Failed to generate question for '{grammar_point}'")
    return None


# Fallback: pre-translated explanations for common grammar points
FALLBACK_EXPLANATIONS = {
    "tw": {
        "asked that": "在 'ask that' 後面，動詞要用原形（不加 -s）。這是虛擬語氣的用法。",
        "Neither...nor": "'Neither...nor' 的動詞要和最近的主詞一致。",
        "which": "逗號後面的 'which' 引導非限制性子句，用來補充說明整個句子。",
        "on": "星期幾前面要用介詞 'on'。例如：on Monday, on Friday。",
    },
    "vi": {
        "asked that": "Sau 'ask that', động từ phải ở dạng nguyên mẫu (không thêm -s). Đây là thể giả định.",
        "Neither...nor": "'Neither...nor' chia động từ theo chủ ngữ gần nhất.",
        "which": "Dấu phẩy trước 'which' tạo mệnh đề quan hệ không hạn định, bổ nghĩa cho cả câu.",
        "on": "Dùng giới từ 'on' trước các ngày trong tuần. Ví dụ: on Monday, on Friday.",
    },
}
