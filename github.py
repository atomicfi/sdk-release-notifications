from datetime import datetime
from zoneinfo import ZoneInfo

from githubkit import GitHub
from githubkit.exception import RequestFailed
from githubkit.versions.latest.models import Release


class GitHubRelease:
    def __init__(self, release: Release, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        self.tag_name = release.tag_name
        self.body = release.body.replace('\r\n', '\n') if release.body else ""
        self.url = release.html_url
        self.published = release.published_at
        self.published_pretty = self._format_published_date(release.published_at)
        self.assets = [GitHubRelease.ReleaseAsset(asset) for asset in release.assets]
        self.platform_name = {
            "atomic-transact-ios": "iOS",
            "atomic-transact-android-public": "Android",
            "atomic-transact-react-native": "React Native",
            "atomic-transact-flutter": "Flutter",
        }.get(self.repo)
        self.formatted_body = f"# {self.platform_name} {self.tag_name}\n\n{self.body}"

    def _format_published_date(self, published_at) -> str:
        """Format the ISO8601 published date into a pretty string in Mountain Time."""
        if not published_at:
            return "Unknown date"

        # Parse the datetime and convert to Mountain Time
        dt = datetime.fromisoformat(str(published_at).replace('Z', '+00:00'))
        mt_dt = dt.astimezone(ZoneInfo("America/Denver"))

        # Use %Z to get the proper timezone abbreviation (MST/MDT)
        return mt_dt.strftime("%B %d, %Y at %I:%M %p %Z")

    def published_date_iso(self) -> str:
        """Get just the date portion of the published date in ISO format (YYYY-MM-DD)."""
        if not self.published:
            return ""

        # Parse the datetime and get just the date part
        dt = datetime.fromisoformat(str(self.published).replace('Z', '+00:00'))
        return dt.date().isoformat()

    def __str__(self) -> str:
        assets_str = "\n".join([f"    - {asset}" for asset in self.assets])
        body_text = str(self.body) if self.body else "No description"
        body_preview = body_text[:100] + ('...' if len(body_text) > 100 else '')
        return (
            f"GitHubRelease(\n"
            f"  Tag: {self.tag_name}\n"
            f"  Published: {self.published_pretty}\n"
            f"  Assets ({len(self.assets)}):\n{assets_str}\n"
            f"  Body: {body_preview}\n"
            f")"
        )

    def __repr__(self) -> str:
        return f"GitHubRelease(tag_name='{self.tag_name}', published={self.published}, assets_count={len(self.assets)})"

    class ReleaseAsset:
        def __init__(self, asset):
            self.name = asset.name
            self.download_url = asset.browser_download_url
            self.size = asset.size

        @property
        def size_mb(self) -> str:
            """Returns the size in megabytes as a formatted string."""
            mb = round(self.size / (1024 * 1024), 1) if self.size else 0.0
            return f"{mb} MB"

        def __str__(self) -> str:
            return f"{self.name} ({self.size_mb})"

        def __repr__(self) -> str:
            return f"ReleaseAsset(name='{self.name}', size={self.size})"


class GitHubClient:
    def __init__(self, token: str | None = None):
        if token:
            self.github = GitHub(token)
        else:
            self.github = GitHub()

    def get_release(self, owner: str, repo: str, tag: str | None) -> GitHubRelease:
        if tag:
            try:
                response = self.github.rest.repos.get_release_by_tag(owner=owner, repo=repo, tag=tag)
            except RequestFailed:
                response = self.github.rest.repos.get_latest_release(owner=owner, repo=repo)
        else:
            response = self.github.rest.repos.get_latest_release(owner=owner, repo=repo)
        release: Release = response.parsed_data
        return GitHubRelease(release=release, owner=owner, repo=repo)
