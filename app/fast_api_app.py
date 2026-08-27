# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import Runner

from app.app_utils import services
from app.chat.routes import router as chat_router
from app.chat.runtime import ChatRuntime
from app.medication.dependencies import close_medication_dependencies
from app.prediction.routes import router as prediction_router
from config.settings import settings


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app

    settings.validate_runtime()
    session_service = services.get_session_service()
    runner = Runner(
        app=adk_app,
        session_service=session_service,
        artifact_service=services.get_artifact_service(),
    )
    app.state.runner = runner
    app.state.chat_runtime = ChatRuntime(
        runner=runner,
        session_service=session_service,
        app_name=adk_app.name,
    )
    try:
        yield
    finally:
        await close_medication_dependencies()
        await services.close_services()


app = FastAPI(
    title="Medication Consultation Agent",
    description="Google ADK medication consultation with DeepSeek V4 Flash",
    version="1.0.0",
    lifespan=lifespan,
)
origins = [item.strip() for item in settings.ALLOW_ORIGINS.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)
app.include_router(prediction_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
