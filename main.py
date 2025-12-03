from actions import GITHUB, PARAMS
from github import GitHubClient
from linear import Linear
from notion import add_notion_database_row
from slack import send_slack_notification


def main():
    release = GitHubClient().get_release(GITHUB.owner, GITHUB.name, GITHUB.version)
    print(release)

    page_url = add_notion_database_row(release, PARAMS.notion_api_key)
    linear_url = Linear(PARAMS.linear_api_key).create_linear_issue(release, notion_page=page_url)

    print(linear_url)

    send_slack_notification(release, PARAMS.slack_webhook_url, notion_page=page_url, linear_url=linear_url)


if __name__ == "__main__":
    main()
