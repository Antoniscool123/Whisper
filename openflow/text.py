"""Conservative, deterministic text cleanup. Never rewrites meaning with an LLM."""
from __future__ import annotations

import re
from dataclasses import dataclass

# Deliberately do not remove words such as "like", "actually", or Danish "ligesom":
# they often carry meaning. These tokens are hesitations in the supported presets.
FILLERS = ("øhm", "øh", "ømm", "ehm", "erm", "umm", "uhh", "uh", "um")
COMMANDS = {
    "nyt afsnit": "\n\n", "new paragraph": "\n\n",
    "ny linje": "\n", "new line": "\n",
    "spørgsmålstegn": "?", "question mark": "?",
    "udråbstegn": "!", "exclamation mark": "!", "exclamation point": "!",
    "punktum": ".", "full stop": ".", "period": ".",
    "komma": ",", "comma": ",",
    "kolon": ":", "colon": ":",
    "semikolon": ";", "semicolon": ";",
}
_WORD = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class DictionaryRule:
    spoken: str
    written: str


def parse_dictionary(source: str) -> tuple[list[DictionaryRule], list[int]]:
    rules: list[DictionaryRule] = []
    invalid: list[int] = []
    seen: set[str] = set()
    for number, line in enumerate(source.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("=>")
        if len(parts) != 2:
            invalid.append(number)
            continue
        spoken, written = (part.strip() for part in parts)
        if not spoken or not written or len(spoken) > 120 or len(written) > 240 or spoken.casefold() in seen:
            invalid.append(number)
            continue
        seen.add(spoken.casefold())
        rules.append(DictionaryRule(spoken, written))
        if len(rules) >= 200:
            break
    return rules, invalid


def _case_like(match: re.Match[str], replacement: str) -> str:
    original = match.group(0)
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def tidy_text(source: str, *, fillers: bool = True, commands: bool = False,
              dictionary: str = "", language: str = "da") -> str:
    text = source.replace("\r\n", "\n").replace("\r", "\n").strip()
    # Remove Whisper's bracketed non-speech annotations, not ordinary parentheses.
    text = re.sub(r"\[(?:musik|music|applause|latter|laughter|silence|støj|noise)\]", "", text, flags=re.I)
    if commands:
        pattern = r"(?<!\w)(" + "|".join(re.escape(x) for x in sorted(COMMANDS, key=len, reverse=True)) + r")(?!\w)"
        text = re.sub(pattern, lambda m: COMMANDS[m.group(0).casefold()], text, flags=re.I)
        text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
    if fillers:
        # Anchoring to punctuation/edges avoids deleting a filler inside a word.
        pattern = r"(?<![\w])(" + "|".join(FILLERS) + r")(?:[ \t]*,[ \t]*|[ \t]+|(?=[.!?;:]|$))"
        text = re.sub(pattern, "", text, flags=re.I)
        text = re.sub(r"(^|[.!?]\s+)([,;:]\s*)+", r"\1", text)
    rules, _ = parse_dictionary(dictionary)
    if rules:
        mapping = {rule.spoken.casefold(): rule.written for rule in rules}
        pattern = r"(?<!\w)(" + "|".join(re.escape(x.spoken) for x in sorted(rules, key=lambda x: len(x.spoken), reverse=True)) + r")(?!\w)"
        text = re.sub(pattern, lambda m: _case_like(m, mapping[m.group(0).casefold()]), text, flags=re.I)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if text:
        text = text[:1].upper() + text[1:]
        text = re.sub(r"([.!?][ \t]+)(\w)", lambda m: m.group(1) + m.group(2).upper(), text)
        text = re.sub(r"(\n{2,})(\w)", lambda m: m.group(1) + m.group(2).upper(), text)
    return text


def word_count(text: str) -> int:
    return len(_WORD.findall(text))
