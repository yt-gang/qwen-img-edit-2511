#!/usr/bin/env bash

echo "worker-comfyui: Build version ${BUILD_VERSION:-unknown}"

# SYMLINK MODEL DIRS TO NETWORK VOLUME IF PRESENT
if [ -d /runpod-volume ]; then
    echo "worker-comfyui: Network volume detected, symlinking model dirs to /runpod-volume/models"
    for dir in diffusion_models clip vae loras controlnet; do
        mkdir -p "/runpod-volume/models/$dir"
        # -T replaces ComfyUI's pre-created directory instead of nesting the
        # symlink inside it (for example, models/vae/vae).
        ln -sfnT "/runpod-volume/models/$dir" "/comfyui/models/$dir"
    done
else
    echo "worker-comfyui: No network volume detected, using local model storage"
fi

# GitHub deployments run their container smoke test without attaching endpoint
# storage. Permit that explicit test mode to validate ComfyUI and the handler,
# while keeping the Network Volume mandatory for every production worker.
if [ "${CATLINE_BUILD_TEST:-false}" = "true" ]; then
    echo "worker-comfyui: RunPod build-test mode; skipping model-volume validation"
    MODEL_READY_MARKER=/tmp/catline-build-test.verified
    printf 'build-test\n' > "${MODEL_READY_MARKER}"
elif [ ! -d /runpod-volume ]; then
    echo "worker-comfyui: /runpod-volume is required in production" >&2
    exit 1
else
    echo "worker-comfyui: Validating immutable model manifest..."
    MODEL_READY_MARKER=$(python /opt/catline/verify_models.py \
        --manifest /opt/catline/models.json --base /runpod-volume/models)
fi
export MODEL_READY_MARKER

# Use libtcmalloc for better memory management
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"

# Ensure ComfyUI-Manager runs in offline network mode inside the container
comfy-manager-set-mode offline || echo "worker-comfyui - Could not set ComfyUI-Manager network_mode" >&2

echo "worker-comfyui: Starting ComfyUI"

# Allow operators to tweak verbosity; default is DEBUG.
: "${COMFY_LOG_LEVEL:=DEBUG}"

# Serve the API and don't shutdown the container
if [ "$SERVE_API_LOCALLY" == "true" ]; then
    python -u /comfyui/main.py --disable-auto-launch --disable-metadata --listen --verbose "${COMFY_LOG_LEVEL}" --log-stdout &
    echo $! > /tmp/comfyui.pid

    echo "worker-comfyui: Starting RunPod Handler"
    python -u /handler.py --rp_serve_api --rp_api_host=0.0.0.0
else
    python -u /comfyui/main.py --disable-auto-launch --disable-metadata --verbose "${COMFY_LOG_LEVEL}" --log-stdout &
    echo $! > /tmp/comfyui.pid

    echo "worker-comfyui: Starting RunPod Handler"
    python -u /handler.py
fi
