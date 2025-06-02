#!/usr/bin/env python3
"""
Release automation script for ZephFlow Python SDK.

This script automates the release process after manual version updates in zephflow/versions.py.
It reads versions, validates them, runs tests, creates git tags, and pushes them.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Tuple, Optional


def run_command(cmd: list[str], dry_run: bool = False, capture_output: bool = False) -> Optional[str]:
  """
  Execute a shell command.

  Args:
      cmd: Command as list of strings
      dry_run: If True, only print the command without executing
      capture_output: If True, capture and return the output

  Returns:
      Command output if capture_output is True, None otherwise

  Raises:
      SystemExit: If command fails
  """
  print(f"{'[DRY RUN] Would execute' if dry_run else 'Executing'}: {' '.join(cmd)}")

  if dry_run:
    return None

  try:
    result = subprocess.run(
      cmd,
      check=True,
      capture_output=capture_output,
      text=True
    )
    if capture_output:
      return result.stdout.strip()
    return None
  except subprocess.CalledProcessError as e:
    print(f"Error: Command failed with exit code {e.returncode}")
    if e.stderr:
      print(f"stderr: {e.stderr}")
    sys.exit(1)


def read_versions(version_file: Path) -> Tuple[str, str]:
  """
  Read Python and Java SDK versions from versions.py file.

  Args:
      version_file: Path to the versions.py file

  Returns:
      Tuple of (PYTHON_SDK_VERSION, JAVA_SDK_VERSION)

  Raises:
      SystemExit: If file doesn't exist or versions can't be parsed
  """
  if not version_file.exists():
    print(f"Error: Version file not found: {version_file}")
    sys.exit(1)

  print(f"Reading versions from {version_file}")

  try:
    content = version_file.read_text()

    # Use regex to find the version assignments
    python_match = re.search(r'PYTHON_SDK_VERSION\s*=\s*["\']([^"\']+)["\']', content)
    java_match = re.search(r'JAVA_SDK_VERSION\s*=\s*["\']([^"\']+)["\']', content)

    if not python_match or not java_match:
      print("Error: Could not find version definitions in versions.py")
      sys.exit(1)

    python_version = python_match.group(1)
    java_version = java_match.group(1)

    print(f"  Python SDK version: {python_version}")
    print(f"  Java SDK version: {java_version}")

    return python_version, java_version

  except Exception as e:
    print(f"Error reading versions: {e}")
    sys.exit(1)


def validate_pypi_version(version: str) -> bool:
  """
  Validate that version string follows PEP 440 for PyPI.

  Args:
      version: Version string to validate

  Returns:
      True if valid, False otherwise
  """
  # PEP 440 regex pattern (simplified but covers most cases)
  # Matches: X.Y.Z, X.Y.ZaN, X.Y.ZbN, X.Y.ZrcN, X.Y.Z.postN, X.Y.Z.devN
  pattern = r'^(\d+!)?\d+(\.\d+)*((a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?$'
  return bool(re.match(pattern, version))


def validate_version_sync(python_version: str, java_version: str) -> bool:
  """
  Validate that Python and Java versions have synchronized major.minor versions.

  Args:
      python_version: Python SDK version
      java_version: Java SDK version

  Returns:
      True if major.minor are aligned, False otherwise
  """
  # Extract major.minor from Python version
  python_match = re.match(r'^(\d+\.\d+)', python_version)
  if not python_match:
    return False
  python_major_minor = python_match.group(1)

  # Extract major.minor from Java version
  java_match = re.match(r'^(\d+\.\d+)', java_version)
  if not java_match:
    return False
  java_major_minor = java_match.group(1)

  return python_major_minor == java_major_minor


def check_git_status(dry_run: bool = False) -> None:
  """
  Check if git working directory is clean.

  Args:
      dry_run: If True, skip the check

  Raises:
      SystemExit: If working directory is dirty
  """
  if dry_run:
    print("[DRY RUN] Would check git status")
    return

  print("Checking git status...")

  # Check for uncommitted changes
  result = subprocess.run(
    ["git", "status", "--porcelain"],
    capture_output=True,
    text=True
  )

  if result.stdout.strip():
    print("Error: Working directory is not clean. Please commit or stash your changes.")
    print("Uncommitted changes:")
    print(result.stdout)
    sys.exit(1)

  print("  Working directory is clean")


def verify_version_in_head(version_file: Path, python_version: str, java_version: str, dry_run: bool = False) -> None:
  """
  Verify that HEAD commit contains the expected versions in versions.py.

  Args:
      version_file: Path to versions.py
      python_version: Expected Python SDK version
      java_version: Expected Java SDK version
      dry_run: If True, skip the check

  Raises:
      SystemExit: If versions don't match
  """
  if dry_run:
    print("[DRY RUN] Would verify versions in HEAD commit")
    return

  print("Verifying versions in HEAD commit...")

  # Get content of versions.py from HEAD
  relative_path = version_file.relative_to(Path.cwd())
  head_content = run_command(
    ["git", "show", f"HEAD:{relative_path}"],
    capture_output=True
  )

  if not head_content:
    print("Error: Could not read versions.py from HEAD commit")
    sys.exit(1)

  # Check if versions match
  if f'PYTHON_SDK_VERSION = "{python_version}"' not in head_content and \
      f"PYTHON_SDK_VERSION = '{python_version}'" not in head_content:
    print(f"Error: Python version {python_version} not found in HEAD commit")
    sys.exit(1)

  if f'JAVA_SDK_VERSION = "{java_version}"' not in head_content and \
      f"JAVA_SDK_VERSION = '{java_version}'" not in head_content:
    print(f"Error: Java version {java_version} not found in HEAD commit")
    sys.exit(1)

  print("  Versions verified in HEAD commit")


def run_tests(dry_run: bool = False) -> None:
  """
  Run unit tests using pytest with coverage.

  Args:
      dry_run: If True, skip running tests

  Raises:
      SystemExit: If tests fail
  """
  print("\nRunning unit tests...")

  cmd = ["poetry", "run", "pytest", "tests/", "--cov=zephflow", "--cov-report=term-missing"]

  if dry_run:
    print(f"[DRY RUN] Would execute: {' '.join(cmd)}")
    return

  try:
    subprocess.run(cmd, check=True)
    print("  All tests passed!")
  except subprocess.CalledProcessError:
    print("Error: Unit tests failed. Aborting release.")
    sys.exit(1)


def confirm_action(message: str) -> bool:
  """
  Ask user for confirmation.

  Args:
      message: Confirmation message

  Returns:
      True if user confirms, False otherwise
  """
  while True:
    response = input(f"{message} (Y/n): ").strip().lower()
    if response in ['y', 'yes', '']:
      return True
    elif response in ['n', 'no']:
      return False
    else:
      print("Please enter Y or n")


def create_and_push_tag(version: str, tag_message: str, dry_run: bool = False) -> None:
  """
  Create an annotated git tag and push it to origin.

  Args:
      version: Version string to use as tag name
      tag_message: Message for the annotated tag
      dry_run: If True, skip actual git commands
  """
  tag_name = version

  print(f"\nCreating git tag: {tag_name}")
  print(f"Tag message: {tag_message}")

  if not dry_run and not confirm_action("Create and push this tag?"):
    print("Tag creation cancelled.")
    return

  # Create annotated tag
  run_command(
    ["git", "tag", "-a", tag_name, "-m", tag_message],
    dry_run=dry_run
  )

  print(f"\nPushing tag {tag_name} to origin...")

  # Push tag to origin
  run_command(
    ["git", "push", "origin", tag_name],
    dry_run=dry_run
  )

  if not dry_run:
    print(f"\nSuccessfully created and pushed tag {tag_name}")


def main():
  """Main entry point for the release script."""
  parser = argparse.ArgumentParser(
    description="Release automation script for ZephFlow Python SDK"
  )
  parser.add_argument(
    "--tag-message", "--message", "-m",
    help="Custom message for the annotated Git tag",
    dest="tag_message"
  )
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print what actions would be taken without executing them"
  )

  args = parser.parse_args()

  # Determine project root and version file path
  script_dir = Path(__file__).parent
  project_root = script_dir.parent
  version_file = project_root / "zephflow" / "versions.py"

  # Change to project root directory
  os.chdir(project_root)
  print(f"Working directory: {project_root}")

  # Step 1: Read versions
  python_version, java_version = read_versions(version_file)

  # Step 2: Check git status
  check_git_status(args.dry_run)

  # Step 3: Validate Python SDK version for PyPI
  print("\nValidating version formats...")
  if not validate_pypi_version(python_version):
    print(f"Error: Python version '{python_version}' is not valid for PyPI (PEP 440)")
    print("Valid formats: X.Y.Z, X.Y.ZaN, X.Y.ZbN, X.Y.ZrcN, X.Y.Z.postN, X.Y.Z.devN")
    sys.exit(1)
  print(f"  Python version '{python_version}' is valid for PyPI")

  # Step 4: Validate version synchronization
  if not validate_version_sync(python_version, java_version):
    print(f"Error: Major.minor versions are not synchronized")
    print(f"  Python: {python_version}")
    print(f"  Java: {java_version}")
    sys.exit(1)
  print("  Major.minor versions are synchronized")

  # Step 5: Verify versions in HEAD commit
  verify_version_in_head(version_file, python_version, java_version, args.dry_run)

  # Step 6: Run unit tests
  run_tests(args.dry_run)

  # Step 7: Create and push tag
  tag_message = args.tag_message or f"Release version {python_version}"
  create_and_push_tag(python_version, tag_message, args.dry_run)

  print("\nRelease process completed successfully!")
  if args.dry_run:
    print("(This was a dry run - no actual changes were made)")


if __name__ == "__main__":
  main()
