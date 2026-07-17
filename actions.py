import os


class GITHUB:
    ref = os.getenv("GITHUB_REF")
    assert ref, "GITHUB_REF is not set"

    repository = os.getenv("GITHUB_REPOSITORY")
    assert repository, "GITHUB_REPOSITORY is not set"

    owner = repository.split("/")[0]
    name = repository.split("/")[-1]
    version = ref.split("/")[-1] if ref.startswith("refs/tags/") else None


class PARAMS:
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    assert slack_webhook_url, "SLACK_WEBHOOK_URL is not set"

    notion_api_key = os.getenv("NOTION_API_KEY")
    assert notion_api_key, "NOTION_API_KEY is not set"

    linear_api_key = os.getenv("LINEAR_API_KEY")
    assert linear_api_key, "LINEAR_API_KEY is not set"

    github_token = os.getenv("GITHUB_RELEASE_PULL_TOKEN")
    # Optional, so no assertion here
