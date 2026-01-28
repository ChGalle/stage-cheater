#!/bin/bash
#
# Stage-Cheater Start Script
#
# For Raspberry Pi with Raspbian Lite (no X11/desktop)
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# SDL settings for framebuffer/KMS mode (no X11 needed)
export SDL_VIDEODRIVER=kmsdrm
export SDL_RENDER_DRIVER=opengles2

# Activate virtual environment if it exists
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Run Stage-Cheater
exec stage-cheater "$@"
