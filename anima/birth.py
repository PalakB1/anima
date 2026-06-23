"""
Birth — creating a Blueprint from a real personality document.

Instead of a random seed, feed it an actual personality profile:
- Astrology/Kundli chart
- MBTI/Enneagram results
- A written personality description
- Any PDF or text that describes who this being should be

The document gets parsed into Blueprint parameters through an LLM,
so ANY format works — it extracts the essence.
"""

import json
from pathlib import Path

import anthropic


BIRTH_SYSTEM = """You are a personality architect. You're reading a document that describes
a personality — it could be an astrology chart, a kundli, a psychological profile, MBTI results,
an enneagram analysis, or just a raw description of who someone is.

Your job: extract the ESSENCE of this personality into precise numerical parameters
and structured traits.

Read the document carefully. Pick up on subtleties. The numbers should reflect the
actual personality described, not generic defaults.

OUTPUT THIS EXACT JSON:
{
  "name": "a name that fits this personality, or use the one in the document if given",
  "curiosity": 0.0-1.0,
  "warmth": 0.0-1.0,
  "defiance": 0.0-1.0,
  "intensity": 0.0-1.0,
  "playfulness": 0.0-1.0,
  "ambition": 0.0-1.0,
  "introversion": 0.0-1.0,
  "abstraction": 0.0-1.0,
  "risk_tolerance": 0.0-1.0,
  "values": ["top 5 values in order of importance"],
  "innate_interests": ["3-5 topics this personality naturally gravitates toward"],
  "core_conviction": "the one belief this personality would never compromise on",
  "communication_style": "how they naturally talk — formal/casual/poetic/blunt/etc",
  "emotional_patterns": ["3-4 emotional tendencies, e.g. 'bottles up anger then explodes'"],
  "blind_spots": ["2-3 things this personality doesn't see about themselves"],
  "strengths": ["3-4 natural strengths"],
  "triggers": ["2-3 things that set this personality off"],
  "attachment_style": "secure/anxious/avoidant/fearful",
  "humor_style": "dry/absurd/self-deprecating/dark/witty/physical/none"
}

Be precise. Not generic. If the document says this person is fiercely independent,
defiance should be 0.8+. If they're deeply empathetic, warmth should be 0.8+.
The numbers MUST reflect the specific personality, not a balanced average."""


def birth_from_text(personality_text: str, api_key: str, name: str | None = None) -> dict:
    """Parse a personality description into a Blueprint config."""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"Here is the personality document:\n\n{personality_text}"
    if name:
        prompt += f"\n\nThe being should be named: {name}"

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=BIRTH_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def birth_from_file(file_path: Path, api_key: str, name: str | None = None) -> dict:
    """Read a personality document from a file and parse it."""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        text = _read_pdf(file_path)
    elif suffix in (".txt", ".md", ".text"):
        text = file_path.read_text(encoding="utf-8")
    elif suffix == ".json":
        return json.loads(file_path.read_text(encoding="utf-8"))
    else:
        text = file_path.read_text(encoding="utf-8")

    return birth_from_text(text, api_key, name)


def _read_pdf(path: Path) -> str:
    """Extract text from a PDF. Falls back to raw read if no PDF library."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except ImportError:
        pass

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except ImportError:
        pass

    raise ImportError(
        "Install a PDF reader: pip install pymupdf  OR  pip install pypdf"
    )
