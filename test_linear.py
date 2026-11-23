import unittest
from unittest.mock import Mock

from github import GitHubRelease
from linear import Linear


class ReleaseNotificationTests(unittest.TestCase):
    def setUp(self):
        self.linear = Linear("test")
        self.client = Mock()
        self.linear.client = self.client
        self.release = Mock(spec=GitHubRelease)
        self.release.platform_name = "Android"
        self.release.tag_name = "v3.28.0"
        self.release.repo = "atomic-transact-android-public"
        self.release.url = "https://example.com/release"
        self.release.linear_releases_url = "https://example.com/linear"
        self.release.formatted_body = "Android release notes"
        self.team = {
            "id": "sdk",
            "projects": {"nodes": [{"id": "release-notes"}]},
            "states": {"nodes": [{"id": "todo"}]},
        }
        self.routing = {"teams": {"nodes": [self.team]}, "users": {"nodes": [{"id": "assignee"}]}}
        self.created = {"issueCreate": {"success": True, "issue": {"id": "issue"}}}

    def test_creates_routed_issue_without_followup_fetch(self):
        self.client.execute_graphql.side_effect = [
            self.routing,
            {"issueLabels": {"nodes": [{"id": "release-label"}]}},
            {"issueLabels": {"nodes": [{"id": "android-label"}]}},
            self.created,
        ]
        self.linear.create_linear_issue(self.release, "https://example.com/notion")

        calls = self.client.execute_graphql.call_args_list
        self.assertEqual(len(calls), 4)
        for removed_field in ("progressHistory", "currentProgress"):
            self.assertNotIn(removed_field, calls[0].args[0])
        mutation, variables = calls[-1].args
        self.assertIn("issueCreate(input: $input)", mutation)
        data = variables["input"].copy()
        description = data.pop("description")
        self.assertIn("Android release notes", description)
        self.assertIn("https://example.com/notion", description)
        self.assertEqual(data, {
            "title": "Notify Release Android v3.28.0",
            "teamId": "sdk",
            "projectId": "release-notes",
            "stateId": "todo",
            "assigneeId": "assignee",
            "labelIds": ["release-label", "android-label"],
        })
        self.assertEqual(len(self.client.mock_calls), len(calls))

    def test_missing_labels_are_optional_but_failed_creation_is_reported(self):
        no_labels = {"issueLabels": {"nodes": []}}
        self.client.execute_graphql.side_effect = [
            self.routing, no_labels, no_labels, {"issueCreate": {"success": False, "issue": None}},
        ]
        with self.assertRaisesRegex(ValueError, "did not confirm creation"):
            self.linear.create_linear_issue(self.release, None)
        self.assertEqual(self.client.execute_graphql.call_args.args[1]["input"]["labelIds"], [])
