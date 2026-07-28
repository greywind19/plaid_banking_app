"""Plaid API client, configured from environment variables."""
import os
import plaid
from plaid.api import plaid_api
from dotenv import load_dotenv

load_dotenv()

_CLIENT_ID = os.getenv("PLAID_CLIENT_ID", "")
_SECRET = os.getenv("PLAID_SECRET", "")
_ENV = os.getenv("PLAID_ENV", "sandbox").lower()

if not _CLIENT_ID or not _SECRET:
    print(
        "[plaid] PLAID_CLIENT_ID / PLAID_SECRET are not set. "
        "Copy .env.example to .env and fill in your sandbox credentials."
    )

_HOSTS = {
    "sandbox": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}

_configuration = plaid.Configuration(
    host=_HOSTS.get(_ENV, plaid.Environment.Sandbox),
    api_key={"clientId": _CLIENT_ID, "secret": _SECRET},
)

_api_client = plaid.ApiClient(_configuration)
client = plaid_api.PlaidApi(_api_client)

SANDBOX_INSTITUTION_ID = os.getenv("SANDBOX_INSTITUTION_ID", "ins_109508")
