from linear_api import LinearClient, LinearIssueInput

from github import GitHubRelease


class Linear:
    def __init__(self, api_key: str):
        self.client = LinearClient(api_key=api_key)

    def create_linear_issue(self, release: GitHubRelease, notion_page: str | None) -> str:
        issue_title = f"Notify Release {release.platform_name} {release.tag_name}"
        issue_description = (
            f"Send an email notification for a release of {release.repo}.\n\n"
            f"Release URL: {release.url}\n"
            f"Notion Page: {notion_page}\n"
            f"Related Issues: https://linear.app/atomicbuilt/team/SDK/issue-label/{release.tag_name}\n\n"
            f"+++ # Release Notes\n\n{release.formatted_body}\n\n+++"  # +++ frames a collapsible section
        )

        team_id = self.get_sdk_team_id()
        labels = []
        if release.platform_name:
            platform_label_id = self.get_platform_label(release.platform_name, team_id=team_id)
            if platform_label_id:
                labels.append(platform_label_id)

            version_label_id = self.get_or_make_version_label(release.tag_name, release.platform_name, team_id=team_id)
            if version_label_id:
                labels.append(version_label_id)

        user_id = self.client.users.get_id_by_email("trey@atomicfi.com")

        new_issue = LinearIssueInput(
            title=issue_title,
            description=issue_description,
            teamName="SDK",
            projectName="Release Notes",
            stateName="Todo",
            assigneeId=user_id,
            labelIds=labels,
        )

        created = self.client.issues.create(new_issue)
        return created.url

    def get_sdk_team_id(self) -> str:
        return self.client.teams.get("SDK").id

    def get_label_with_name(self, name: str, team_id: str) -> str | None:
        # Taken from client.teams.get_labels,
        # but that function doesn't return all pages correctly.
        # So instead I'm filtering for the parent label here,
        # then getting the child label from that
        query = """
        query($teamId: ID!, $name: String!) {
            issueLabels(filter: {
                team: { id: { eq: $teamId } }
                name: { eq: $name }
            }) {
                nodes {
                    id
                    name
                }
            }
        }
        """

        result = self.client.teams._execute_query(query, variables={
            "teamId": team_id,
            "name": name
        })
        labels = result.get("issueLabels", {}).get("nodes", [])
        if labels and len(labels) > 0:
            return labels[0].get("id")

    def get_platform_label(self, platform: str, team_id: str) -> str | None:
        # Taken from client.teams.get_labels,
        # but that function doesn't return all pages correctly.
        # So instead I'm filtering for the specific label here
        query = """
        query($teamId: ID!, $platform: String!) {
            issueLabels(filter: {
                team: { id: { eq: $teamId } }
                name: { eq: $platform }
                parent: { name: { eq: "Platform" } }
            }) {
                nodes {
                    id
                    name
                }
            }
        }
        """

        result = self.client.teams._execute_query(query, variables={
            "teamId": team_id,
            "platform": platform
        })
        labels = result.get("issueLabels", {}).get("nodes", [])
        if labels and len(labels) > 0:
            return labels[0].get("id")

    def get_or_make_version_label(self, version: str, platform: str, team_id: str) -> str | None:
        # Taken from client.teams.get_labels,
        # but that function doesn't return all pages correctly.
        # So instead I'm filtering for the specific label here
        query = """
        query($teamId: ID!, $version: String!, $platform: String!) {
            issueLabels(filter: {
                team: { id: { eq: $teamId } }
                name: { eq: $version }
                parent: { name: { eq: $platform } }
            }) {
                nodes {
                    id
                    name
                }
            }
        }
        """

        platform_name = f"{platform} Version"
        result = self.client.teams._execute_query(query, variables={
            "teamId": team_id,
            "platform": platform_name,
            "version": version
        })
        labels = result.get("issueLabels", {}).get("nodes", [])
        if labels and len(labels) > 0:
            id = labels[0].get("id")
            if id:
                return id

        # Create the label if it doesn't exist
        # Find the parent's id so we can assign it properly
        parent = self.get_label_with_name(platform_name, team_id)
        if not parent:
            return None

        mutation = """
        mutation IssueLabelCreate($issueLabelCreateInput: IssueLabelCreateInput!) {
            issueLabelCreate(input: $issueLabelCreateInput) {
                success
                issueLabel {
                    id
                    name
                }
            }
        }
        """
        # Color gets set automatically from the parent
        result = self.client.teams._execute_query(mutation, variables={
            "issueLabelCreateInput": {
                "parentId": parent,
                "name": version,
                "teamId": team_id,
            }
        })
        created_label = result.get("issueLabelCreate", {}).get("issueLabel", {})
        return created_label.get("id")
