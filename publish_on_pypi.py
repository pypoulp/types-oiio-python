"""
This script automates the process of cleaning a Python repository, 
building a source distribution (sdist), and publishing the package to PyPI or Test PyPI. 
It provides a simple CLI interface to toggle between
release and test modes.
"""

import argparse
import subprocess
import sys
from pathlib import Path

here = Path(__file__).parent.resolve()


def run_command(command):
    """Run a shell command and handle errors gracefully."""
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error while running command: {e.cmd}")
        sys.exit(1)


def publish_to_pypi(repository_url):
    """
    Publish the package to the specified PyPI repository.

    Lists all files in the `dist` directory to be uploaded and asks for user confirmation
    before proceeding with the upload.
    """
    print(f"Publishing to {repository_url}...")

    dist_files = list((here / "dist").glob("*"))

    print("=" * 80)
    print(f"Publishing {len(dist_files)} files to PyPI: {repository_url}")
    for file in dist_files:
        print(file)
    print("=" * 80)

    confirm = (
        input("Are you sure you want to publish to PyPI? (yes/no): ").strip().lower()
    )
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    dist_empty = len(dist_files) == 0
    if dist_empty:
        print("No files to publish.")
        sys.exit(0)

    run_command(f"twine upload --repository {repository_url} dist/*")


def main():
    """
    Main entry point for the script.

    Parses command-line arguments to determine the mode (release or test) and
    performs cleanup, builds the source distribution, and publishes it to PyPI.
    """
    parser = argparse.ArgumentParser(description="Publish Python packages to PyPI.")
    parser.add_argument(
        "--release", action="store_true", help="Publish to PyPI instead of Test PyPI."
    )
    args = parser.parse_args()

    if args.release:
        confirm = (
            input("Using RELEASE mode, do you want to continue? (yes/no): ")
            .strip()
            .lower()
        )
        if confirm != "yes":
            print("Aborted.")
            sys.exit(0)
        repository_url = "pypi"
    else:
        repository_url = "testpypi"

    # Clean, build, and publish
    subprocess.run(["python", "-m", "build"], check=True)

    publish_to_pypi(repository_url)


if __name__ == "__main__":
    main()
