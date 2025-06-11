#!/usr/bin/env bash
#
# update-login-button.sh
#
# Usage: ./update-login-button.sh <LoginUrl> [GlobalJsPath]
#
# Takes a login URL (e.g., from configure-login.py output) and the path to
# global.js. It finds the HTML login button (looking for ">Login</button>")
# and updates its onclick attribute to redirect to the provided LoginUrl.
#
set -euo pipefail

# Check for the correct number of arguments
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: $0 <LoginUrl> [GlobalJsPath]"
  echo "  <LoginUrl>     : The URL to redirect to on login button click (e.g., from configure-login.py output)."
  echo "  [GlobalJsPath] : Optional. The relative path to global.js. Defaults to ../frontend/script/global.js."
  exit 1
fi

LOGIN_URL="window.location.href='$1'"
GLOBAL_JS_PATH="${2:-frontend/script/global.js}" # Default to ../frontend/script/global.js if not provided

# Resolve the absolute path for global.js
GLOBAL_JS="$(pwd)/${GLOBAL_JS_PATH}"

# Check if global.js exists
if [ ! -f "$GLOBAL_JS" ]; then
  echo "❌ global.js not found at '$GLOBAL_JS'"
  echo "Please ensure the path is correct or provide the full path as the second argument."
  exit 1
fi

echo "Updating login button in: ${GLOBAL_JS}" >&2
echo "New login URL: ${LOGIN_URL}" >&2

# Use sed to find the login button and replace its onclick attribute.
# We are looking for a button that contains ">Login</button>" and
# has an onclick attribute. The regex captures the parts before and after
# the onclick, allowing us to insert the new URL.
# The 'g' flag ensures all occurrences on the line are replaced, though usually there's only one login button.
# The 'i.bak' creates a backup file.
# The `printf '%s\n'` command is used to ensure the sed command is compatible across different systems.
sed -i.bak -E "s|(.*<button[^>]*onclick=\")[^\"]*(\"[^>]*>Login</button>.*)|\1${LOGIN_URL}\2|" "$GLOBAL_JS"

if [ $? -eq 0 ]; then
  echo "✅ Login button onclick URL updated successfully in '$GLOBAL_JS'" >&2
  # Remove the backup file
  rm -f "${GLOBAL_JS}.bak"
else
  echo "❌ Failed to update login button onclick URL in '$GLOBAL_JS'" >&2
  echo "Please check the file content and permissions."
  exit 1
fi
