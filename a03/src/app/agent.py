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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.medication.skill_loader import load_medication_skill
from app.medication.tools import consult_medication
from config.settings import settings

gemini_model = Gemini(
    model="gemini-3.1-flash-lite",
    client_kwargs={"api_key": settings.GOOGLE_API_KEY},
    retry_options=types.HttpRetryOptions(
        attempts=3,
    ),
)


root_agent = Agent(
    name="medication_consultation_agent",
    description="Tu van thuoc co grounding tu Neo4j va du lieu Long Chau.",
    model=gemini_model,
    instruction=load_medication_skill(),
    tools=[consult_medication],
    output_key="final_summary",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
        max_output_tokens=4096,
        thinking_config=types.ThinkingConfig(
            thinking_level="medium",
        ),
    ),
)


app = App(
    root_agent=root_agent,
    name="app",
)
