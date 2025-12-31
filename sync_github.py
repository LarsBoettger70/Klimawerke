#!/usr/bin/env python3
"""
GitHub Sync Tool - Dual Workflow Support

Version: 1.0.6

This version supports syncing both:
1. Manual changes made directly by the user.
2. Changes made by an external agent (with automated testing).

Enhancements:
- Ensures `sync_from_github` explicitly pulls updates from the `main` branch.
- Automatically merges `main` branch updates into the current feature/development branch.
- Provides more descriptive logs for pull operations.
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, Optional

class GitHubSyncTool:
    """GitHub Sync Tool with dual workflows."""
    
    VERSION = "1.0.6"  # Update this version number as needed

    def __init__(self):
        self.repo_path = Path.cwd()
        self.feature_branch = "feature/agent-output"
        self.agent_test_cmd = ['python3', 'agent_generated_file.py']  # Example agent test

    def is_git_repo(self) -> bool:
        """Check if the current directory is a Git repository."""
        try:
            subprocess.run(['git', 'rev-parse', '--git-dir'], cwd=self.repo_path, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def switch_to_branch(self, branch: str) -> Tuple[bool, str]:
        """Switch to a specific branch."""
        try:
            subprocess.run(['git', 'checkout', branch], cwd=self.repo_path, check=True)
            return True, f"Switched to branch '{branch}'"
        except subprocess.CalledProcessError as e:
            return False, f"Error switching to branch '{branch}': {e.stderr}"

    def pull_changes(self, branch: str) -> Tuple[bool, str]:
        """Pull changes from the remote repository for the specified branch."""
        try:
            subprocess.run(['git', 'pull', 'origin', branch], cwd=self.repo_path, check=True)
            return True, f"✓ Successfully pulled changes from '{branch}'"
        except subprocess.CalledProcessError as e:
            return False, f"Error pulling changes from '{branch}': {e.stderr}"

    def merge_branch(self, branch: str) -> Tuple[bool, str]:
        """Merge a specific branch into the current branch."""
        try:
            subprocess.run(['git', 'merge', branch], cwd=self.repo_path, check=True)
            return True, f"✓ Successfully merged '{branch}' into the current branch"
        except subprocess.CalledProcessError as e:
            return False, f"Error merging '{branch}' into the current branch: {e.stderr}"

    def sync_to_github(self, commit_message: Optional[str] = None, is_agent_workflow=False) -> Tuple[bool, str]:
        """
        Sync changes to GitHub, with separate workflows for manual and agent-generated changes.
        """
        if not self.is_git_repo():
            return False, "Error: Not in a git repository."
        
        output = []

        # Switch to feature branch
        output.append("Step 1: Switching to feature branch...")
        success, message = self.switch_to_branch(self.feature_branch)
        output.append(message)
        if not success:
            return False, "\n".join(output)

        # If agent workflow, run tests before syncing
        if is_agent_workflow:
            output.append("\nStep 2: Testing agent-generated files...")
            success, message = self.test_agent_files()
            output.append(message)
            if not success:
                # Abort if tests fail
                output.append("\n✗ Aborting sync because agent tests failed.")
                return False, "\n".join(output)
        else:
            output.append("\nStep 2: Skipping testing (manual workflow)...")

        try:
            # Stage all changes
            output.append("\nStep 3: Staging all changes...")
            subprocess.run(['git', 'add', '.'], cwd=self.repo_path, check=True)
            output.append("✓ Changes staged successfully.")

            # Commit changes
            output.append("\nStep 4: Committing changes...")
            if not commit_message:
                commit_message = "Sync: Manual or agent-generated changes"
            subprocess.run(['git', 'commit', '-m', commit_message], cwd=self.repo_path, check=True)
            output.append(f"✓ Changes committed: {commit_message}")

            # Push to feature branch
            output.append("\nStep 5: Pushing changes to GitHub...")
            subprocess.run(['git', 'push', '-u', 'origin', self.feature_branch], cwd=self.repo_path, check=True)
            output.append("✓ Changes pushed successfully.")

            return True, "\n".join(output)

        except subprocess.CalledProcessError as e:
            output.append(f"Error during sync: {e.stderr}")
            return False, "\n".join(output)

    def sync_from_github(self) -> Tuple[bool, str]:
        """
        Sync changes from GitHub, explicitly pulling from `main` and merging updates into the current feature branch.
        """
        if not self.is_git_repo():
            return False, "Error: Not in a Git repository."
        
        output = []

        try:
            # Detect the current branch
            current_branch_result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=self.repo_path, capture_output=True, text=True, check=True)
            current_branch = current_branch_result.stdout.strip()

            # Step 1: Stash uncommitted changes
            output.append("Step 1: Stashing local changes (if any)...")
            subprocess.run(['git', 'stash'], cwd=self.repo_path, check=False)
            output.append("✓ Local changes stashed.")

            # Step 2: Switch to `main` and pull changes
            output.append("\nStep 2: Switching to 'main' branch...")
            success, message = self.switch_to_branch('main')
            output.append(message)
            if not success:
                return False, "\n".join(output)

            output.append("\nStep 3: Pulling latest changes from 'main' branch...")
            success, message = self.pull_changes('main')
            output.append(message)
            if not success:
                return False, "\n".join(output)

            # Step 4: Switch back to the previous branch and merge `main` updates
            if current_branch != 'main':
                output.append(f"\nStep 4: Switching back to '{current_branch}'...")
                success, message = self.switch_to_branch(current_branch)
                output.append(message)
                if not success:
                    return False, "\n".join(output)

                output.append(f"\nStep 5: Merging updates from 'main' into '{current_branch}'...")
                success, message = self.merge_branch('main')
                output.append(message)
                if not success:
                    return False, "\n".join(output)

            # Step 6: Reapply stashed changes
            output.append("\nStep 6: Reapplying stashed changes...")
            subprocess.run(['git', 'stash', 'pop'], cwd=self.repo_path, check=False)
            output.append("✓ Stashed changes reapplied (if any).")

            return True, "\n".join(output)

        except subprocess.CalledProcessError as e:
            return False, f"Unexpected error while syncing: {e.stderr}"


def print_menu():
    """Print the main menu options."""
    print("\n" + "=" * 60)
    print(f"GitHub Sync Tool - Main Menu (v{GitHubSyncTool.VERSION})")
    print("=" * 60)
    print("1. Sync Files with Manual Changes")
    print("2. Sync Files with Agent-Generated Changes")
    print("3. Pull Changes from GitHub")
    print("4. Test Agent Files Locally")
    print("5. Exit")
    print("=" * 60)


def main():
    """Main entry point."""
    print(f"\n🚀 GitHub Sync Tool - Dual Workflow Support (v{GitHubSyncTool.VERSION})")
    print("Repository:", Path.cwd())
    tool = GitHubSyncTool()

    while True:
        print_menu()
        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == '1':
            # Manual changes
            commit_msg = input("Enter commit message (or press Enter for default): ").strip()
            success, message = tool.sync_to_github(commit_msg, is_agent_workflow=False)
        elif choice == '2':
            # Agent-generated changes
            commit_msg = input("Enter commit message (or press Enter for default): ").strip()
            success, message = tool.sync_to_github(commit_msg, is_agent_workflow=True)
        elif choice == '3':
            # Pull changes
            success, message = tool.sync_from_github()
        elif choice == '4':
            # Test agent files locally
            success, message = tool.test_agent_files()
        elif choice == '5':
            print("\n👋 Goodbye!")
            sys.exit(0)
        else:
            success, message = False, "Invalid choice. Please select an option between 1 and 5."

        print("\n" + message)
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
