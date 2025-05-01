# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

default_env_vars = {
    "GOOGLE_GENAI_USE_VERTEXAI": "1",
    "GOOGLE_CLOUD_PROJECT": "YOUR_PROJECT_NAME",
    "GOOGLE_CLOUD_LOCATION": "us-central1",
    "BQ_PROJECT_ID": "YOUR_PROJECT_NAME",
    "BQ_DATASET_ID": "forecasting_sticker_sales",
    "BQML_RAG_CORPUS_NAME": "",
    "NL2SQL_METHOD": "BASELINE",
    "CODE_INTERPRETER_EXTENSION_NAME": "",
    "ROOT_AGENT_MODEL": "gemini-2.0-flash-001",
    "ANALYTICS_AGENT_MODEL": "gemini-2.0-flash-001",
    "BIGQUERY_AGENT_MODEL": "gemini-2.0-flash-001",
    "BASELINE_NL2SQL_MODEL": "gemini-2.0-flash-001",
    "CHASE_NL2SQL_MODEL": "gemini-2.0-flash-001",
    "BQML_AGENT_MODEL": "gemini-2.0-flash-001",
}

for key, default_value in default_env_vars.items():
    if os.environ.get(key) is None:
        os.environ[key] = default_value
        print(f"  Set '{key}'='{default_value}'")


from . import agent

__all__ = ["agent"]
