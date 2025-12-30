#!/usr/bin/env python3
"""
Git Sync Automation Script
A terminal-based tool for managing Git synchronization between local MacBook and GitHub.

Features:
- Check Python installation and version
- Sync files from local to GitHub (push)
- Sync files from GitHub to local (pull)
- User-friendly menu interface
- Exception handling for network and Git issues
"""

import sys
import subprocess
import platform
import os


class GitSyncManager:
    """Manager for Git synchronization operations."""
    
    def __init__(self):
        """Initialize the Git Sync Manager."""
        self.repo_path = os.getcwd()
        
    def check_python_installation(self):
        """
        Check if Python is installed and display version information.
        
        Returns:
            bool: True (always, since this code runs in Python)
        """
        print("\n" + "="*60)
        print("Python Installation Check")
        print("="*60)
        
        # Get Python version
        python_version = sys.version
        python_version_info = sys.version_info
        
        print(f"✓ Python is installed and running")
        print(f"  Version: {python_version_info.major}.{python_version_info.minor}.{python_version_info.micro}")
        print(f"  Full info: {python_version}")
        print(f"  Executable: {sys.executable}")
        print(f"  Platform: {platform.platform()}")
        print(f"  System: {platform.system()} {platform.release()}")
        
        return True
    
    def check_git_status(self):
        """
        Check Git status to see if there are changes to commit.
        
        Returns:
            tuple: (has_changes, status_output)
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path
            )
            has_changes = bool(result.stdout.strip())
            return has_changes, result.stdout
        except subprocess.CalledProcessError as e:
            print(f"✗ Error checking git status: {e}")
            return False, ""
    
    def sync_to_github(self):
        """
        Sync files from local machine to GitHub.
        Stages, commits, and pushes changes to the main branch.
        """
        print("\n" + "="*60)
        print("Syncing Files: Local → GitHub")
        print("="*60)
        
        try:
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            if result.returncode != 0:
                print("✗ Error: Not a git repository!")
                print(f"  Current directory: {self.repo_path}")
                print("  Please run this script from within a git repository.")
                return False
            
            # Check for changes
            has_changes, status = self.check_git_status()
            
            if not has_changes:
                print("✓ No local changes to commit")
                print("  Working directory is clean")
                return True
            
            # Show what files have changed
            print("\nFiles to be synced:")
            print(status)
            
            # Ask for commit message
            print("\nEnter a commit message (or press Enter for default):")
            commit_message = input("→ ").strip()
            
            if not commit_message:
                commit_message = "Auto-sync: Update files from local machine"
            
            # Stage all changes
            print("\n1. Staging changes...")
            subprocess.run(
                ["git", "add", "."],
                check=True,
                cwd=self.repo_path
            )
            print("   ✓ Changes staged")
            
            # Commit changes
            print("\n2. Committing changes...")
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True,
                cwd=self.repo_path
            )
            print("   ✓ Changes committed")
            
            # Push to remote
            print("\n3. Pushing to GitHub...")
            result = subprocess.run(
                ["git", "push", "origin", "main"],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            if result.returncode == 0:
                print("   ✓ Successfully pushed to GitHub!")
                if result.stdout:
                    print(f"\n{result.stdout}")
            else:
                # Try with current branch if main doesn't exist
                current_branch = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=self.repo_path
                ).stdout.strip()
                
                print(f"   Note: 'main' branch not found, trying '{current_branch}'...")
                result = subprocess.run(
                    ["git", "push", "origin", current_branch],
                    capture_output=True,
                    text=True,
                    cwd=self.repo_path
                )
                
                if result.returncode == 0:
                    print(f"   ✓ Successfully pushed to GitHub (branch: {current_branch})!")
                    if result.stdout:
                        print(f"\n{result.stdout}")
                else:
                    print(f"   ✗ Failed to push to GitHub")
                    print(f"   Error: {result.stderr}")
                    return False
            
            print("\n" + "="*60)
            print("Sync to GitHub completed successfully!")
            print("="*60)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"\n✗ Error during sync to GitHub:")
            print(f"  {e}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"  Details: {e.stderr}")
            return False
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            return False
    
    def sync_from_github(self):
        """
        Sync files from GitHub to local machine.
        Pulls the latest changes from the main branch.
        """
        print("\n" + "="*60)
        print("Syncing Files: GitHub → Local")
        print("="*60)
        
        try:
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            if result.returncode != 0:
                print("✗ Error: Not a git repository!")
                print(f"  Current directory: {self.repo_path}")
                print("  Please run this script from within a git repository.")
                return False
            
            # Check for uncommitted changes
            has_changes, status = self.check_git_status()
            
            if has_changes:
                print("⚠ Warning: You have uncommitted local changes!")
                print(status)
                print("\nOptions:")
                print("  1. Stash changes and pull (recommended)")
                print("  2. Discard local changes and pull")
                print("  3. Cancel")
                choice = input("→ Choose an option (1-3): ").strip()
                
                if choice == "1":
                    print("\nStashing local changes...")
                    subprocess.run(
                        ["git", "stash", "push", "-m", "Auto-stash before pull"],
                        check=True,
                        cwd=self.repo_path
                    )
                    print("✓ Changes stashed")
                elif choice == "2":
                    print("\n⚠ This will discard all local changes!")
                    confirm = input("Are you sure? (yes/no): ").strip().lower()
                    if confirm != "yes":
                        print("Cancelled.")
                        return False
                    subprocess.run(
                        ["git", "reset", "--hard"],
                        check=True,
                        cwd=self.repo_path
                    )
                    print("✓ Local changes discarded")
                else:
                    print("Cancelled.")
                    return False
            
            # Get current branch
            current_branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path
            ).stdout.strip()
            
            print(f"\nCurrent branch: {current_branch}")
            
            # Fetch from remote
            print("\n1. Fetching from GitHub...")
            subprocess.run(
                ["git", "fetch", "origin"],
                check=True,
                cwd=self.repo_path
            )
            print("   ✓ Fetch completed")
            
            # Pull changes
            print(f"\n2. Pulling changes from origin/{current_branch}...")
            result = subprocess.run(
                ["git", "pull", "origin", current_branch],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            if result.returncode == 0:
                print("   ✓ Successfully pulled from GitHub!")
                if result.stdout:
                    print(f"\n{result.stdout}")
                
                # Check if there was a merge conflict (CONFLICT appears in output)
                if "CONFLICT" in result.stdout:
                    print("\n⚠ MERGE CONFLICT DETECTED!")
                    print("  Please resolve conflicts manually:")
                    print("  1. Check files with conflicts: git status")
                    print("  2. Edit conflicted files")
                    print("  3. Stage resolved files: git add <file>")
                    print("  4. Complete merge: git commit")
                    return False
            else:
                print(f"   ✗ Failed to pull from GitHub")
                print(f"   Error: {result.stderr}")
                
                # Check for specific error messages
                if "divergent branches" in result.stderr.lower():
                    print("\n⚠ Your branch has diverged from remote!")
                    print("  Consider using: git pull --rebase origin " + current_branch)
                
                return False
            
            print("\n" + "="*60)
            print("Sync from GitHub completed successfully!")
            print("="*60)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"\n✗ Error during sync from GitHub:")
            print(f"  {e}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"  Details: {e.stderr}")
            return False
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            return False
    
    def display_menu(self):
        """Display the main menu."""
        print("\n" + "="*60)
        print(" "*15 + "Git Sync Automation Tool")
        print("="*60)
        print("\nMenue:")
        print("  1. Check Python Installation")
        print("  2. Sync files from MacBook to GitHub (Push)")
        print("  3. Sync files from GitHub to MacBook (Pull)")
        print("  4. Exit")
        print("\n" + "-"*60)
    
    def run(self):
        """Run the main program loop."""
        print("\n" + "="*60)
        print(" "*10 + "Welcome to Git Sync Automation Tool")
        print("="*60)
        print(f"\nWorking directory: {self.repo_path}")
        
        while True:
            try:
                self.display_menu()
                choice = input("Enter your choice (1-4): ").strip()
                
                if choice == "1":
                    self.check_python_installation()
                    
                elif choice == "2":
                    self.sync_to_github()
                    
                elif choice == "3":
                    self.sync_from_github()
                    
                elif choice == "4":
                    print("\n" + "="*60)
                    print("Thank you for using Git Sync Automation Tool!")
                    print("="*60 + "\n")
                    sys.exit(0)
                    
                else:
                    print("\n✗ Invalid choice. Please enter a number between 1 and 4.")
                
                # Wait for user to press Enter before showing menu again
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\n" + "="*60)
                print("Program interrupted by user.")
                print("="*60 + "\n")
                sys.exit(0)
            except Exception as e:
                print(f"\n✗ Unexpected error: {e}")
                input("\nPress Enter to continue...")


def main():
    """Main entry point for the script."""
    try:
        manager = GitSyncManager()
        manager.run()
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
