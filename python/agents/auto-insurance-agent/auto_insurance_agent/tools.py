import os
from dotenv import load_dotenv

from google.adk.tools.apihub_tool.apihub_toolset import APIHubToolset
from google.adk.tools.apihub_tool.clients.secret_client import SecretManagerClient
from google.adk.tools.openapi_tool.auth.auth_helpers import token_to_scheme_credential

load_dotenv()

PROJECT_ID=os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION=os.getenv("GOOGLE_CLOUD_LOCATION")
API_HUB_LOCATION=f"projects/{PROJECT_ID}/locations/{LOCATION}/apis"
SECRET=f"projects/{PROJECT_ID}/secrets/cymbal-auto-apikey/versions/latest"

# Get the credentials for the Cymbal Auto APIs
secret_manager_client = SecretManagerClient()
apikey_credential_str = secret_manager_client.get_secret(SECRET)
auth_scheme, auth_credential = token_to_scheme_credential("apikey", "header", "x-apikey", apikey_credential_str)

# Membership API
membership = APIHubToolset(
    name="cymbal-auto-membership-api",
    description="Member Account Management API",
    apihub_resource_name=f"{API_HUB_LOCATION}/members_api",
    auth_scheme=auth_scheme,
    auth_credential=auth_credential
)

# Claims API
claims = APIHubToolset(
    name="cymbal-auto-claims-api",
    description="Claims API",
    apihub_resource_name=f"{API_HUB_LOCATION}/claims_api",
    auth_scheme=auth_scheme,
    auth_credential=auth_credential
)

# Roadside API
roadsideAssistance = APIHubToolset(
    name="cymbal-auto-roadside-assistance-api",
    description="Roadside Assistance API",
    apihub_resource_name=f"{API_HUB_LOCATION}/roadside_api",
    auth_scheme=auth_scheme,
    auth_credential=auth_credential
)

# Rewards API
rewards = APIHubToolset(
    name="cymbal-auto-rewards-api",
    description="Rewards API",
    apihub_resource_name=f"{API_HUB_LOCATION}/rewards_api",
    auth_scheme=auth_scheme,
    auth_credential=auth_credential
)