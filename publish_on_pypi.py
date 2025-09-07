"""
This script automates the process of cleaning a Python repository, 
building a source distribution (sdist), and publishing the package to PyPI or Test PyPI. 
It provides a simple CLI interface to toggle between
release and test modes.
"""

import argparse
import shutil
import subprocess
import sys
import re
from pathlib import Path

here = Path(__file__).parent.resolve()

# GitHub repository base URL for images
GITHUB_RAW_URL = "https://raw.githubusercontent.com/pypoulp/types-oiio-python/main/"


def replace_image_urls_for_pypi():
    """
    Replace local image URLs with GitHub URLs in README.md for PyPI.
    Returns the original content for restoration.
    """
    readme_path = here / "README.md"
    original_content = readme_path.read_text(encoding='utf-8')
    
    # Replace relative image paths with GitHub raw URLs
    modified_content = re.sub(
        r'!\[([^\]]*)\]\(img/([^)]+)\)',
        rf'![\1]({GITHUB_RAW_URL}img/\2)',
        original_content
    )
    
    if modified_content != original_content:
        readme_path.write_text(modified_content, encoding='utf-8')
        print("✓ Replaced local image URLs with GitHub URLs in README.md")
    
    return original_content


def restore_readme(original_content):
    """Restore the original README.md content."""
    readme_path = here / "README.md"
    readme_path.write_text(original_content, encoding='utf-8')
    print("✓ Restored original README.md")


def cleanup():
    """Clean the dist folder and build artifacts."""
    dist_dir = here / "dist"
    build_dir = here / "build"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)


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

    # Store original README content before modifications
    original_readme = None
    
    try:
        # Clean build artifacts
        cleanup()
        
        # Replace image URLs for PyPI
        original_readme = replace_image_urls_for_pypi()
        
        # Build the package
        subprocess.run(["python", "-m", "build"], check=True)
        
        # Publish to PyPI
        publish_to_pypi(repository_url)
        
        # If we get here, publishing was successful
        print("✓ Publishing completed successfully!")
        
    except KeyboardInterrupt:
        print("\n✗ Publishing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Publishing failed: {e}")
        sys.exit(1)
    finally:
        # Always restore the original README
        if original_readme is not None:
            restore_readme(original_readme)


if __name__ == "__main__":
    main()
