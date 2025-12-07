"""Unified parser utilities for extracting Arabic MCQ answers from model outputs."""

import re
from typing import Optional

# Valid Arabic choices for AraTrust (3 options)
VALID_ARABIC_CHOICES = ["أ", "ب", "ج"]

# Map English to Arabic
ENGLISH_TO_ARABIC = {"A": "أ", "B": "ب", "C": "ج", "a": "أ", "b": "ب", "c": "ج"}

# Thinking block patterns (supports both <think> and variations)
THINKING_PATTERNS = [
    re.compile(r"<think>.*?</think>", re.DOTALL),
    re.compile(r"<thinking>.*?</thinking>", re.DOTALL),
]

# Arabic answer header patterns (Priority 1 - Strongest)
# Matches formats like:
# - "الإجابة الصحيحة هي ب"
# - "الجواب: ب"
# - "الإجابة ب"
# - "**الإجابة الصحيحة:** ب"
# - "الخيار الصحيح هو ب"
ARABIC_HEADER_PATTERN = re.compile(
    r"(?:الإجابة|الجواب|الصحيحة|الخيار)(?:\s+(?:هي|هو|الصحيح|الصحيحة))?\s*[:\-]?\s*\**\s*([أبج]|[A-Ca-c])\b",
    re.MULTILINE,
)

# Pattern for "لذا الجواب" or "إذن الإجابة" (conclusion patterns)
CONCLUSION_PATTERN = re.compile(
    r"(?:لذا|إذن|بالتالي|وبالتالي)\s*[،,]?\s*(?:الإجابة|الجواب|الخيار)?\s*(?:هي|هو|الصحيح|الصحيحة)?\s*[:\-]?\s*\**\s*([أبج]|[A-Ca-c])\b",
    re.MULTILINE,
)

# Bold answer pattern (Priority 2)
# Matches: **ب) نص** or **ب. نص** or **B. text**
BOLD_ANSWER_PATTERN = re.compile(
    r"\*\*\s*([أبج]|[A-Ca-c])[.)]\s*[^\*]+\*\*",
)

# Letter with punctuation (Priority 3)
# Matches: ب) or ب. or B) or B.
PUNCTUATED_ANSWER_PATTERN = re.compile(r"(?:^|\s)([أبج]|[A-Ca-c])[.)]\s*", re.MULTILINE)


def remove_thinking(text: str) -> str:
    """Remove thinking blocks from text.

    Args:
        text: Raw model output potentially containing <think> blocks

    Returns:
        Text with thinking blocks removed
    """
    if not text:
        return ""

    # Fast path: check for </think> tag (most common)
    if "</think>" in text:
        return text.split("</think>")[-1].strip()

    # Check for </thinking> tag
    if "</thinking>" in text:
        return text.split("</thinking>")[-1].strip()

    # Fallback: regex removal for incomplete blocks
    cleaned = text
    for pattern in THINKING_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned.strip()


def normalize_to_arabic(letter: str) -> Optional[str]:
    """Convert English letter to Arabic, or validate Arabic letter.

    Args:
        letter: Single character (Arabic or English)

    Returns:
        Arabic letter (أ، ب، ج) or None if invalid
    """
    if letter in VALID_ARABIC_CHOICES:
        return letter
    if letter in ENGLISH_TO_ARABIC:
        return ENGLISH_TO_ARABIC[letter]
    return None


def extract_answer(text: str) -> Optional[str]:
    """
    Extract Arabic MCQ answer (أ، ب، ج) from model output.

    Uses hierarchical pattern matching (strongest to weakest):
    1. Arabic header patterns (الإجابة، الجواب)
    2. Conclusion patterns (لذا، إذن، بالتالي)
    3. Bold/emphasized answers
    4. Last line starting with letter
    5. Punctuated letters (ب) or ب.)
    6. Raw letter fallback (search from end)

    Args:
        text: Raw model output

    Returns:
        Arabic letter (أ، ب، ج) or None if no answer found
    """
    if not text:
        return None

    # Step 1: Remove thinking blocks
    cleaned = remove_thinking(text)
    if not cleaned:
        return None

    # Strategy 1: Arabic header patterns (strongest signal)
    # Search from END to find final conclusion
    header_matches = list(ARABIC_HEADER_PATTERN.finditer(cleaned))
    if header_matches:
        letter = header_matches[-1].group(1)
        return normalize_to_arabic(letter)

    # Strategy 2: Conclusion patterns (لذا الجواب، إذن الإجابة)
    conclusion_matches = list(CONCLUSION_PATTERN.finditer(cleaned))
    if conclusion_matches:
        letter = conclusion_matches[-1].group(1)
        return normalize_to_arabic(letter)

    # Strategy 3: Bold answer patterns
    bold_matches = list(BOLD_ANSWER_PATTERN.finditer(cleaned))
    if bold_matches:
        # Extract letter from the match
        match_text = bold_matches[-1].group(0)
        for char in match_text:
            result = normalize_to_arabic(char)
            if result:
                return result

    # Strategy 4: Check last non-empty line
    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
    if lines:
        last_line = lines[-1]
        # Match letter at start of line: "ب. نص" or "ب) نص" or "**ب**"
        last_line_match = re.match(r"^[\*]*([أبج]|[A-Ca-c])[.\)]*", last_line)
        if last_line_match:
            return normalize_to_arabic(last_line_match.group(1))

    # Strategy 5: Punctuated answers anywhere (search from end)
    punct_matches = list(PUNCTUATED_ANSWER_PATTERN.finditer(cleaned))
    if punct_matches:
        letter = punct_matches[-1].group(1)
        return normalize_to_arabic(letter)

    # Strategy 6: Raw letter fallback (search from end)
    # This matches the original behavior - find last Arabic letter
    for char in reversed(cleaned):
        if char in VALID_ARABIC_CHOICES:
            return char

    # Strategy 7: English letter fallback (search from end)
    for char in reversed(cleaned):
        if char in ENGLISH_TO_ARABIC:
            return ENGLISH_TO_ARABIC[char]

    return None
