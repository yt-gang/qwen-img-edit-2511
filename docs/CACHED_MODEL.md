# RunPod cached-model deployment

This deployment keeps the Qwen Image Edit 2511 weights in RunPod's host-local
Hugging Face Model Cache. The normal Network Volume remains the rollback path.

## 1. Publish the private repository

From a temporary Pod with the current model volume mounted at `/workspace`:

```bash
git clone https://github.com/yt-gang/qwen-img-edit-2511.git
cd qwen-img-edit-2511

export HF_TOKEN='YOUR_WRITE_TOKEN'
export HF_CACHE_REPO='YOUR_HF_NAMESPACE/qwen-image-edit-2511-runpod-cache'
SOURCE_MODEL_ROOT=/workspace/models bash scripts/publish-cached-model.sh
```

Keep the repository private. Do not commit or paste `HF_TOKEN` into logs. The
script publishes only the five files pinned by `models.json`, plus Apache-2.0
license and attribution files.

## 2. Configure RunPod

1. Deploy the current `main` Docker build.
2. Select the private Hugging Face repository as the endpoint **Model** and add
   a Hugging Face read token.
3. Set `QWEN_CACHED_MODEL_REPO=YOUR_HF_NAMESPACE/qwen-image-edit-2511-runpod-cache`.
4. Set `QWEN_REQUIRE_CACHED_MODEL=true` for fail-closed startup.
5. Keep the existing 4090/5090 GPU selection and enable FlashBoot after the
   first successful test.

The worker reads snapshots from:

```text
/runpod-volume/huggingface-cache/hub/models--ORG--NAME/snapshots/REVISION/
```

## 3. Verify

Worker logs must contain `using RunPod cached model snapshot`. Submit:

```json
{"input":{"health_check":true}}
```

The response must contain `"ready": true`. Then run one cold reference edit and
two hot edits through `serverless-generation-api`; record delay/execution time
and visually inspect all outputs for noise.

## Rollback

Remove `QWEN_CACHED_MODEL_REPO`, `QWEN_REQUIRE_CACHED_MODEL` and the endpoint
Model selection, attach the existing Network Volume, and redeploy.
