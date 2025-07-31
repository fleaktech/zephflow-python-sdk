import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import requests

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
        """
        Download the JAR from GitHub, with retries and resume support.
        """
        retries = 3
        timeout_seconds = 30
        chunk_size = 8192

        tag = f"v{version}"
        jar_filename = f"sdk-{version}-all.jar"
        download_url = (
            f"https://github.com/{self.GITHUB_REPO}/releases/download/{tag}/{jar_filename}"
        )

        for attempt in range(retries):
            # --- Resume Logic ---
            # 1. Check if a partial file exists and get its size.
            resume_byte_pos = 0
            if jar_path.exists():
                resume_byte_pos = jar_path.stat().st_size

            # 2. Set the Range header to start the download from where it left off.
            headers = {"Range": f"bytes={resume_byte_pos}-"} if resume_byte_pos > 0 else {}

            try:
                print(f"Attempting to download ZephFlow SDK v{version}...")
                if resume_byte_pos > 0:
                    print(f"Resuming from byte {resume_byte_pos}.")

                with requests.get(
                    download_url, headers=headers, stream=True, timeout=timeout_seconds
                ) as r:
                    # Handle cases where the server doesn't support range requests
                    # or the file changed.
                    if r.status_code != 206 and resume_byte_pos > 0:
                        print("Server did not support resume. Starting download from beginning.")
                        resume_byte_pos = 0  # Reset for full download

                    # Check for any HTTP error status.
                    r.raise_for_status()

                    # Determine file open mode and initial downloaded size.
                    open_mode = "ab" if resume_byte_pos > 0 and r.status_code == 206 else "wb"
                    downloaded_size = resume_byte_pos

                    # Get total file size. For a resumed download, this is in 'Content-Range'.
                    if r.status_code == 206:
                        # e.g. Content-Range: bytes 12345-67890/67890
                        total_size_str = r.headers.get("Content-Range", "0/0").split("/")[-1]
                        total_size = int(total_size_str)
                    else:
                        total_size = int(r.headers.get("Content-Length", 0))

                    if total_size == 0:
                        raise RuntimeError("Could not determine total file size.")

                    with open(jar_path, open_mode) as f:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            percent = min(downloaded_size * 100 / total_size, 100)
                            progress = int(50 * percent / 100)
                            sys.stdout.write(
                                f'\r[{"#" * progress}{"." * (50 - progress)}] {percent:.1f}%'
                            )
                            sys.stdout.flush()

                print()  # New line after progress bar

                # Final check
                if jar_path.stat().st_size != total_size:
                    raise RuntimeError(
                        f"Download incomplete. Expected {total_size} bytes, "
                        f"got {jar_path.stat().st_size}."
                    )

                print(f"Successfully downloaded to {jar_path}")
                return  # Exit the function on success

            except requests.exceptions.RequestException as e:
                # If the range is not satisfiable (e.g., local file is corrupt/larger),
                # delete and restart.
                if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 416:
                    print("\nLocal file is invalid. Deleting and restarting download.")
                    jar_path.unlink()  # Delete corrupt partial file
                else:
                    print(f"\nDownload failed: {e}. Retrying... ({attempt + 1}/{retries})")

            if attempt < retries - 1:
                import time

                time.sleep(2)

        raise RuntimeError(f"Failed to download JAR from {download_url} after {retries} attempts.")
