# GitHub Issue Creation

This directory contains scripts for creating GitHub issues for the LeagueLedger project.

## Create GitHub Issues Script

The `create_github_issues.py` script allows you to automatically create structured GitHub issues for your project features.

### Prerequisites

1. A GitHub account
2. A personal access token with "repo" scope (Create one at https://github.com/settings/tokens)
3. Python 3.6+ installed with the requests library

### Setup

1. Update the script with your GitHub information:
   ```python
   REPO_OWNER = "YOUR_GITHUB_USERNAME"  # Replace with your GitHub username
   REPO_NAME = "LeagueLedger"  # Replace with your repository name
   ```

2. Set your GitHub token as an environment variable:
   
   **Windows:**
   ```cmd
   set GITHUB_TOKEN=your_token_here
   ```

   **Mac/Linux:**
   ```bash
   export GITHUB_TOKEN=your_token_here
   ```

### Usage

Run the script from the command line:

```bash
python scripts/create_github_issues.py
```

This will create issues for the profile management features:
- Add profile picture update functionality
- Implement username change capability
- Create account deletion process
- Add profile privacy settings
- Implement social media integration for profiles

### Customizing Issues

You can customize the issues by editing the `PROFILE_ISSUES` list in the script. Each issue consists of:

- `title`: The issue title
- `body`: Markdown-formatted issue description
- `labels`: List of labels to apply to the issue

### Best Practices

- Always use clear titles and detailed descriptions
- Include requirements and acceptance criteria in each issue
- Use labels to categorize issues for better organization
- Mention related areas of code that might be affected

## Adding More Issue Sets

To add more feature sets beyond profile management, create new issue lists following the same format and add them to the script.