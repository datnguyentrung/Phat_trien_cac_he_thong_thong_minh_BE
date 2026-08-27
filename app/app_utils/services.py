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

"""Process-wide ADK services for the HTTP serving surface."""

from __future__ import annotations

import functools
from pathlib import Path

from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import DatabaseSessionService

from config.settings import PROJECT_ROOT, settings


@functools.cache
def get_session_service():
    """Return the persistent SQLite-backed ADK session service."""
    data_dir = Path(PROJECT_ROOT) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return DatabaseSessionService(db_url=settings.SESSION_DB_URL)


@functools.cache
def get_artifact_service():
    """Return in-memory artifacts; this agent does not create files."""
    return InMemoryArtifactService()


async def close_services() -> None:
    """Release persistent ADK resources created by this process."""
    if get_session_service.cache_info().currsize:
        await get_session_service().close()
    get_session_service.cache_clear()
    get_artifact_service.cache_clear()
