"""
Command-line interface for ZephFlow Python SDK.

Usage:
    python -m zephflow --version
    python -m zephflow --clear-cache
    python -m zephflow --check-java
    python -m zephflow --download-jar 0.2.1
"""

import argparse
import sys

from . import __version__
from .jar_manager import JarManager
from .versions import JAVA_SDK_VERSION


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ZephFlow Python SDK CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m zephflow --version              Show version information
  python -m zephflow --clear-cache          Clear the JAR cache
  python -m zephflow --check-java           Check Java installation
  python -m zephflow --download-jar 0.2.1   Download JAR version 0.2.1
        """,
    )

    parser.add_argument("--version", action="store_true", help="Show version information")

    parser.add_argument("--clear-cache", action="store_true", help="Clear the JAR cache directory")

    parser.add_argument(
        "--check-java", action="store_true", help="Check if Java 17 is properly installed"
    )

    parser.add_argument(
        "--download-jar",
        metavar="VERSION",
        help="Download a specific version of the JAR (e.g., 0.2.1)",
    )

    args = parser.parse_args()

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    if args.version:
        print(f"ZephFlow Python SDK version {__version__}")
        print(f"Required Java SDK version: {JAVA_SDK_VERSION}")
        return 0

    if args.clear_cache:
        jar_manager = JarManager()
        jar_manager.clear_cache()
        return 0

    if args.check_java:
        jar_manager = JarManager()
        try:
            jar_manager._check_java_version()
            print("✅ Java 17 or higher is properly installed")
            return 0
        except RuntimeError as e:
            print(f"❌ {e}")
            return 1

    if args.download_jar:
        jar_manager = JarManager()
        try:
            jar_path = jar_manager.get_jar_path(args.download_jar)
            print(f"✅ JAR available at: {jar_path}")
            return 0
        except Exception as e:
            print(f"❌ Failed to download JAR: {e}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
