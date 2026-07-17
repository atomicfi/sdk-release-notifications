from linear_api import LinearClient, LinearIssueInput

from github import GitHubRelease


class Linear:
    def __init__(self, api_key: str):
        self.client = LinearClient(api_key=api_key)

    def create_linear_issue(self, release: GitHubRelease, notion_page: str | None) -> None:
        issue_title = f"Notify Release {release.platform_name} {release.tag_name}"
        issue_description = (
            f"Send an email notification for a release of {release.repo}.\n\n"
            f"Release URL: {release.url}\n"
            f"Notion Page: {notion_page}\n"
            f"Linear Releases: {release.linear_releases_url}\n\n"
            f"+++ # Release Notes\n\n{release.formatted_body}\n\n+++"  # +++ frames a collapsible section
        )

        label_ids = []
        if release.platform_name:
            platform_label_id = self.get_platform_label(
                release.platform_name,
                team_id=self.get_sdk_team_id(),
            )
            if platform_label_id:
                label_ids.append(platform_label_id)

        user_id = self.client.users.get_id_by_email("erik.sargent@atomicfi.com")

        new_issue = LinearIssueInput(
            title=issue_title,
            description=issue_description,
            teamName="SDK",
            projectName="SDK Release Notes",
            stateName="Todo",
            assigneeId=user_id,
            labelIds=label_ids,
        )

        self.client.issues.create(new_issue)

    def get_sdk_team_id(self) -> str:
        return self.client.teams.get("SDK").id

    def get_platform_label(self, platform: str, team_id: str) -> str | None:
        query = """
        query($teamId: ID!, $platform: String!) {
            issueLabels(filter: {
                team: { id: { eq: $teamId } }
                name: { eq: $platform }
                parent: { name: { eq: "Platform" } }
            }) {
                nodes {
                    id
                }
            }
        }
        """

        result = self.client.teams._execute_query(query, variables={
            "teamId": team_id,
            "platform": platform,
        })
        labels = result.get("issueLabels", {}).get("nodes", [])
        if labels:
            return labels[0].get("id")
