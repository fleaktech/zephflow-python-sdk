#!/usr/bin/env python3
"""
Release script for ZephFlow Python SDK.

This script helps coordinate releases between the Java SDK and Python SDK.
It ensures version numbers stay in sync and handles the release process.

Usage:
    python scripts/release.py --version 0.2.1
    python scripts/release.py --version 0.2.2-rc.1
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True):
  """Run a shell command and return the output."""
  print(f"Running: {cmd}")
  result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
  if check and result.returncode != 0:
    print(f"Error: {result.stderr}")
    sys.exit(1)
  return result


def check_poetry_installed():
  """Check if Poetry is installed."""
  result = run_command("poetry --version", check=False)
  if result.returncode != 0:
    print("Error: Poetry is not installed.")
    print("Install it with: curl -sSL https://install.python-poetry.org | python3 -")
    sys.exit(1)
  print(f"Using {result.stdout.strip()}")


def create_git_tag_for_version(version):
  """Create git tag for the version (used by poetry-dynamic-versioning)."""
  # Check if we have uncommitted changes
  result = run_command("git status --porcelain", check=False)
  if result.stdout.strip():
    print("Error: You have uncommitted changes. Please commit them first.")
    sys.exit(1)

  # Check if tag already exists
  result = run_command(f"git tag -l v{version}", check=False)
  if result.stdout.strip():
    print(f"Error: Tag v{version} already exists")
    sys.exit(1)

  # Create tag
  run_command(f'git tag -a v{version} -m "Release version {version}"')
  print(f"Created tag v{version}")

  # Update jar_manager.py GITHUB_REPO if needed
  root_dir = Path(__file__).parent.parent
  jar_manager_file = root_dir / "zephflow" / "jar_manager.py"
  content = jar_manager_file.read_text()
  # Ensure the correct repo is set
  content = re.sub(
    r'GITHUB_REPO = "[^"]*"',
    'GITHUB_REPO = "fleaktech/zephflow-core"',
    content
  )
  jar_manager_file.write_text(content)
  print(f"Updated {jar_manager_file}")


def check_java_release(version):
  """Check if the Java SDK release exists on GitHub."""
  # For now, just print a reminder
  print("\n" + "=" * 60)
  print("IMPORTANT: Before releasing the Python SDK:")
  print(f"1. Ensure Java SDK version {version} is released at:")
  print(f"   https://github.com/fleaktech/zephflow-core/releases/tag/v{version}")
  print(f"2. Verify the JAR file 'sdk-{version}-all.jar' is available")
  print("=" * 60 + "\n")

  response = input("Has the Java SDK been released? (y/n): ")
  if response.lower() != 'y':
    print("Please release the Java SDK first.")
    sys.exit(1)


def install_dependencies():
  """Install project dependencies."""
  print("Installing dependencies...")
  run_command("poetry install")


def build_package():
  """Build the Python package."""
  print("Building package...")
  run_command("poetry build")
  print("Package built successfully")


def run_tests():
  """Run tests if they exist."""
  if Path("tests").exists():
    print("Running tests...")
    run_command("poetry run pytest tests/")
    print("Tests passed")
  else:
    print("No tests directory found, skipping tests")


def run_linting():
  """Run linting and formatting checks."""
  print("Running code quality checks...")

  # Format check
  result = run_command("poetry run black --check zephflow/", check=False)
  if result.returncode != 0:
    print("Code formatting issues found. Run 'poetry run black zephflow/' to fix.")
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
      sys.exit(1)

  # Import sort check
  result = run_command("poetry run isort --check zephflow/", check=False)
  if result.returncode != 0:
    print("Import sorting issues found. Run 'poetry run isort zephflow/' to fix.")
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
      sys.exit(1)

  # Linting
  result = run_command("poetry run flake8 zephflow/", check=False)
  if result.returncode != 0:
    print("Linting issues found.")
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
      sys.exit(1)

  print("Code quality checks completed")


def push_git_tag():
  """Push git tags to GitHub."""
  response = input("Push tag to GitHub? (y/n): ")
  if response.lower() == 'y':
    run_command("git push origin --tags")
    print("Tag pushed to GitHub")


def publish_to_pypi(dry_run=False):
  """Publish to PyPI."""
  if dry_run:
    print("Dry run - would publish to PyPI")
    run_command("poetry publish --dry-run")
  else:
    response = input("Publish to PyPI? (y/n): ")
    if response.lower() == 'y':
      run_command("poetry publish")
      print("Published to PyPI!")
    else:
      print("Skipping PyPI publication")


def main():
  parser = argparse.ArgumentParser(description="Release ZephFlow Python SDK")
  parser.add_argument("--version", required=True, help="Version to release (e.g., 0.2.1)")
  parser.add_argument("--skip-java-check", action="store_true",
                      help="Skip checking for Java SDK release")
  parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
  parser.add_argument("--skip-linting", action="store_true", help="Skip linting checks")
  parser.add_argument("--skip-tag", action="store_true", help="Skip creating git tag")
  parser.add_argument("--dry-run", action="store_true",
                      help="Perform a dry run (don't actually publish)")

  args = parser.parse_args()

  print(f"Preparing to release ZephFlow Python SDK version {args.version}")

  # Check Poetry is installed
  check_poetry_installed()

  # Check Java release
  if not args.skip_java_check:
    check_java_release(args.version)

  # Create git tag for dynamic versioning
  create_git_tag_for_version(args.version)

  # Install dependencies
  install_dependencies()

  # Run linting
  if not args.skip_linting:
    run_linting()

  # Run tests
  if not args.skip_tests:
    run_tests()

  # Build package
  build_package()

  # Push git tag
  if not args.skip_tag:
    push_git_tag()

  # Publish to PyPI
  publish_to_pypi(dry_run=args.dry_run)

  print("\n" + "=" * 60)
  print("Release preparation complete!")
  print("\nNext steps:")
  print("1. If you haven't already, push the tag: git push origin --tags")
  print("2. Create a GitHub release from the tag")
  print("3. The GitHub Action will automatically publish to PyPI")
  print("\nNote: Version is now managed by git tags via poetry-dynamic-versioning")
  print("The package version will be automatically set from the git tag.")
  print("=" * 60)


if __name__ == "__main__":
  main()
