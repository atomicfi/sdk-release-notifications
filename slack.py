from uuid import uuid4

import requests
from slackblocks.blocks import (
    ActionsBlock,
    Block,
    ContextBlock,
    DividerBlock,
    MarkdownBlock,
    SectionBlock,
    TableBlock,
)
from slackblocks.elements import Button
from slackblocks.messages import ResponseType, WebhookMessage
from slackblocks.objects import RawText, Text
from slackblocks.rich_text.objects import RichTextObject

from github import GitHubRelease

# Slack caps the cumulative text of Markdown blocks in a message at 12,000 characters.
SLACK_MARKDOWN_TEXT_LIMIT = 12_000
# Slack section blocks cap their text at 3,000 characters.
SLACK_SECTION_TEXT_LIMIT = 3_000


def _truncate_for_slack(text: str, limit: int = SLACK_MARKDOWN_TEXT_LIMIT) -> str:
    """Truncate text to fit Slack's Markdown-block limit, adding a notice when cut.

    The full release notes remain available via the message's link buttons.
    """
    if len(text) <= limit:
        return text
    suffix = "…\n\n_Release notes truncated — see the full release using the links below._"
    return text[: limit - len(suffix)].rstrip() + suffix


def _build_blocks(
    release: GitHubRelease,
    body_block: Block,
    notion_page: str | None,
    linear_url: str | None,
) -> list[Block]:
    """Build the shared layout around either release-notes block type."""
    title = f"*{release.repo}*: _{release.tag_name}_ was released!"
    blocks = [
        SectionBlock(
            text=title,
            accessory=Button(
                text=":github: View Release",
                url=release.url,
                action_id=str(uuid4()),
            ),
        ),
        body_block,
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
        header: list[RawText | RichTextObject] = [RawText(text="Asset Name"), RawText(text="Size")]
        asset_rows: list[list[RawText | RichTextObject]] = [
            [RawText(text=asset.name), RawText(text=asset.size_mb)]
            for asset in release.assets
        ]
        blocks.append(TableBlock(rows=[header] + asset_rows))

    actions = []
    if notion_page:
        actions.append(Button(
            text=":notion: View Notion Page",
            url=notion_page,
            action_id=str(uuid4()),
        ))
    if linear_url:
        actions.append(Button(
            text=":linear: View Linear Releases",
            url=linear_url,
            action_id=str(uuid4()),
        ))
    if actions:
        blocks.append(ActionsBlock(elements=actions))

    return blocks


def _send_webhook_message(message: WebhookMessage, webhook_url: str) -> None:
    response = requests.post(
        webhook_url,
        data=message.json(),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    if response.status_code != 200:
        raise requests.HTTPError(
            f"Unexpected Slack response: {response.status_code} {response.text}",
            response=response,
        )


def _http_error_details(error: requests.HTTPError) -> str:
    if error.response is None:
        return str(error)
    return f"{error.response.status_code} {error.response.reason}"


def send_slack_notification(
    release: GitHubRelease,
    webhook_url: str,
    notion_page: str | None,
    linear_url: str | None,
):
    if not webhook_url.startswith("https://hooks.slack.com"):
        raise ValueError("webhook_url must start with https://hooks.slack.com")

    markdown_body = _truncate_for_slack(release.formatted_body)
    message = WebhookMessage(
        response_type=ResponseType.IN_CHANNEL,
        blocks=_build_blocks(
            release,
            MarkdownBlock(text=markdown_body),
            notion_page,
            linear_url,
        ),
    )

    try:
        _send_webhook_message(message, webhook_url)
        print(f"Message was sent successfully > {message.text}")
    except requests.HTTPError as error:
        error_details = _http_error_details(error)
        print(
            f"Markdown release notes were rejected by Slack ({error_details}); "
            "retrying with a section block."
        )
        fallback_body = _truncate_for_slack(
            release.formatted_body,
            limit=SLACK_SECTION_TEXT_LIMIT,
        )
        fallback_message = WebhookMessage(
            response_type=ResponseType.IN_CHANNEL,
            blocks=_build_blocks(
                release,
                SectionBlock(text=fallback_body),
                notion_page,
                linear_url,
            ),
        )
        try:
            _send_webhook_message(fallback_message, webhook_url)
            print(f"Fallback message was sent successfully > {fallback_message.text}")
        except requests.HTTPError as fallback_error:
            raise RuntimeError(
                "Failed to send the Markdown Slack message and its section-block fallback "
                f"> Markdown: {error_details}; "
                f"fallback: {_http_error_details(fallback_error)}"
            ) from fallback_error
