from notion_client import Client as NotionClient

from github import GitHubRelease

# Notion caps each rich-text run's text content at 2000 characters.
NOTION_RICH_TEXT_LIMIT = 2000


def _rich_text_runs(content: str, limit: int = NOTION_RICH_TEXT_LIMIT):
    """Split content into multiple rich-text runs, each within Notion's per-run limit.

    Notion concatenates runs within a paragraph seamlessly, so this preserves the
    full text with no visible break and no data loss.
    """
    chunks = [content[i:i + limit] for i in range(0, len(content), limit)]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks] or [
        {"type": "text", "text": {"content": ""}}
    ]


def add_notion_database_row(release: GitHubRelease, notion_api_key: str):
    db_id = "2abbcf47-784e-80ab-bbaf-000b58a95a97"

    notion = NotionClient(auth=notion_api_key)
    page = notion.pages.create(
        parent={"data_source_id": db_id},
        properties={
            "Release": {
                "title": [
                    {
                        "text": {
                            "content": f"{release.platform_name} {release.tag_name}",
                        }
                    }
                ]
            },
            "SDK": {
                "select": {
                    "name": release.platform_name,
                }
            },
            "URL": {
                "url": release.url,
            },
            "Date": {
                "date": {
                    "start": release.published_date_iso(),
                }
            },
        },
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": _rich_text_runs(release.formatted_body),
                },
            }
        ],
    )

    return page.get("url")
