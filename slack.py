import urllib.request
from typing import List
from uuid import uuid4

from slackblocks import (
    ActionsBlock,
    Button,
    ContextBlock,
    DividerBlock,
    RawText,
    ResponseType,
    RichTextObject,
    SectionBlock,
    TableBlock,
    Text,
    WebhookMessage,
)

from github import GitHubRelease


def send_slack_notification(release: GitHubRelease, webhook_url: str, notion_page: str | None, linear_url: str | None):
    title = f"*{release.repo}*: _{release.tag_name}_ was released!"
    body = release.formatted_body

    blocks = [
            SectionBlock(
                text=title,
                accessory=Button(
                    text=":github: View Release",
                    url=release.url,
                    action_id=str(uuid4()),
                ),
            ),
            SectionBlock(
                text=body,
            ),
            ContextBlock(
                elements=[
                    Text(
                        text=f"Published {release.published_pretty}",
                    ),
                ]
            ),
            DividerBlock(),
        ]

    if len(release.assets) > 0:
        header: List[RawText | RichTextObject] = [RawText(text="Asset Name"), RawText(text="Size")]
        asset_rows: List[List[RawText | RichTextObject]] = [
            [RawText(text=asset.name), RawText(text=asset.size_mb)]
            for asset in release.assets
        ]
        rows: List[List[RawText | RichTextObject]] = [header] + asset_rows
        table_block = TableBlock(
            rows=rows,
        )
        blocks.append(table_block)

    actions = []
    if notion_page:
        actions.append(Button(
            text=":notion: View Notion Page",
            url=notion_page,
            action_id=str(uuid4()),
        ))
    if linear_url:
        actions.append(Button(
            text=":linear: View Linear Issue",
            url=linear_url,
            action_id=str(uuid4()),
        ))
    if len(actions) > 0:
        blocks.append(
            ActionsBlock(
                elements=actions
            )
        )

    message = WebhookMessage(
        response_type=ResponseType.IN_CHANNEL,
        blocks=blocks
    )

    # Run this through https://app.slack.com/block-kit-builder to verify formatting
    # print(message.json())
    data = message.json().encode("utf-8")

    if not webhook_url.startswith("https://hooks.slack.com"):
        raise ValueError("webhook_url must start with https://hooks.slack.com")

    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()

            if status_code != 200:
                response = response.read().decode("utf-8")

                raise Exception(f"Failed to send message to Slack > {status_code} {response}")
            else:
                print(f"Message was sent successfully > {message.text}")
    except urllib.error.HTTPError as e:
        raise Exception(f"Failed to send message to Slack > {e.code} {e.reason}")
