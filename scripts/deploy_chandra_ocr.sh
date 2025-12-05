#!/bin/bash
# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

# Deploy Chandra OCR to Modal and update .env with the inference URL
#
# Usage:
#   ./scripts/deploy_chandra_ocr.sh
#   ENV_PATH=/path/to/.env ./scripts/deploy_chandra_ocr.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
ENV_PATH="${ENV_PATH:-$PROJECT_ROOT/annotator/.env}"
ENV_VAR_NAME="OCR_INFERENCE_URL"

echo "Deploying Chandra OCR to Modal..."
echo "ENV path: $ENV_PATH"

# Deploy the app and capture output
DEPLOY_OUTPUT=$(python3 -m modal deploy "$SCRIPT_DIR/chandra_ocr_modal.py" 2>&1)
DEPLOY_EXIT_CODE=$?

echo "$DEPLOY_OUTPUT"

if [ $DEPLOY_EXIT_CODE -ne 0 ]; then
    echo "Error: Deployment failed with exit code $DEPLOY_EXIT_CODE"
    exit 1
fi

# Extract URL from the deployment output
# Modal outputs URLs in format: https://username--app-name-function-name.modal.run
URL=$(echo "$DEPLOY_OUTPUT" | grep -oE 'https://[a-zA-Z0-9_-]+--chandra-ocr-inference[a-zA-Z0-9_-]*\.modal\.run[^\s]*' | head -1)

if [ -z "$URL" ]; then
    # Try alternative pattern
    URL=$(echo "$DEPLOY_OUTPUT" | grep -oE 'https://[^\s]+\.modal\.run[^\s]*' | grep -i ocr | head -1)
fi

if [ -z "$URL" ]; then
    echo "Warning: Could not extract URL from deployment output"
    echo "You may need to manually check the Modal dashboard for the endpoint URL"
    exit 0
fi

echo ""
echo "Found endpoint URL: $URL"

# Update .env file
mkdir -p "$(dirname "$ENV_PATH")"

if [ -f "$ENV_PATH" ]; then
    # Check if variable exists
    if grep -q "^${ENV_VAR_NAME}=" "$ENV_PATH"; then
        # Update existing variable (macOS compatible sed)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${ENV_VAR_NAME}=.*|${ENV_VAR_NAME}=${URL}|" "$ENV_PATH"
        else
            sed -i "s|^${ENV_VAR_NAME}=.*|${ENV_VAR_NAME}=${URL}|" "$ENV_PATH"
        fi
        echo "Updated ${ENV_VAR_NAME} in $ENV_PATH"
    else
        # Append variable
        echo "" >> "$ENV_PATH"
        echo "${ENV_VAR_NAME}=${URL}" >> "$ENV_PATH"
        echo "Added ${ENV_VAR_NAME} to $ENV_PATH"
    fi
else
    # Create new .env file
    echo "${ENV_VAR_NAME}=${URL}" > "$ENV_PATH"
    echo "Created $ENV_PATH with ${ENV_VAR_NAME}"
fi

echo ""
echo "Done! Endpoint URL written to $ENV_PATH"
echo ""
echo "To test the endpoint:"
echo "  curl -X POST $URL \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"image_base64\": \"<base64_image>\"}'"
