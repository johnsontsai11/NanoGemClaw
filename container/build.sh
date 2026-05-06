#!/bin/bash
# Build the NanoGemClaw agent container image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="nanogemclaw-agent"
TAG="${1:-latest}"

echo "Building NanoGemClaw agent container image..."
echo "Image: ${IMAGE_NAME}:${TAG}"

# Build with Apple Container (or Docker)
BUILD_SUCCESS=false

# Allow forcing a runtime via RUNTIME=docker or RUNTIME=container
if [[ "${RUNTIME}" == "container" ]]; then
    echo "Forcing build with Apple Container..."
    container build -t "${IMAGE_NAME}:${TAG}" .
    BUILD_SUCCESS=true
elif [[ "${RUNTIME}" == "docker" ]]; then
    echo "Forcing build with Docker..."
    docker build -t "${IMAGE_NAME}:${TAG}" .
    BUILD_SUCCESS=true
else
    # Auto-detect and fallback
    if command -v container &> /dev/null; then
        echo "Attempting build with Apple Container..."
        # We don't use 'set -e' for this specific command to allow fallback
        if container build -t "${IMAGE_NAME}:${TAG}" . ; then
            BUILD_SUCCESS=true
        else
            echo "Apple Container build failed. Falling back..."
        fi
    fi

    if [ "$BUILD_SUCCESS" = false ] && command -v docker &> /dev/null; then
        echo "Using Docker (OrbStack)..."
        docker build -t "${IMAGE_NAME}:${TAG}" .
        BUILD_SUCCESS=true
    fi
fi

if [ "$BUILD_SUCCESS" = false ]; then
    echo "Error: Build failed or no container runtime found"
    exit 1
fi

echo ""
echo "Build complete!"
echo "Image: ${IMAGE_NAME}:${TAG}"
echo ""
echo "Test with:"
echo "  echo '{\"prompt\":\"What is 2+2?\",\"groupFolder\":\"test\",\"chatJid\":\"test@g.us\",\"isMain\":false}' | container run -i ${IMAGE_NAME}:${TAG}"
