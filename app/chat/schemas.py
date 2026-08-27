from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(min_length=1)
    session_id: str | None = Field(default=None, alias="sessionId")
    user_id: str = Field(default="guest", min_length=1, alias="userId")

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class MessageChunk(BaseModel):
    type: str = "message"
    content: str
    sessionId: str
    phase: str = "FINAL_SUMMARY"


class DoneChunk(BaseModel):
    type: str = "done"
    sessionId: str


class ErrorChunk(BaseModel):
    type: str = "error"
    error: str
    sessionId: str

