#!/usr/bin/env bash
# Publish the exact Qwen Image Edit 2511 worker model set as a private HF repository.
set -euo pipefail

SOURCE_MODEL_ROOT="${SOURCE_MODEL_ROOT:-/workspace/models}"
STAGING_ROOT="${STAGING_ROOT:-/workspace/qwen-image-edit-2511-runpod-cache}"
HF_CACHE_REPO="${HF_CACHE_REPO:?set HF_CACHE_REPO to your private org/name repository}"
: "${HF_TOKEN:?set HF_TOKEN to a Hugging Face write token}"

FILES=(
  "diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors"
  "clip/qwen_2.5_vl_7b_fp8_scaled.safetensors"
  "vae/qwen_image_vae.safetensors"
  "loras/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
  "loras/Qwen-Image-Edit-2511-Lightning-8steps-V1.0-bf16.safetensors"
)

mkdir -p "${STAGING_ROOT}"
for relative in "${FILES[@]}"; do
  source_path="${SOURCE_MODEL_ROOT}/${relative}"
  target_path="${STAGING_ROOT}/${relative}"
  if [ ! -s "${source_path}" ]; then
    echo "missing required source file: ${source_path}" >&2
    exit 1
  fi
  mkdir -p "$(dirname "${target_path}")"
  if ! ln -f "${source_path}" "${target_path}" 2>/dev/null; then
    cp --reflink=auto "${source_path}" "${target_path}"
  fi
done

curl -fsSL https://www.apache.org/licenses/LICENSE-2.0.txt -o "${STAGING_ROOT}/LICENSE"
cat > "${STAGING_ROOT}/NOTICE" <<'EOF'
This private cache republishes selected Apache-2.0 model files from:
- Comfy-Org/Qwen-Image-Edit_ComfyUI
- Comfy-Org/Qwen-Image_ComfyUI
- lightx2v/Qwen-Image-Edit-2511-Lightning
See models.json in https://github.com/yt-gang/qwen-img-edit-2511 for pinned revisions and checksums.
EOF
cat > "${STAGING_ROOT}/README.md" <<'EOF'
---
license: apache-2.0
base_model:
- Qwen/Qwen-Image-Edit-2511
private: true
---

# Qwen Image Edit 2511 RunPod cache

Private, minimal cached-model package for `yt-gang/qwen-img-edit-2511`. The
worker's `models.json` is the authoritative list of pinned files, sizes and
SHA-256 values.
EOF

python3 -m pip install --no-cache-dir -U --break-system-packages "huggingface_hub[hf_transfer]" hf_transfer >/dev/null
export HF_HUB_ENABLE_HF_TRANSFER=1
hf repo create "${HF_CACHE_REPO}" --repo-type model --private --exist-ok
hf upload-large-folder "${HF_CACHE_REPO}" "${STAGING_ROOT}" --repo-type model
echo "Published private cached-model repository: https://huggingface.co/${HF_CACHE_REPO}"
