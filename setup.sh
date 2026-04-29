#!/bin/bash
set -e

echo "=== Jira Automation Setup ==="

# Detect Python 3.10+ (needed for modern type hints)
PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        version=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

# Fallback: check known macOS framework path
if [ -z "$PYTHON" ] && [ -x "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" ]; then
    PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
fi

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.10+ is required. Found none."
    echo "Install from https://www.python.org/downloads/"
    exit 1
fi

echo "Using: $PYTHON ($($PYTHON --version))"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv venv
fi

# Activate venv
source venv/bin/activate

pip install -r requirements.txt --quiet

if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from template."
    echo "Edit it with your credentials:"
    echo "  1. Get your API token at: https://id.atlassian.com/manage-profile/security/api-tokens"
    echo "  2. Set JIRA_USER_EMAIL and JIRA_API_TOKEN in .env"
    echo "  3. Adjust JIRA_ACTIVE_PROJECTS to your projects"
else
    echo ".env already exists, skipping."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "Then test with:"
echo "  python -m tools.cli.standup"
