from functools import cache
from pathlib import Path

_SKILL_PATH = (
    Path(__file__).resolve().parents[2]
    / "skill"
    / "medication_consultation"
    / "SKILL.md"
)


@cache
def load_medication_skill() -> str:
    instruction = _SKILL_PATH.read_text(encoding="utf-8").strip()
    if not instruction:
        raise RuntimeError(f"Medication skill is empty: {_SKILL_PATH}")
    return instruction

