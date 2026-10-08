"""Deterministic text post-processing: spoken formatting commands and user replacements."""
import re

# Whisper writes commands with its own punctuation around them ("Hello. New line. Thanks."),
# so each pattern swallows the command and the punctuation Whisper put after it,
# keeping the punctuation that ends the sentence before it.
_COMMANDS = [
    (re.compile(r"\s*\bnew paragraph\b[,.!?;]?\s*", re.IGNORECASE), "\n\n"),
    (re.compile(r"\s*\b(?:new line|next line)\b[,.!?;]?\s*", re.IGNORECASE), "\n"),
]


def apply_voice_commands(text: str) -> str:
    for pattern, repl in _COMMANDS:
        text = pattern.sub(repl, text)
    # Capitalize the first letter after each inserted line break.
    return re.sub(r"(\n+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text).strip()


def apply_replacements(text: str, replacements: list[list[str]]) -> str:
    """Whole-word, case-insensitive 'spoken -> typed' replacements, e.g. 'my email' -> address."""
    for pair in replacements:
        if len(pair) != 2 or not pair[0].strip():
            continue
        spoken, typed = pair[0].strip(), pair[1]
        text = re.sub(rf"(?<!\w){re.escape(spoken)}(?!\w)", lambda _: typed, text, flags=re.IGNORECASE)
    return text


def word_count(text: str) -> int:
    return len(text.split())
