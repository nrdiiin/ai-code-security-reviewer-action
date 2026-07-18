"""Tests for post_pr_comment.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from post_pr_comment import (
    MARKER,
    find_existing_comment,
    github_api,
    main,
    post_comment,
    update_comment,
)


class TestGithubApi:
    @patch("post_pr_comment.urlopen")
    def test_get_request(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps([{"id": 1}]).encode()
        mock_urlopen.return_value = mock_resp

        result = github_api("GET", "https://api.github.com/test", "tok123")
        assert result == [{"id": 1}]

    @patch("post_pr_comment.urlopen")
    def test_post_request(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 201
        mock_resp.read.return_value = json.dumps({"id": 42}).encode()
        mock_urlopen.return_value = mock_resp

        result = github_api("POST", "https://api.github.com/test", "tok123", {"body": "hello"})
        assert result == {"id": 42}

    @patch("post_pr_comment.urlopen")
    def test_204_returns_empty_dict(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 204
        mock_urlopen.return_value = mock_resp

        result = github_api("DELETE", "https://api.github.com/test", "tok123")
        assert result == {}


class TestFindExistingComment:
    @patch("post_pr_comment.github_api")
    def test_finds_marker(self, mock_api):
        mock_api.return_value = [
            {"id": 1, "body": "some comment"},
            {"id": 2, "body": f"hello\n{MARKER}\nworld"},
        ]
        result = find_existing_comment("owner/repo", 5, "tok")
        assert result == 2

    @patch("post_pr_comment.github_api")
    def test_no_marker_returns_none(self, mock_api):
        mock_api.return_value = [
            {"id": 1, "body": "some comment"},
            {"id": 2, "body": "another comment"},
        ]
        result = find_existing_comment("owner/repo", 5, "tok")
        assert result is None

    @patch("post_pr_comment.github_api")
    def test_empty_comments(self, mock_api):
        mock_api.return_value = []
        result = find_existing_comment("owner/repo", 5, "tok")
        assert result is None

    @patch("post_pr_comment.github_api")
    def test_api_error_returns_none(self, mock_api):
        from urllib.error import HTTPError

        mock_api.side_effect = HTTPError("url", 403, "Forbidden", {}, None)
        result = find_existing_comment("owner/repo", 5, "tok")
        assert result is None


class TestPostComment:
    @patch("post_pr_comment.github_api")
    def test_posts_comment(self, mock_api):
        mock_api.return_value = {"id": 10}
        post_comment("owner/repo", 5, "tok", "body text")
        mock_api.assert_called_once_with(
            "POST",
            "https://api.github.com/repos/owner/repo/issues/5/comments",
            "tok",
            {"body": "body text"},
        )


class TestUpdateComment:
    @patch("post_pr_comment.github_api")
    def test_updates_comment(self, mock_api):
        mock_api.return_value = {}
        update_comment("owner/repo", 42, "tok", "new body")
        mock_api.assert_called_once_with(
            "PATCH",
            "https://api.github.com/repos/owner/repo/issues/comments/42",
            "tok",
            {"body": "new body"},
        )


class TestMain:
    def test_skips_non_pr_event_with_empty_pr_number(self, capsys):
        """Non-PR event with empty --pr-number should NOT crash (BUG 2 fix)."""
        with patch("sys.argv", [
            "post_pr_comment.py",
            "--token", "tok",
            "--comment-file", "/tmp/fake.md",
            "--repo", "owner/repo",
            "--event", "push",
            "--pr-number", "",
        ]):
            main()
        captured = capsys.readouterr()
        assert "Skipping" in captured.out
        assert "push" in captured.out

    def test_skips_non_pr_event_with_zero_pr_number(self, capsys):
        """Non-PR event with --pr-number=0 should skip gracefully."""
        with patch("sys.argv", [
            "post_pr_comment.py",
            "--token", "tok",
            "--comment-file", "/tmp/fake.md",
            "--repo", "owner/repo",
            "--event", "push",
            "--pr-number", "0",
        ]):
            main()
        captured = capsys.readouterr()
        assert "Skipping" in captured.out

    def test_skips_when_no_pr_number(self, capsys):
        """PR event with no valid PR number should skip."""
        with patch("sys.argv", [
            "post_pr_comment.py",
            "--token", "tok",
            "--comment-file", "/tmp/fake.md",
            "--repo", "owner/repo",
            "--event", "pull_request",
            "--pr-number", "0",
        ]):
            main()
        captured = capsys.readouterr()
        assert "No valid PR number" in captured.out

    def test_skips_when_pr_number_empty_on_pr_event(self, capsys):
        """PR event with empty --pr-number should skip gracefully."""
        with patch("sys.argv", [
            "post_pr_comment.py",
            "--token", "tok",
            "--comment-file", "/tmp/fake.md",
            "--repo", "owner/repo",
            "--event", "pull_request",
            "--pr-number", "",
        ]):
            main()
        captured = capsys.readouterr()
        assert "Invalid PR number" in captured.out

    def test_skips_when_pr_number_invalid(self, capsys):
        """PR event with non-numeric --pr-number should skip gracefully."""
        with patch("sys.argv", [
            "post_pr_comment.py",
            "--token", "tok",
            "--comment-file", "/tmp/fake.md",
            "--repo", "owner/repo",
            "--event", "pull_request",
            "--pr-number", "abc",
        ]):
            main()
        captured = capsys.readouterr()
        assert "Invalid PR number" in captured.out

    def test_skips_missing_comment_file(self, capsys):
        """Missing comment file should skip."""
        with patch("sys.argv", [
            "post_pr_comment.py",
            "--token", "tok",
            "--comment-file", "/nonexistent/comment.md",
            "--repo", "owner/repo",
            "--event", "pull_request",
            "--pr-number", "5",
        ]):
            main()
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_skips_empty_comment_file(self, tmp_path, capsys):
        """Empty comment file should skip."""
        comment_file = tmp_path / "comment.md"
        comment_file.write_text("")

        with patch("sys.argv", [
            "post_pr_comment.py",
            "--token", "tok",
            "--comment-file", str(comment_file),
            "--repo", "owner/repo",
            "--event", "pull_request",
            "--pr-number", "5",
        ]):
            main()
        captured = capsys.readouterr()
        assert "empty" in captured.out.lower()

    @patch("post_pr_comment.find_existing_comment")
    @patch("post_pr_comment.post_comment")
    def test_creates_new_comment(self, mock_post, mock_find, tmp_path):
        """New comment when none exists."""
        comment_file = tmp_path / "comment.md"
        comment_file.write_text(f"{MARKER}\nHello")

        mock_find.return_value = None

        with patch("sys.argv", [
            "post_pr_comment.py",
            "--token", "tok",
            "--comment-file", str(comment_file),
            "--repo", "owner/repo",
            "--event", "pull_request",
            "--pr-number", "5",
        ]):
            main()

        mock_post.assert_called_once()

    @patch("post_pr_comment.find_existing_comment")
    @patch("post_pr_comment.update_comment")
    def test_updates_existing_comment(self, mock_update, mock_find, tmp_path):
        """Update existing comment when marker found."""
        comment_file = tmp_path / "comment.md"
        comment_file.write_text(f"{MARKER}\nUpdated")

        mock_find.return_value = 42

        with patch("sys.argv", [
            "post_pr_comment.py",
            "--token", "tok",
            "--comment-file", str(comment_file),
            "--repo", "owner/repo",
            "--event", "pull_request",
            "--pr-number", "5",
        ]):
            main()

        mock_update.assert_called_once()
        assert mock_update.call_args[0][1] == 42  # comment_id
