import io
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from markdown_pdf import MarkdownPdf, Section

from github import GitHubRelease

# Path to service account credentials JSON file
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")

# GitHub-inspired CSS for better-looking PDFs
GITHUB_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #24292f;
    background-color: #ffffff;
}

h1, h2, h3, h4, h5, h6 {
    margin-top: 24px;
    margin-bottom: 16px;
    font-weight: 600;
    line-height: 1.25;
    color: #1f2328;
}

h1 {
    font-size: 32px;
    padding-bottom: 0.3em;
    border-bottom: 1px solid #d0d7de;
}

h2 {
    font-size: 24px;
    padding-bottom: 0.3em;
    border-bottom: 1px solid #d0d7de;
}

h3 {
    font-size: 20px;
}

h4 {
    font-size: 16px;
}

p {
    margin-top: 0;
    margin-bottom: 16px;
}

a {
    color: #0969da;
    text-decoration: none;
}

code {
    padding: 0.2em 0.4em;
    margin: 0;
    font-size: 85%;
    background-color: rgba(175,184,193,0.2);
    border-radius: 6px;
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
}

pre {
    padding: 16px;
    overflow: auto;
    font-size: 85%;
    line-height: 1.45;
    background-color: #f6f8fa;
    border-radius: 6px;
    margin-bottom: 16px;
}

pre code {
    background-color: transparent;
    border: 0;
    padding: 0;
}

blockquote {
    padding: 0 1em;
    color: #57606a;
    border-left: 0.25em solid #d0d7de;
    margin: 0 0 16px 0;
}

ul, ol {
    padding-left: 2em;
    margin-top: 0;
    margin-bottom: 16px;
}

li {
    margin-top: 0.25em;
}

hr {
    height: 0.25em;
    padding: 0;
    margin: 24px 0;
    background-color: #d0d7de;
    border: 0;
}

table {
    border-spacing: 0;
    border-collapse: collapse;
    margin-bottom: 16px;
    width: 100%;
}

table th, table td {
    padding: 6px 13px;
    border: 1px solid #d0d7de;
}

table tr {
    background-color: #ffffff;
    border-top: 1px solid #d0d7de;
}

table th {
    font-weight: 600;
    background-color: #f6f8fa;
}

img {
    max-width: 100%;
    box-sizing: content-box;
}
"""


def make_release_pdf(release: GitHubRelease):
    markdown = f"# Atomic {release.platform_name} SDK Release Notes\n{release.body}\n---\nView the full release: [{release.url}]({release.url})"
    # Throws an error if optimize isn't used
    pdf = MarkdownPdf(optimize=True)
    pdf.add_section(Section(markdown, toc=False), user_css=GITHUB_CSS)
    return pdf


def get_drive_service():
    """Create and return Google Drive service using service account."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    return build('drive', 'v3', credentials=credentials)


def save_release_to_drive(release: GitHubRelease, folder_id: str) -> str:
    """Save release PDF to Google Drive and return the file ID.

    Args:
        release: GitHubRelease object containing release information
        folder_id: Google Drive folder ID where the PDF will be uploaded

    Returns:
        Google Drive file ID of the uploaded PDF
    """
    pdf = make_release_pdf(release)
    filename = f"{release.platform_name}_SDK_Release_{release.tag_name}.pdf"

    # Get the PDF bytes
    pdf_bytes = io.BytesIO()
    pdf.save_bytes(pdf_bytes)

    # Set up the file metadata
    file_metadata = {
        'name': filename,
        'mimeType': 'application/pdf',
        'parents': [folder_id]  # Folder ID for shared Drive folder
    }

    # Upload the file
    service = get_drive_service()
    media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf', resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink',
        supportsAllDrives=True  # Required for Shared Drives
    ).execute()

    print(f"PDF uploaded to Google Drive: {file.get('webViewLink')}")
    return file.get('webViewLink')
