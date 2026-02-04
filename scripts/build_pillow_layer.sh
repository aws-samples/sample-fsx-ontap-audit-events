#!/bin/bash
# Build Lambda layer for Pillow

set -e

LAYER_DIR="layers/pillow"
BUILD_DIR="$LAYER_DIR/python"

echo "Building Pillow layer..."

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Install dependencies using uv
uv pip install -r "$LAYER_DIR/requirements.txt" --target "$BUILD_DIR" --python-platform x86_64-manylinux2014 --python-version 3.12

echo "Pillow layer built successfully at $BUILD_DIR"
