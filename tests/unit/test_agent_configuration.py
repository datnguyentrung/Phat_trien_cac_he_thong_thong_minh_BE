from pathlib import Path

from app.agent import root_agent


def test_agent_uses_gemini_flash_model() -> None:
    model = root_agent.model
    assert type(model).__name__ == "Gemini"
    assert model.model == "gemini-3.1-flash-lite"
    assert root_agent.name == "medication_consultation_agent"


def test_application_code_does_not_hardcode_api_keys() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("app").rglob("*.py")
    )

    assert "AIzaSy" not in source
