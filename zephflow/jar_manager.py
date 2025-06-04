import json
import os
import platform
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from .versions import JAVA_SDK_VERSION


class JarManager:
    """Manages the ZephFlow Java SDK JAR file."""

    GITHUB_REPO = "fleaktech/zephflow-core"  # Update with your actual repo
    JAR_PATTERN = r"sdk-(\d+\.\d+\.\d+(?:-dev\.\d+[^.]*)?)-all\.jar"

    def __init__(self) -> None:
        self.cache_dir = self._get_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.version_file = self.cache_dir / "version.json"

    def _get_cache_dir(self) -> Path:
        """Get platform-specific cache directory."""
        if platform.system() == "Windows":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        elif platform.system() == "Darwin":  # macOS
            base = Path.home() / "Library" / "Caches"
        else:  # Linux and others
            base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

        return base / "zephflow"

    def get_jar_path(self, version: Optional[str] = None) -> str:
        """Get the path to the JAR file, downloading if necessary."""
        # Use configured version if none provided
        if version is None:
            version = JAVA_SDK_VERSION

        # Check for environment variable override (for local development)
        env_jar_path = os.environ.get("ZEPHFLOW_MAIN_JAR")
        if env_jar_path and os.path.exists(env_jar_path):
            print(f"Using JAR from environment variable: {env_jar_path}")
            return env_jar_path

        # Check Java version first
        self._check_java_version()

        # Construct expected JAR filename
        jar_filename = f"sdk-{version}-all.jar"
        jar_path = self.cache_dir / jar_filename

        # Check if we already have this version
        if jar_path.exists() and self._verify_cached_version(version):
            print(f"Using cached JAR: {jar_path}")
            return str(jar_path)

        # Download the JAR
        print(f"Downloading ZephFlow SDK v{version}...")
        self._download_jar(version, jar_path)

        # Update version cache
        self._update_version_cache(version)

        return str(jar_path)

    def _check_java_version(self) -> None:
        """Check if Java 17 or higher is installed."""
        try:
            result = subprocess.run(
                ["java", "-version"], capture_output=True, text=True, check=True
            )

            # Java version info is typically in stderr
            version_output = result.stderr or result.stdout

            # Extract version number (handles both old and new version formats)
            # Old: java version "1.8.0_281"
            # New: java version "17.0.1"
            version_match = re.search(r'version "(\d+)(?:\.(\d+))?', version_output)

            if version_match:
                major = int(version_match.group(1))
                # Handle old version format (1.x means Java x)
                if major == 1 and version_match.group(2):
                    major = int(version_match.group(2))

                if major < 17:
                    raise RuntimeError(
                        f"Java 17 or higher is required, but found Java {major}. "
                        "Please install Java 17 from https://adoptium.net/"
                    )
            else:
                print("Warning: Could not determine Java version")

        except FileNotFoundError:
            raise RuntimeError(
                "Java is not installed or not in PATH. "
                "Please install Java 17 from https://adoptium.net/"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to check Java version: {e}")

    def _verify_cached_version(self, version: str) -> bool:
        """Verify that the cached JAR matches the expected version."""
        if not self.version_file.exists():
            return False

        try:
            with open(self.version_file, "r") as f:
                cached_info = json.load(f)
                return bool(cached_info.get("version") == version)
        except (json.JSONDecodeError, KeyError):
            return False

    def _update_version_cache(self, version: str):
        """Update the version cache file."""
        with open(self.version_file, "w") as f:
            json.dump({"version": version}, f)

    def _download_jar(self, version: str, jar_path: Path):
        """Download the JAR from GitHub releases."""
        # Construct the download URL
        # Handle both release and dev versions
        if "-dev." in version:
            # Dev versions might be in pre-releases
            tag = f"v{version}"
        else:
            tag = f"v{version}"

        jar_filename = f"sdk-{version}-all.jar"
        download_url = (
            f"https://github.com/{self.GITHUB_REPO}/releases/download/" f"{tag}/{jar_filename}"
        )

        try:
            # Download with progress indicator
            def download_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = min(downloaded * 100 / total_size, 100)
                progress = int(50 * percent / 100)
                sys.stdout.write(f'\r[{"#" * progress}{"." * (50 - progress)}] {percent:.1f}%')
                sys.stdout.flush()

            urllib.request.urlretrieve(download_url, jar_path, download_progress)
            print()  # New line after progress bar

            # Verify the download
            if not jar_path.exists() or jar_path.stat().st_size == 0:
                raise RuntimeError("Downloaded JAR file is empty or missing")

            print(f"Successfully downloaded to {jar_path}")

        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise RuntimeError(
                    f"JAR file not found for version {version}. "
                    f"Please check if the release exists at "
                    f"https://github.com/{self.GITHUB_REPO}/releases"
                )
            else:
                raise RuntimeError(f"Failed to download JAR: HTTP {e.code}")
        except Exception as e:
            # Clean up partial download
            if jar_path.exists():
                jar_path.unlink()
            raise RuntimeError(f"Failed to download JAR: {e}")

    def clear_cache(self):
        """Clear the JAR cache directory."""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            print(f"Cleared cache at {self.cache_dir}")
