from typing import Any

from linear_api import LinearClient

from github import GitHubRelease


class Linear:
    def __init__(self, api_key: str):
        self.client: LinearClient = LinearClient(api_key=api_key)

    def create_linear_issue(self, release: GitHubRelease, notion_page: str | None) -> None:
        issue_title = f"Notify Release {release.platform_name} {release.tag_name}"
        issue_description = (
            f"Send an email notification for a release of {release.repo}.\n\n"
            f"Release URL: {release.url}\n"
            f"Notion Page: {notion_page}\n"
            f"Linear Releases: {release.linear_releases_url}\n\n"
            f"+++ # Release Notes\n\n{release.formatted_body}\n\n+++"  # +++ frames a collapsible section
        )

        routing = self.client.execute_graphql("""
            query ReleaseNotificationRouting {
                teams(filter: { key: { eq: "SDK" } }) {
                    nodes {
                        id
                        projects(filter: { name: { eq: "SDK Release Notes" } }) { nodes { id } }
                        states(filter: { name: { eq: "Todo" } }) { nodes { id } }
                    }
                }
                users(filter: { email: { eq: "erik.sargent@atomicfi.com" } }) { nodes { id } }
            }
        """)
        teams = routing["teams"]["nodes"]
        if len(teams) != 1:
            raise ValueError("Expected one Linear team with key SDK")
        team = teams[0]
        team_id = team["id"]
        release_notification_label_id = self.get_label_by_name(
            "Release Notification",
            team_id=team_id,
        )
        label_ids = []
        if release_notification_label_id:
            label_ids.append(release_notification_label_id)
        else:
            print('SDK team label "Release Notification" was not found; creating the ticket without it.')
        if release.platform_name:
            platform_label_id = self.get_platform_label(
                release.platform_name,
                team_id=team_id,
            )
            if platform_label_id:
                label_ids.append(platform_label_id)

        issue_input = {
            "title": issue_title,
            "description": issue_description,
            "teamId": team_id,
            "projectId": self._required_id(team["projects"], "SDK Release Notes project"),
            "stateId": self._required_id(team["states"], "Todo state"),
            "assigneeId": self._required_id(routing["users"], "release notification assignee"),
            "labelIds": label_ids,
        }
        result = self.client.execute_graphql("""
            mutation CreateReleaseNotification($input: IssueCreateInput!) {
                issueCreate(input: $input) { success issue { id } }
            }
        """, {"input": issue_input})
        created = result["issueCreate"]
        if not created["success"] or not created["issue"]:
            raise ValueError(f"Linear did not confirm creation of {issue_title}")

    @staticmethod
    def _required_id(connection: dict[str, Any], name: str) -> str:
        nodes = connection["nodes"]
        if len(nodes) != 1:
            raise ValueError(f"Expected one Linear {name}, found {len(nodes)}")
        return nodes[0]["id"]

    def get_label_by_name(self, label_name: str, team_id: str) -> str | None:
        query = """
        query($teamId: ID!, $labelName: String!) {
            issueLabels(filter: {
                team: { id: { eq: $teamId } }
                name: { eq: $labelName }
            }) {
                nodes {
                    id
                }
            }
        }
        """

        result = self.client.execute_graphql(query, variables={
            "teamId": team_id,
            "labelName": label_name,
        })
        labels = result.get("issueLabels", {}).get("nodes", [])
        if labels:
            return labels[0].get("id")

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

        result = self.client.execute_graphql(query, variables={
            "teamId": team_id,
            "platform": platform,
        })
        labels = result.get("issueLabels", {}).get("nodes", [])
        if labels:
            return labels[0].get("id")
