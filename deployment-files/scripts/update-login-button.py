#!/usr/bin/env python3
import argparse
import re
import sys
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="Update the URL in the Login button's onclick handler.")
    parser.add_argument(
        "new_url",
        help="The new login URL to set (e.g. https://.../login?client_id=...&response_type=code…)")
    parser.add_argument(
        "file_path",
        nargs="?",
        default=f"{os.getcwd()}/frontend/script/global.js",
        help="Path to the JS/HTML file containing the <button>Login</button> (default: %(default)s)")
    args = parser.parse_args()

    file_path = Path(args.file_path)
    if not file_path.is_file():
        print(f"❌ File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    original = file_path.read_text(encoding="utf-8")

    # Backup original
    backup = file_path.with_name(file_path.name + ".bak")
    backup.write_text(original, encoding="utf-8")

    # Regex to find: <button ... onclick="window.location.href='ANY_URL'" ...>Login</button>
    pattern = re.compile(
    r'(<button[^>]*onclick\s*=\s*")'
    r'window\.location\.href=[\'"][^\'"]+[\'"];?'
    r'(".*?>\s*Login\s*</button>)',
    re.IGNORECASE
)


    replacement = r'\1window.location.href=\'{}\''.format(args.new_url) + r'\2'
    updated, count = pattern.subn(replacement, original)

    if count:
        file_path.write_text(updated, encoding="utf-8")
        print(f"✅ Updated {count} Login button URL(s) in '{file_path}'.")
    else:
        print(f"⚠️  No Login button patterns found in '{file_path}'.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
