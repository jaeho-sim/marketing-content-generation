"""
GCS helpers — signed URL generation and object download.

Signed URL strategy
-------------------
generate_signed_url(version="v4") requires a signing key:

• Local dev with GOOGLE_APPLICATION_CREDENTIALS pointing to a service-account JSON:
  google.auth.default() returns ServiceAccountCredentials which sign locally.

• Cloud Run / GCE (ADC via metadata server):
  google.auth.default() returns ComputeEngineCredentials. After refreshing we
  pass service_account_email + access_token to generate_signed_url so the
  library delegates signing to the IAM signBlob API.
  Requires the Cloud Run SA to have roles/iam.serviceAccountTokenCreator on itself
  (self-signing), which Cloud Run grants by default.

• Local docker-compose (STORAGE_EMULATOR_HOST set):
  fake-gcs-server is used; we return a plain unsigned upload URL and use an
  anonymous client — no credentials needed at all.
"""
import datetime
import uuid
import google.auth
import google.auth.transport.requests
from google.cloud import storage
from app.config import get_settings

settings = get_settings()
_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


# ---------------------------------------------------------------------------
# Internal client factories
# ---------------------------------------------------------------------------

def _anon_client() -> storage.Client:
    """Anonymous client for the local fake-gcs-server emulator."""
    from google.auth.credentials import AnonymousCredentials
    return storage.Client(
        project=settings.gcs_project_id,
        credentials=AnonymousCredentials(),
        client_options={"api_endpoint": settings.storage_emulator_host},
    )


def _real_credentials_and_client() -> tuple[object, storage.Client]:
    """Return (refreshed_credentials, storage_client) for real GCS."""
    credentials, _ = google.auth.default(scopes=_SCOPES)
    credentials.refresh(google.auth.transport.requests.Request())
    client = storage.Client(project=settings.gcs_project_id, credentials=credentials)
    return credentials, client


def _client() -> storage.Client:
    return _anon_client() if settings.storage_emulator_host else _real_credentials_and_client()[1]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_media_gcs_key(event_id: uuid.UUID) -> str:
    return f"media/{event_id}/upload"


def generate_presigned_upload_url(gcs_key: str) -> str:
    """
    Returns a URL the producer can PUT their media file to directly.

    Emulator: plain unsigned URL pointing at fake-gcs-server (no signing needed).
    Real GCS: v4 signed URL valid for gcs_presigned_url_expiry_seconds.
    """
    if settings.storage_emulator_host:
        # Use the public host so the browser can reach the URL directly.
        public_host = settings.storage_emulator_public_host or settings.storage_emulator_host
        return (
            f"{public_host}/upload/storage/v1/b/"
            f"{settings.gcs_bucket_name}/o?uploadType=media&name={gcs_key}"
        )

    credentials, client = _real_credentials_and_client()
    blob = client.bucket(settings.gcs_bucket_name).blob(gcs_key)
    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(seconds=settings.gcs_presigned_url_expiry_seconds),
        method="PUT",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )


def download_to_file(gcs_key: str, dest_path: str) -> None:
    _client().bucket(settings.gcs_bucket_name).blob(gcs_key).download_to_filename(dest_path)


def delete_object(gcs_key: str) -> None:
    _client().bucket(settings.gcs_bucket_name).blob(gcs_key).delete()
