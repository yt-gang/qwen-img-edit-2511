#!/usr/bin/env bash

echo "worker-comfyui: Build version ${BUILD_VERSION:-unknown}"

# Resolve the host-local RunPod Model Cache first, with Network Volume fallback.
if [ -d /runpod-volume ]; then
    export QWEN_MODEL_FALLBACK="${QWEN_MODEL_FALLBACK:-/runpod-volume/models}"
else
    export QWEN_MODEL_FALLBACK="${QWEN_MODEL_FALLBACK:-/comfyui/models}"
fi
export COMFY_MODEL_BASE
COMFY_MODEL_BASE=$(python /opt/catline/resolve_model_base.py --manifest /opt/catline/models.json) || exit 1

if [ "${COMFY_MODEL_BASE}" != "/comfyui/models" ]; then
    if [[ "${COMFY_MODEL_BASE}" == */huggingface-cache/* ]]; then
        echo "worker-comfyui: using RunPod cached model snapshot ${COMFY_MODEL_BASE}"
    else
        echo "worker-comfyui: using Network Volume models ${COMFY_MODEL_BASE}"
    fi
    for dir in diffusion_models clip vae loras; do
        test -d "${COMFY_MODEL_BASE}/$dir" || { echo "worker-comfyui: missing model directory $dir" >&2; exit 1; }
        # The base image pre-creates these directories. `ln -sfnT` cannot
        # replace a real directory, so remove only the ephemeral container
        # path before linking it to persistent storage.
        rm -rf -- "/comfyui/models/$dir"
        ln -s "${COMFY_MODEL_BASE}/$dir" "/comfyui/models/$dir" || exit 1
        test -L "/comfyui/models/$dir" || exit 1
    done
else
    echo "worker-comfyui: using container-local model storage"
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
    if [[ "${COMFY_MODEL_BASE}" == */huggingface-cache/* ]]; then
        MODEL_READY_MARKER=/tmp/catline-cached-model.verified
        printf 'cached-model\n' > "${MODEL_READY_MARKER}"
    else
        echo "worker-comfyui: Validating immutable model manifest..."
        MODEL_READY_MARKER=$(python /opt/catline/verify_models.py \
            --manifest /opt/catline/models.json --base "${COMFY_MODEL_BASE}")
    fi
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
