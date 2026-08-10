import os


def required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"{name} is not set")
    return value


class GITHUB:
    ref: str = required_env("GITHUB_REF")

    repository: str = required_env("GITHUB_REPOSITORY")

    owner: str = repository.split("/")[0]
    name: str = repository.split("/")[-1]
    version: str | None = ref.split("/")[-1] if ref.startswith("refs/tags/") else None


class PARAMS:
    slack_webhook_url: str = required_env("SLACK_WEBHOOK_URL")
    notion_api_key: str = required_env("NOTION_API_KEY")
    linear_api_key: str = required_env("LINEAR_API_KEY")

    github_token: str | None = os.getenv("GITHUB_RELEASE_PULL_TOKEN")
