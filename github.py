from datetime import date, datetime
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
            "atomic-transact-capacitor": "Capacitor"
        }.get(self.repo)
        self.linear_releases_url = {
            "atomic-transact-ios": "https://linear.app/atomicbuilt/pipeline/ios/releases",
            "atomic-transact-android-public": "https://linear.app/atomicbuilt/pipeline/android-sdk/releases",
            "atomic-transact-react-native": "https://linear.app/atomicbuilt/pipeline/react-native-sdk/releases",
            "atomic-transact-flutter": "https://linear.app/atomicbuilt/pipeline/flutter-sdk/releases",
            "atomic-transact-capacitor": "https://linear.app/atomicbuilt/pipeline/capacitor-sdk/releases",
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


class GitHubTag:
    def __init__(self, owner: str, repo: str, tag_name: str, published: str):
        self.owner = owner
        self.repo = repo
        self.tag_name = tag_name
        self.published = published
        self.url = f"https://github.com/{owner}/{repo}/tree/{tag_name}"

    def published_date_iso(self) -> str:
        if not self.published:
            return ""

        dt = datetime.fromisoformat(str(self.published).replace('Z', '+00:00'))
        return dt.date().isoformat()

    def __str__(self) -> str:
        return f"GitHubTag(tag_name='{self.tag_name}', published='{self.published_date_iso()}')"

    def __repr__(self) -> str:
        return str(self)


class GitHubClient:
    def __init__(self, token: str | None = None):
        if token:
            self.github = GitHub(token)
        else:
            self.github = GitHub()

    def get_all_releases(self, owner: str, repo: str) -> list[GitHubRelease]:
        releases = []
        try:
            response = self.github.rest.repos.list_releases(owner=owner, repo=repo)
            for release in response.parsed_data:
                releases.append(GitHubRelease(release=release, owner=owner, repo=repo))
        except RequestFailed as e:
            print(f"Failed to fetch releases for {owner}/{repo}: {e}")
        return releases

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

    def get_tags_before_date(self, owner: str, repo: str, before_date_iso: str) -> list[GitHubTag]:
        cutoff_date = date.fromisoformat(before_date_iso)
        tags: list[GitHubTag] = []

        page = 1
        while True:
            try:
                response = self.github.rest.repos.list_tags(owner=owner, repo=repo, page=page, per_page=100)
            except RequestFailed as e:
                print(f"Failed to fetch tags for {owner}/{repo} on page {page}: {e}")
                break

            page_tags = list(response.parsed_data)
            if not page_tags:
                break

            print(len(page_tags))
            for tag in page_tags:
                try:
                    commit_response = self.github.rest.repos.get_commit(owner=owner, repo=repo, ref=tag.commit.sha)
                    commit_data = commit_response.parsed_data
                    committer = commit_data.commit.committer
                    author = commit_data.commit.author
                    commit_date = (committer.date if committer else None) or (author.date if author else None)
                    print(commit_date)
                    if not commit_date:
                        continue

                    published_date = datetime.fromisoformat(str(commit_date).replace('Z', '+00:00')).date()
                    if published_date >= cutoff_date:
                        continue

                    tags.append(
                        GitHubTag(
                            owner=owner,
                            repo=repo,
                            tag_name=tag.name,
                            published=str(commit_date),
                        )
                    )
                except RequestFailed as e:
                    print(f"Failed to fetch commit for tag {tag.name} in {owner}/{repo}: {e}")

            page += 1

        return tags
