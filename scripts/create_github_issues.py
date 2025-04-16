#!/usr/bin/env python3
"""
Script to create GitHub issues for LeagueLedger project.
"""
import requests
import os
import json
import sys
import re
from typing import Dict, List, Any
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# GitHub repository information
GITHUB_API_URL = "https://api.github.com"
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")

# GitHub authentication - use a personal access token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def validate_env():
    """Validate that all required environment variables are set."""
    missing_vars = []
    if not GITHUB_TOKEN:
        missing_vars.append("GITHUB_TOKEN")
    if not REPO_OWNER:
        missing_vars.append("REPO_OWNER")
    if not REPO_NAME:
        missing_vars.append("REPO_NAME")
    
    if missing_vars:
        print("Error: The following environment variables are missing in your .env file:")
        for var in missing_vars:
            print(f"- {var}")
        print("\nPlease update your .env file in the scripts directory.")
        return False
    return True

def get_all_issues():
    """Get all open issues from the repository."""
    url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    params = {
        "state": "open",
        "per_page": 100
    }
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch issues: {response.status_code}")
        print(response.text)
        return []

def close_issue(issue_number):
    """Close an issue by its number."""
    url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_number}"
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {
        "state": "closed"
    }
    
    response = requests.patch(url, json=data, headers=headers)
    
    if response.status_code == 200:
        print(f"Successfully closed issue #{issue_number}")
        return True
    else:
        print(f"Failed to close issue #{issue_number}: {response.status_code}")
        print(response.text)
        return False

def delete_all_issues():
    """Close all open issues in the repository."""
    issues = get_all_issues()
    
    if not issues:
        print("No open issues found.")
        return
    
    print(f"Found {len(issues)} open issues. Closing all...")
    
    for issue in issues:
        close_issue(issue["number"])
    
    print("Finished closing issues.")

def create_github_issue(issue_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a GitHub issue using the GitHub API."""
    url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.post(url, json=issue_data, headers=headers)
    
    if response.status_code == 201:
        print(f"Successfully created issue: {issue_data['title']}")
        return response.json()
    else:
        print(f"Failed to create issue: {response.status_code}")
        print(response.text)
        return {}

def parse_todo_file(file_path):
    """Parse the TODO.md file and extract the issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading TODO.md file: {e}")
        return []
        
    # Split the content by sections (## headings)
    sections = re.split(r'^## ', content, flags=re.MULTILINE)
    
    # The first section is the title and intro, skip it
    sections = sections[1:]
    
    all_issues = []
    
    for section in sections:
        # Get the section title from the first line
        title_line = section.split('\n', 1)[0].strip()
        section_content = section.split('\n', 1)[1].strip() if len(section.split('\n', 1)) > 1 else ""
        
        # Create a main issue for the section
        section_issue = {
            "title": title_line,
            "body": f"## {title_line}\n\nThis issue tracks the progress of all {title_line.lower()} tasks.\n\n### Tasks\n{section_content}",
            "labels": ["epic", title_line.lower().replace(' & ', '-').replace(' ', '-')]
        }
        all_issues.append(section_issue)
        
        # Parse individual tasks in the section
        tasks = parse_section_tasks(section_content, title_line)
        all_issues.extend(tasks)
        
    return all_issues

def parse_section_tasks(section_content, section_title):
    """Parse individual tasks from a section."""
    issues = []
    
    # Extract tasks at the top level (directly under the section)
    tasks = re.findall(r'^- \[ \] (.+)$', section_content, re.MULTILINE)
    for task in tasks:
        # Skip tasks that are groups (they have subtasks and usually end with a colon)
        if task.strip().endswith(':') or task.strip().startswith('**'):
            continue
            
        issue = {
            "title": task.strip(),
            "body": f"## Description\nImplement the following task from {section_title}:\n\n{task.strip()}\n\n## Related\nPart of the {section_title} epic.",
            "labels": ["task", section_title.lower().replace(' & ', '-').replace(' ', '-')]
        }
        issues.append(issue)
    
    # Extract grouped tasks (subtasks under headings like "User Management")
    groups = re.findall(r'- \[ \] \*\*(.*?)\*\*\s*\n((?:  - \[ \].*\n)*)', section_content, re.MULTILINE)
    
    for group_name, group_tasks_text in groups:
        # Create a group issue
        group_issue = {
            "title": f"{group_name}",
            "body": f"## Description\nImplement {group_name} features for {section_title}.\n\n## Tasks\n{group_tasks_text}\n\n## Related\nPart of the {section_title} epic.",
            "labels": ["group", section_title.lower().replace(' & ', '-').replace(' ', '-'), group_name.lower().replace(' ', '-')]
        }
        issues.append(group_issue)
        
        # Add individual subtasks
        subtasks = re.findall(r'  - \[ \] (.*)', group_tasks_text)
        for subtask in subtasks:
            subtask_issue = {
                "title": f"{group_name}: {subtask.strip()}",
                "body": f"## Description\nImplement the following {group_name} feature:\n\n{subtask.strip()}\n\n## Related\nPart of the {group_name} group in the {section_title} epic.",
                "labels": ["subtask", section_title.lower().replace(' & ', '-').replace(' ', '-'), group_name.lower().replace(' ', '-')]
            }
            issues.append(subtask_issue)
    
    return issues

def main():
    """Main function to create all the issues."""
    print("LeagueLedger GitHub Issue Creator")
    print("=================================")
    
    # Validate environment variables
    if not validate_env():
        sys.exit(1)
    
    print(f"Repository: {REPO_OWNER}/{REPO_NAME}")
    
    # Delete existing issues
    delete_option = input("Do you want to close all existing open issues? (y/n): ").lower()
    if delete_option == 'y':
        delete_all_issues()
    
    # Parse TODO.md and create issues
    todo_path = Path(__file__).parent.parent / 'TODO.md'
    if not todo_path.exists():
        print(f"Error: TODO.md file not found at {todo_path}")
        sys.exit(1)
    
    print(f"Parsing TODO.md at {todo_path}...")
    issues = parse_todo_file(todo_path)
    
    print(f"Found {len(issues)} issues to create.")
    create_option = input(f"Do you want to create {len(issues)} GitHub issues? (y/n): ").lower()
    
    if create_option != 'y':
        print("Operation cancelled.")
        sys.exit(0)
    
    # Create issues
    created_issues = []
    for issue in issues:
        result = create_github_issue(issue)
        if result:
            created_issues.append(result)
    
    # Show results
    if created_issues:
        print("\nSuccessfully created issues:")
        for issue in created_issues:
            print(f"- #{issue['number']} {issue['title']}: {issue['html_url']}")
    
    print("\nCompleted creating GitHub issues.")

if __name__ == "__main__":
    main()