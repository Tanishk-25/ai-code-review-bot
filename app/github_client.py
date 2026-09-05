"""All GitHub API interactions live here — nothing else in the app talks to GitHub directly."""

from github import Auth, Github


class GitHubClient:
    def __init__(self, token: str, repo_name: str):
        auth = Auth.Token(token)
        self._gh = Github(auth=auth)
        self._repo = self._gh.get_repo(repo_name)

    def get_pull_request(self, pr_number: int):
        return self._repo.get_pull(pr_number)

    def get_changed_files(self, pr_number: int) -> list[dict]:
        """Return each changed file's name, status, and unified diff patch."""
        pr = self.get_pull_request(pr_number)
        files = []
        for f in pr.get_files():
            files.append({
                "filename": f.filename,
                "status": f.status,
                "patch": f.patch,
                "additions": f.additions,
                "deletions": f.deletions,
            })
        return files

    def post_summary_comment(self, pr_number: int, body: str):
        """Post the AI review summary as a single PR comment."""
        pr = self.get_pull_request(pr_number)
        pr.create_issue_comment(body)