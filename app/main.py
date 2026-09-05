"""Entry point: fetch PR data, run the AI reviewer, post the result back to GitHub."""

import os
import sys

from dotenv import load_dotenv

from app.ai_reviewer import AIReviewer
from app.github_client import GitHubClient
from app.reviewer import load_config, review_files


def main():
    load_dotenv(".env")

    token = os.environ.get("GITHUB_TOKEN")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("PR_NUMBER")

    if not token:
        print("ERROR: GITHUB_TOKEN is not set.")
        sys.exit(1)
    if not gemini_key:
        print("ERROR: GEMINI_API_KEY is not set.")
        sys.exit(1)
    if not repo_name:
        print("ERROR: GITHUB_REPOSITORY is not set.")
        sys.exit(1)
    if not pr_number:
        print("ERROR: PR_NUMBER is not set.")
        sys.exit(1)

    config = load_config()

    try:
        github_client = GitHubClient(token=token, repo_name=repo_name)
        changed_files = github_client.get_changed_files(int(pr_number))
    except Exception as exc:
        print(f"ERROR: Failed to fetch PR data from GitHub: {exc}")
        sys.exit(1)

    if not changed_files:
        print("No changed files found in this PR — nothing to review.")
        return

    ai_reviewer = AIReviewer(api_key=gemini_key, model=config["model"])

    try:
        summary = review_files(changed_files, ai_reviewer, config)
    except Exception as exc:
        print(f"ERROR: AI review failed: {exc}")
        sys.exit(1)

    body = summary.to_markdown()
    print(body)

    try:
        github_client.post_summary_comment(int(pr_number), body)
    except Exception as exc:
        print(f"ERROR: Failed to post comment to GitHub: {exc}")
        sys.exit(1)

    print("\nReview posted successfully.")


if __name__ == "__main__":
    main()