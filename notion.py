from notion_client import Client as NotionClient

from github import GitHubRelease


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
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": release.formatted_body,
                            },
                        }
                    ]
                },
            }
        ],
    )

    return page.get("url")
