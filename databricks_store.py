from typing import Protocol

from databricks import sql


class ReleaseVersion(Protocol):
    repo: str
    tag_name: str
    url: str

    def published_date_iso(self) -> str: ...


class DatabricksReleaseStore:
    def __init__(
        self,
        server_hostname: str,
        http_path: str,
        access_token: str | None = None,
        auth_type: str | None = None,
    ):
        self.server_hostname = server_hostname
        self.http_path = http_path
        self.access_token = access_token
        self.auth_type = auth_type
        self._connection = None
        self._cursor = None

    def _connect_kwargs(self) -> dict:
        connect_kwargs = {
            "server_hostname": self.server_hostname,
            "http_path": self.http_path,
        }
        if self.access_token:
            connect_kwargs["access_token"] = self.access_token
        elif self.auth_type:
            connect_kwargs["auth_type"] = self.auth_type
        else:
            raise ValueError("Databricks auth is not configured. Provide access_token or auth_type.")
        return connect_kwargs

    def open_session(self):
        if self._connection is None:
            self._connection = sql.connect(**self._connect_kwargs())
            self._cursor = self._connection.cursor()

    def close_session(self):
        if self._cursor is not None:
            self._cursor.close()
            self._cursor = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self):
        self.open_session()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close_session()

    def _get_cursor(self):
        if self._cursor is None:
            self.open_session()
        if self._cursor is None:
            raise RuntimeError("Failed to create Databricks cursor")
        return self._cursor

    def merge_release(self, release: ReleaseVersion):
        published_date = release.published_date_iso()
        if not published_date:
            print(f"Skipping Databricks merge for {release.repo} {release.tag_name}: no publish date")
            return

        query = """
        MERGE INTO sdk.releases.versions AS target
        USING (
            SELECT
                ? AS repo,
                ? AS tag,
                CAST(? AS DATE) AS published_date,
                ? AS url
        ) AS source
        ON target.repo = source.repo AND target.tag = source.tag
        WHEN MATCHED THEN UPDATE SET
            target.published_date = source.published_date,
            target.url = source.url
        WHEN NOT MATCHED THEN INSERT (repo, tag, published_date, url)
        VALUES (source.repo, source.tag, source.published_date, source.url)
        """

        cursor = self._get_cursor()
        cursor.execute(
            query,
            (release.repo, release.tag_name, published_date, release.url),
        )

        print(f"Merged {release.repo} {release.tag_name} into Databricks")
