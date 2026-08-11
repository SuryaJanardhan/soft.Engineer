import os
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv


def sync_secrets(repo_name: str = "SuryaJanardhan/soft.Engineer") -> None:
    load_dotenv()
    gh_bin = Path(".venv/bin/gh")
    if not gh_bin.exists():
        gh_bin_str = "gh"
    else:
        gh_bin_str = str(gh_bin.resolve())

    secrets_to_sync = {
        "JIRA_BASE_URL": os.getenv("JIRA_BASE_URL", ""),
        "JIRA_EMAIL": os.getenv("JIRA_EMAIL", ""),
        "JIRA_API_TOKEN": os.getenv("JIRA_API_TOKEN", ""),
        "JIRA_PROJECT_KEY": os.getenv("JIRA_PROJECT_KEY", ""),
        "GROQ_API_KEY_1": os.getenv("GROQ_API_KEY_1", ""),
        "GROQ_API_KEY_2": os.getenv("GROQ_API_KEY_2", ""),
        "NOTIFICATION_EMAIL": os.getenv("NOTIFICATION_EMAIL", ""),
        "SMTP_HOST": os.getenv("SMTP_HOST", ""),
        "SMTP_PORT": os.getenv("SMTP_PORT", "587"),
        "SMTP_USER": os.getenv("SMTP_USER", ""),
        "SMTP_PASS": os.getenv("SMTP_PASS", ""),
    }

    print(f"Syncing secrets from .env to GitHub Repository '{repo_name}'...")

    for key, value in secrets_to_sync.items():
        if not value:
            print(f"- Skipping {key} (value is empty in .env)")
            continue

        cmd = [gh_bin_str, "secret", "set", key, "-b", value, "-R", repo_name]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Successfully set secret: {key}")
        except subprocess.CalledProcessError as error:
            print(f"Failed to set secret {key}: {error.stderr.strip()}")

    print("\nSecret sync process completed.")


if __name__ == "__main__":
    sync_secrets()
