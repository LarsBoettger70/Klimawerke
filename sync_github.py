#!/usr/bin/env python3
"""
GitHub Sync Automation Script for MacBook

This script automates syncing files between a local MacBook and a GitHub repository.
It provides a terminal menu interface for checking Python installation, syncing files
to/from GitHub, and handling empty folders with .gitkeep files.

Features:
1. Check Python installation and version
2. Sync files from MacBook to GitHub (with .gitkeep for empty folders)
3. Sync files from GitHub to MacBook (with conflict detection)
4. Terminal menu interface

Usage:
    python3 sync_github.py
"""

import subprocess
import sys
import os
import platform
from pathlib import Path
from typing import List, Tuple, Optional


class GitHubSyncTool:
    """Handles GitHub sync operations for local repositories."""
    
    def __init__(self):
        """Initialize the sync tool."""
        self.repo_path = Path.cwd()
        
    def check_python_installation(self) -> Tuple[bool, str]:
        """
        Check if Python is installed and get version information.
        
        Returns:
            Tuple[bool, str]: (is_installed, version_info)
        """
        try:
            version = sys.version
            version_info = sys.version_info
            python_path = sys.executable
            
            info = f"""
Python Installation Status:
{'='*50}
Status: ✓ Installed
Version: {version_info.major}.{version_info.minor}.{version_info.micro}
Full Version: {version}
Executable Path: {python_path}
Platform: {platform.platform()}
Architecture: {platform.machine()}
{'='*50}
"""
            return True, info
        except Exception as e:
            return False, f"Error checking Python installation: {str(e)}"
    
    def is_git_repo(self) -> bool:
        """
        Check if current directory is a Git repository.
        
        Returns:
            bool: True if in a git repository, False otherwise
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_current_branch(self) -> Tuple[bool, str]:
        """
        Get the current Git branch name.
        
        Returns:
            Tuple[bool, str]: (success, branch_name)
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch_name = result.stdout.strip()
            return True, branch_name
        except subprocess.CalledProcessError as e:
            return False, f"Error getting current branch: {e.stderr}"
    
    def find_empty_directories(self) -> List[Path]:
        """
        Find all empty directories in the repository (excluding .git).
        
        Returns:
            List[Path]: List of empty directory paths
        """
        empty_dirs = []
        
        for root, dirs, files in os.walk(self.repo_path):
            # Skip .git directory
            dirs[:] = [d for d in dirs if d != '.git']
            
            # Check if directory is empty (no files and no subdirectories)
            if not dirs and not files:
                empty_dirs.append(Path(root))
        
        return empty_dirs
    
    def add_gitkeep_to_empty_dirs(self) -> Tuple[bool, str]:
        """
        Add .gitkeep files to all empty directories.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            empty_dirs = self.find_empty_directories()
            
            if not empty_dirs:
                return True, "No empty directories found."
            
            created_count = 0
            for dir_path in empty_dirs:
                gitkeep_path = dir_path / '.gitkeep'
                if not gitkeep_path.exists():
                    gitkeep_path.touch()
                    created_count += 1
            
            message = f"Created .gitkeep files in {created_count} empty directories:\n"
            for dir_path in empty_dirs:
                rel_path = dir_path.relative_to(self.repo_path)
                message += f"  - {rel_path}\n"
            
            return True, message
        except Exception as e:
            return False, f"Error adding .gitkeep files: {str(e)}"
    
    def get_git_status(self) -> Tuple[bool, str]:
        """
        Get the current git status.
        
        Returns:
            Tuple[bool, str]: (success, status_output)
        """
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"Error getting git status: {e.stderr}"
    
    def sync_to_github(self, commit_message: Optional[str] = None) -> Tuple[bool, str]:
        """
        Sync files from local MacBook to GitHub.
        
        Steps:
        1. Add .gitkeep to empty directories
        2. Stage all changes
        3. Commit changes
        4. Push to remote main branch
        
        Args:
            commit_message: Optional custom commit message
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        if not self.is_git_repo():
            return False, "Error: Not in a git repository."
        
        try:
            output = []
            
            # Step 1: Add .gitkeep to empty directories
            output.append("Step 1: Checking for empty directories...")
            success, message = self.add_gitkeep_to_empty_dirs()
            output.append(message)
            
            # Step 2: Check for changes
            output.append("\nStep 2: Checking for changes...")
            success, status = self.get_git_status()
            if not success:
                return False, "\n".join(output) + f"\n{status}"
            
            if not status.strip():
                output.append("No changes to commit.")
                return True, "\n".join(output)
            
            output.append(f"Changes detected:\n{status}")
            
            # Step 3: Stage all changes
            output.append("\nStep 3: Staging all changes...")
            result = subprocess.run(
                ['git', 'add', '.'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            output.append("✓ Changes staged successfully")
            
            # Step 4: Commit changes
            output.append("\nStep 4: Committing changes...")
            if not commit_message:
                commit_message = "Automated sync from MacBook"
            
            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            output.append(f"✓ Changes committed: {commit_message}")
            
            # Step 5: Get current branch
            output.append("\nStep 5: Getting current branch...")
            success, branch_name = self.get_current_branch()
            if not success:
                return False, "\n".join(output) + f"\n{branch_name}"
            output.append(f"Current branch: {branch_name}")
            
            # Step 6: Push to remote
            output.append(f"\nStep 6: Pushing to remote branch '{branch_name}'...")
            result = subprocess.run(
                ['git', 'push', 'origin', branch_name],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            output.append("✓ Changes pushed successfully")
            output.append(result.stdout)
            
            return True, "\n".join(output)
            
        except subprocess.CalledProcessError as e:
            error_msg = f"\nError during sync: {e.stderr if e.stderr else str(e)}"
            return False, "\n".join(output) + error_msg
        except Exception as e:
            return False, "\n".join(output) + f"\nUnexpected error: {str(e)}"
    
    def sync_from_github(self) -> Tuple[bool, str]:
        """
        Sync files from GitHub to local MacBook.
        
        Steps:
        1. Fetch from remote
        2. Check for conflicts
        3. Pull changes
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        if not self.is_git_repo():
            return False, "Error: Not in a git repository."
        
        try:
            output = []
            
            # Step 1: Fetch from remote
            output.append("Step 1: Fetching from remote...")
            result = subprocess.run(
                ['git', 'fetch', 'origin'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            output.append("✓ Fetched from remote")
            
            # Step 2: Check for local changes
            output.append("\nStep 2: Checking for local changes...")
            success, status = self.get_git_status()
            if not success:
                return False, "\n".join(output) + f"\n{status}"
            
            if status.strip():
                output.append("⚠ Warning: You have uncommitted local changes:")
                output.append(status)
                output.append("\nPlease commit or stash your changes before pulling.")
                return False, "\n".join(output)
            
            # Step 3: Get current branch
            output.append("\nStep 3: Getting current branch...")
            success, branch_name = self.get_current_branch()
            if not success:
                return False, "\n".join(output) + f"\n{branch_name}"
            output.append(f"Current branch: {branch_name}")
            
            # Step 4: Check for divergence
            output.append("\nStep 4: Checking for remote updates...")
            # Use the current branch's upstream if set, otherwise use origin/<branch>
            result = subprocess.run(
                ['git', 'rev-list', f'HEAD...origin/{branch_name}', '--count'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                output.append(f"⚠ Warning: Could not compare with origin/{branch_name}")
                output.append("Proceeding with pull anyway...")
            else:
                divergence_count = result.stdout.strip()
                if divergence_count == '0':
                    output.append("✓ Already up to date with remote")
                    return True, "\n".join(output)
            
            # Step 5: Pull changes
            output.append(f"\nStep 5: Pulling changes from origin/{branch_name}...")
            result = subprocess.run(
                ['git', 'pull', 'origin', branch_name, '--no-rebase'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                # Check for merge conflicts
                if 'CONFLICT' in result.stdout or 'CONFLICT' in result.stderr:
                    output.append("✗ MERGE CONFLICT DETECTED!")
                    output.append(result.stdout)
                    output.append(result.stderr)
                    output.append("\nPlease resolve conflicts manually:")
                    output.append("1. Fix conflicts in affected files")
                    output.append("2. Run: git add <resolved-files>")
                    output.append("3. Run: git commit")
                    return False, "\n".join(output)
                else:
                    output.append(f"✗ Pull failed: {result.stderr}")
                    return False, "\n".join(output)
            
            output.append("✓ Changes pulled successfully")
            output.append(result.stdout)
            
            return True, "\n".join(output)
            
        except subprocess.CalledProcessError as e:
            error_msg = f"\nError during sync: {e.stderr if e.stderr else str(e)}"
            return False, "\n".join(output) + error_msg
        except Exception as e:
            return False, "\n".join(output) + f"\nUnexpected error: {str(e)}"


def print_menu():
    """Print the main menu options."""
    print("\n" + "="*60)
    print("GitHub Sync Tool - Main Menu")
    print("="*60)
    print("1. Check Python Installation")
    print("2. Sync Files from MacBook to GitHub")
    print("3. Sync Files from GitHub to MacBook")
    print("4. Exit")
    print("="*60)


def main():
    """Main entry point for the script."""
    print("\n🚀 GitHub Sync Automation Tool")
    print("Repository:", Path.cwd())
    
    tool = GitHubSyncTool()
    
    while True:
        print_menu()
        
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == '1':
                # Check Python installation
                print("\n" + "-"*60)
                print("Checking Python Installation...")
                print("-"*60)
                success, message = tool.check_python_installation()
                print(message)
                input("\nPress Enter to continue...")
                
            elif choice == '2':
                # Sync to GitHub
                print("\n" + "-"*60)
                print("Syncing from MacBook to GitHub...")
                print("-"*60)
                
                # Ask for commit message
                commit_msg = input("\nEnter commit message (or press Enter for default): ").strip()
                if not commit_msg:
                    commit_msg = None
                
                print("\nStarting sync process...")
                success, message = tool.sync_to_github(commit_msg)
                print(message)
                
                if success:
                    print("\n✓ Sync completed successfully!")
                else:
                    print("\n✗ Sync failed. Please check the error messages above.")
                
                input("\nPress Enter to continue...")
                
            elif choice == '3':
                # Sync from GitHub
                print("\n" + "-"*60)
                print("Syncing from GitHub to MacBook...")
                print("-"*60)
                
                print("\nStarting sync process...")
                success, message = tool.sync_from_github()
                print(message)
                
                if success:
                    print("\n✓ Sync completed successfully!")
                else:
                    print("\n✗ Sync failed. Please check the error messages above.")
                
                input("\nPress Enter to continue...")
                
            elif choice == '4':
                # Exit
                print("\n👋 Thank you for using GitHub Sync Tool. Goodbye!")
                sys.exit(0)
                
            else:
                print("\n❌ Invalid choice. Please enter a number between 1 and 4.")
                input("\nPress Enter to continue...")
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
