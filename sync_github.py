#!/usr/bin/env python3
"""
GitHub Sync Tool - Dual Workflow Support With Logging

Version: 1.2.0

Enhancements:
- Added Option 6 to edit .gitignore file
- Option 1 shows .gitignore, asks for confirmation, and lets you choose the target branch
- Comprehensive logging to `sync_github.log`
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    filename="sync_github.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class GitHubSyncTool:
    """GitHub Sync Tool with manual and agent-generated workflows."""
    
    VERSION = "1.2.0"

    def __init__(self):
        logging.info("Initializing GitHubSyncTool...")
        self.repo_path = Path.cwd()
        self.feature_branch = "feature/agent-output"
        self.agent_test_cmd = ['python3', 'agent_generated_file.py']

    def is_git_repo(self) -> bool:
        """Check if the current directory is a Git repository."""
        try:
            logging.info("Checking if the directory is a git repository...")
            subprocess.run(['git', 'rev-parse', '--git-dir'], cwd=self.repo_path, check=True, capture_output=True)
            logging.info("Directory is a git repository.")
            return True
        except subprocess.CalledProcessError:
            logging.error("Not a git repository.")
            return False

    def show_gitignore(self) -> str:
        """Display the contents of .gitignore file."""
        gitignore_path = self.repo_path / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                contents = f.read()
            return contents
        else:
            return "No .gitignore file found."

    def edit_gitignore(self) -> Tuple[bool, str]:
        """Edit the .gitignore file using the default system editor."""
        gitignore_path = self.repo_path / ".gitignore"
        
        # Show current contents first
        print("\n" + "=" * 60)
        print("Current .gitignore contents:")
        print("=" * 60)
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                print(f.read())
        else:
            print("No .gitignore file found. A new one will be created.")
        print("=" * 60)
        
        # Ask user what they want to do
        print("\nEdit Options:")
        print("1. Open in default text editor (nano/vim/etc)")
        print("2. Add new patterns interactively")
        print("3. Cancel")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            # Open in system editor
            editor = os.environ.get('EDITOR', 'nano')  # Default to nano if EDITOR not set
            try:
                subprocess.run([editor, str(gitignore_path)], cwd=self.repo_path, check=True)
                logging.info("User edited .gitignore with system editor")
                return True, "✓ .gitignore edited successfully"
            except subprocess.CalledProcessError as e:
                logging.error(f"Error editing .gitignore: {e}")
                return False, f"✗ Error editing .gitignore: {e}"
        
        elif choice == '2':
            # Add patterns interactively
            print("\n" + "=" * 60)
            print("Add patterns to .gitignore")
            print("Enter patterns one per line (empty line to finish)")
            print("=" * 60)
            
            patterns = []
            while True:
                pattern = input("Pattern (or press Enter to finish): ").strip()
                if not pattern:
                    break
                patterns.append(pattern)
            
            if patterns:
                try:
                    with open(gitignore_path, 'a') as f:
                        f.write('\n')
                        for pattern in patterns:
                            f.write(f"{pattern}\n")
                    logging.info(f"Added {len(patterns)} patterns to .gitignore")
                    return True, f"✓ Added {len(patterns)} pattern(s) to .gitignore"
                except Exception as e:
                    logging.error(f"Error writing to .gitignore: {e}")
                    return False, f"✗ Error writing to .gitignore: {e}"
            else:
                return True, "No patterns added"
        
        else:
            logging.info("User cancelled .gitignore edit")
            return True, "Edit cancelled"

    def switch_to_branch(self, branch: str) -> Tuple[bool, str]:
        """Switch to a specific branch."""
        logging.info(f"Switching to branch '{branch}'...")
        try:
            subprocess.run(['git', 'checkout', branch], cwd=self.repo_path, check=True, capture_output=True)
            logging.info(f"Switched to branch '{branch}'")
            return True, f"Switched to branch '{branch}'"
        except subprocess.CalledProcessError as e:
            logging.error(f"Error switching to branch '{branch}': {e.stderr}")
            return False, f"Error switching to branch '{branch}': {e.stderr.decode() if e.stderr else 'Unknown error'}"

    def test_agent_files(self) -> Tuple[bool, str]:
        """Test files generated by the agent."""
        logging.info("Testing agent-generated files...")
        try:
            subprocess.run(self.agent_test_cmd, cwd=self.repo_path, check=True)
            logging.info("Agent-generated files tested successfully.")
            return True, "✓ Agent-generated files tested successfully."
        except subprocess.CalledProcessError as e:
            logging.error(f"Agent-generated files testing failed. Error: {e.stderr}")
            return False, f"✗ Agent-generated files testing failed. Error:\n{e.stderr}"

    def pull_changes(self, branch: str) -> Tuple[bool, str]:
        """Pull changes from the remote repository for the specified branch."""
        logging.info(f"Pulling changes from branch '{branch}'...")
        try:
            subprocess.run(['git', 'pull', 'origin', branch], cwd=self.repo_path, check=True)
            logging.info(f"Successfully pulled changes from branch '{branch}'.")
            return True, f"✓ Successfully pulled changes from '{branch}'"
        except subprocess.CalledProcessError as e:
            logging.error(f"Error pulling changes from '{branch}': {e.stderr}")
            return False, f"Error pulling changes from '{branch}': {e.stderr}"

    def merge_branch(self, branch: str) -> Tuple[bool, str]:
        """Merge a specific branch into the current branch."""
        logging.info(f"Merging branch '{branch}' into current branch...")
        try:
            subprocess.run(['git', 'merge', branch], cwd=self.repo_path, check=True)
            logging.info(f"Successfully merged '{branch}' into current branch.")
            return True, f"✓ Successfully merged '{branch}' into the current branch"
        except subprocess.CalledProcessError as e:
            logging.error(f"Error merging '{branch}':  {e.stderr}")
            return False, f"Error merging '{branch}' into the current branch: {e.stderr}"

    def sync_to_github(self, commit_message: Optional[str] = None, is_agent_workflow=False) -> Tuple[bool, str]:
        """
        Sync changes to GitHub with manual workflow enhancements.
        Shows .gitignore, asks for confirmation, and lets user choose target branch.
        """
        logging.info("Starting sync_to_github function...")
        if not self.is_git_repo():
            logging.error("Not in a git repository.")
            return False, "Error: Not in a git repository."
        
        output = []

        # Step 0: Show .gitignore contents
        print("\n" + "=" * 60)
        print("Contents of .gitignore:")
        print("=" * 60)
        gitignore_contents = self.show_gitignore()
        print(gitignore_contents)
        print("=" * 60)
        
        # Ask for confirmation
        confirm = input("\nAre you happy with the .gitignore settings? (y/n/e to edit): ").strip().lower()
        if confirm == 'e':
            # Edit .gitignore
            success, message = self.edit_gitignore()
            print(f"\n{message}")
            # Ask again after editing
            confirm = input("\nProceed with sync? (y/n): ").strip().lower()
        
        if confirm != 'y':
            logging.info("User cancelled sync due to .gitignore review.")
            return False, "Sync cancelled by user."

        # Ask which branch to push to
        print("\nWhere would you like to push your changes?")
        print("1. Push to 'main' branch (direct push)")
        print("2. Push to 'feature/agent-output' branch (create PR later)")
        branch_choice = input("Enter your choice (1 or 2): ").strip()
        
        if branch_choice == '1':
            target_branch = 'main'
        elif branch_choice == '2':
            target_branch = self.feature_branch
        else:
            logging.error("Invalid branch choice.")
            return False, "Invalid branch choice. Sync cancelled."
        
        logging.info(f"User selected target branch: {target_branch}")

        # Step 1: Stash uncommitted changes
        output.append("Step 1: Stashing uncommitted changes (if any)...")
        logging.info("Stashing uncommitted changes...")
        subprocess.run(['git', 'stash'], cwd=self.repo_path, check=False)
        output.append("✓ Uncommitted changes stashed.")

        # Step 2: Switch to target branch
        output.append(f"\nStep 2: Switching to '{target_branch}' branch...")
        logging.info(f"Switching to '{target_branch}' branch...")
        success, message = self.switch_to_branch(target_branch)
        output.append(message)
        if not success:
            return False, "\n".join(output)

        # Step 3: Reapply stashed changes
        output.append("\nStep 3: Reapplying stashed changes...")
        logging.info("Reapplying stashed changes...")
        subprocess.run(['git', 'stash', 'pop'], cwd=self.repo_path, check=False)
        output.append("✓ Stashed changes reapplied.")

        # If agent workflow, run tests
        if is_agent_workflow:
            output.append("\nStep 4: Testing agent-generated files...")
            logging.info("Testing agent-generated files...")
            success, message = self.test_agent_files()
            output.append(message)
            if not success:
                output.append("\n✗ Aborting sync because agent tests failed.")
                return False, "\n".join(output)
        else:
            output.append("\nStep 4: Skipping testing (manual workflow)...")
            logging.info("Skipping testing (manual workflow)...")

        try:
            # Stage all changes (respecting .gitignore)
            output.append("\nStep 5: Staging all changes...")
            logging.info("Staging all changes...")
            subprocess.run(['git', 'add', '.'], cwd=self.repo_path, check=True)
            output.append("✓ Changes staged successfully.")

            # Commit changes
            output.append("\nStep 6: Committing changes...")
            if not commit_message:
                commit_message = "Sync:  Manual or agent-generated changes"
            logging.info(f"Committing changes with message: {commit_message}")
            subprocess.run(['git', 'commit', '-m', commit_message], cwd=self.repo_path, check=True)
            output.append(f"✓ Changes committed:  {commit_message}")

            # Push to selected branch
            output.append(f"\nStep 7: Pushing changes to '{target_branch}' on GitHub...")
            logging.info(f"Pushing changes to '{target_branch}' on GitHub...")
            subprocess.run(['git', 'push', '-u', 'origin', target_branch], cwd=self.repo_path, check=True)
            output.append(f"✓ Changes pushed successfully to '{target_branch}'.")

            return True, "\n".join(output)

        except subprocess.CalledProcessError as e:
            logging.error(f"Error during sync: {e.stderr}")
            output.append(f"Error during sync: {e.stderr}")
            return False, "\n".join(output)

    def sync_from_github(self) -> Tuple[bool, str]:
        """Sync changes from GitHub, pulling from `main` into the current branch."""
        logging.info("Starting sync_from_github function...")
        if not self.is_git_repo():
            logging.error("Not in a git repository.")
            return False, "Error: Not in a git repository."

        output = []

        try:
            # Detect the current branch
            current_branch_result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=self.repo_path, capture_output=True, text=True, check=True
            )
            current_branch = current_branch_result.stdout.strip()
            logging.info(f"Current branch is '{current_branch}'...")

            # Step 1: Stash uncommitted changes
            output.append("Step 1: Stashing local changes (if any)...")
            logging.info("Stashing local changes...")
            subprocess.run(['git', 'stash'], cwd=self.repo_path, check=False)
            output.append("✓ Local changes stashed.")

            # Step 2: Switch to `main` and pull changes
            output.append("\nStep 2: Switching to 'main' branch...")
            logging.info("Switching to 'main' branch...")
            success, message = self.switch_to_branch('main')
            output.append(message)
            if not success:
                return False, "\n".join(output)

            output.append("\nStep 3: Pulling latest changes from 'main' branch...")
            logging.info("Pulling changes from 'main' branch...")
            success, message = self.pull_changes('main')
            output.append(message)
            if not success:
                return False, "\n".join(output)

            # Step 4: Switch back to previous branch and merge
            if current_branch != 'main':
                output.append(f"\nStep 4: Switching back to '{current_branch}'...")
                logging.info(f"Switching back to branch '{current_branch}'...")
                success, message = self.switch_to_branch(current_branch)
                output.append(message)
                if not success:
                    return False, "\n".join(output)

                output.append(f"\nStep 5: Merging updates from 'main' into '{current_branch}'...")
                logging.info(f"Merging 'main' into '{current_branch}'...")
                success, message = self.merge_branch('main')
                output.append(message)
                if not success:
                    return False, "\n".join(output)

            # Step 6: Reapply stashed changes
            output.append("\nStep 6: Reapplying stashed changes...")
            logging.info("Reapplying stashed changes...")
            subprocess.run(['git', 'stash', 'pop'], cwd=self.repo_path, check=False)
            output.append("✓ Stashed changes reapplied (if any).")

            return True, "\n".join(output)

        except subprocess.CalledProcessError as e:
            logging.error(f"Unexpected error during sync: {e.stderr}")
            return False, f"Unexpected error during sync: {e.stderr}"


def print_menu():
    """Print the main menu options."""
    print("\n" + "=" * 60)
    print(f"GitHub Sync Tool - Main Menu (v{GitHubSyncTool.VERSION})")
    print("=" * 60)
    print("1. Sync Files with Manual Changes")
    print("2. Sync Files with Agent-Generated Changes")
    print("3. Pull Changes from GitHub")
    print("4. Test Agent Files Locally")
    print("5. Edit .gitignore")
    print("6. Exit")
    print("=" * 60)


def main():
    """Main entry point for the script."""
    logging.info("Starting main function...")
    print(f"\n🚀 GitHub Sync Tool - Dual Workflow Support (v{GitHubSyncTool.VERSION})")
    print("Repository:", Path.cwd())
    tool = GitHubSyncTool()

    while True:
        print_menu()
        choice = input("\nEnter your choice (1-6): ").strip()

        if choice == '1':
            commit_msg = input("Enter commit message (or press Enter for default): ").strip()
            success, message = tool.sync_to_github(commit_msg, is_agent_workflow=False)
        elif choice == '2':
            commit_msg = input("Enter commit message (or press Enter for default): ").strip()
            success, message = tool.sync_to_github(commit_msg, is_agent_workflow=True)
        elif choice == '3':
            success, message = tool.sync_from_github()
        elif choice == '4':
            success, message = tool.test_agent_files()
        elif choice == '5':
            success, message = tool.edit_gitignore()
        elif choice == '6':
            logging.info("Exiting GitHub Sync Tool.")
            print("\n👋 Goodbye!")
            sys.exit(0)
        else:
            success, message = False, "Invalid choice. Please select an option between 1 and 6."

        # Print results and log
        print("\n" + message)
        logging.info(message)

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    logging.info("Starting sync_github. py script...")
    main()
