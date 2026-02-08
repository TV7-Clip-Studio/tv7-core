#!/bin/bash
# Script to run the TV7 Media MCP
# Usage: ./run-mcp.sh

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/../"

cargo run --quiet --bin tv7-media-mcp
