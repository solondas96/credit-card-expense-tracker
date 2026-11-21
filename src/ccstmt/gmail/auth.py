"""Gmail OAuth and token management."""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_authenticated_service(credentials_path: Path, token_path: Path):
    """Get authenticated Gmail API service.

    Handles OAuth flow, token refresh, and invalid_grant errors.
    """
    creds = None

    # Load existing token if available
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh or get new token
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            if "invalid_grant" in str(e):
                raise ValueError(
                    "Gmail authorization expired (7-day limit on Testing-status app). "
                    "Run 'ccstmt auth' to re-authorize."
                ) from e
            raise

    # If no valid token, start OAuth flow
    if not creds or not creds.valid:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Google credentials not found at {credentials_path}. "
                "Download credentials.json from Google Cloud Console and save to secrets/"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), SCOPES
        )
        creds = flow.run_local_server(port=0)

        # Save the token for future runs
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


def get_authorized_email(creds: Credentials, service) -> str:
    """Get the email address of the authorized account."""
    try:
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception:
        return ""
