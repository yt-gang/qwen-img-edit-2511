[![Runpod](https://api.runpod.io/badge/ZeroClue/qwen-img-edit-2511)](https://console.runpod.io/hub/ZeroClue/qwen-img-edit-2511) [![Sign Up](https://img.shields.io/badge/RunPod-Sign%20Up-blue)](https://runpod.io?ref=lnnwdl3q)

# Qwen Image Edit 2511

## Catline production contract

This fork's production path requires a pre-seeded RunPod Network Volume. Startup validates the pinned
`models.json` manifest and its full-verification marker and never downloads weights. Seed the shared
volume once with `python /opt/catline/seed_models.py` from a temporary Pod.

Catline sends one to three private R2 reference URLs. Only HTTPS hosts listed in
`R2_ALLOWED_DOWNLOAD_HOSTS` are accepted. References are normalized to the `1080x1920` canvas and
removed from the ComfyUI input directory after the job. The result is a single lossless WebP uploaded
directly to the provided presigned PUT; the response contains only `asset` metadata and timings.

🚀 **AI image editing with enhanced consistency** - Edit images using text instructions with the Qwen-Image-Edit-2511 model. Supports single-image and multi-image editing with Lightning 4-step acceleration.

## 🎯 **Key Capabilities**
- **Single-Image Editing**: Modify any image with text instructions
- **Multi-Image Editing**: Combine elements from multiple source images (person+scene, product+scene)
- **Enhanced Consistency**: Improved person, product, and text identity preservation
- **Text Editing**: Modify text content, fonts, colors, and materials in images
- **ControlNet Support**: Native depth, edge, and keypoint conditioning

## ⚡ Key Features

- **Lightning Generation**: Fast editing with 4-step or 8-step Lightning LoRA optimization
- **Flexible Steps**: Any positive step count — auto-selects 4-step LoRA (≤4), 8-step LoRA (5-8), or base model (>8)
- **Multi-Image Input**: Up to 3 reference images for complex compositions
- **Qwen Vision-Language**: Advanced understanding of edit instructions in Chinese/English
- **Production Ready**: Optimized for RunPod Hub deployment

## 🎯 Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Edit Time (4-step) | 2-5 seconds | 4-step Lightning LoRA mode |
| Edit Time (8-step) | 4-8 seconds | 8-step Lightning LoRA mode |
| Edit Time (40-step) | 15-30 seconds | Full quality mode (no LoRA) |
| Resolution | Source-dependent | Matches input image dimensions |
| Memory Usage | ~16GB GPU | Efficient resource utilization |
| Steps | 4/8 (Lightning) / any (full) | Auto-selects LoRA via API |

## 🏗️ Architecture

### Model Components
- **Base Model**: Qwen Image Edit 2511 (diffusion model, fp8mixed)
- **Text Encoder**: Qwen 2.5 VL 7B (multilingual understanding)
- **VAE**: Qwen Image VAE (efficient encoding/decoding)
- **LoRA**: Qwen-Image-Edit-2511-Lightning-4steps-V1.0 and Qwen-Image-Edit-2511-Lightning-8steps-V1.0 (speed optimization)

### Pipeline Flow
```
Source Image(s) + Edit Instruction → Qwen 2.5 VL Encoder → Qwen Image Edit 2511 + Lightning LoRA → Sampling (4/8/N steps) → VAE Decode → Edited Image
```

## 🚀 Quick Start

### RunPod Serverless (Recommended)
Deploy as a serverless API endpoint for scalable, pay-per-use editing:

1. Visit the Qwen Image Edit 2511 listing on RunPod Hub
2. Select GPU (A10G minimum, A40/A100 recommended)
3. Launch and start editing images instantly

```bash
# Clone the repository
git clone https://github.com/ZeroClue/qwen-img-edit-2511.git
cd qwen-img-edit-2511
```

### 🎁 Get Free Credits

**Sign up with our referral link** to get a credit bonus between $5-$500:
- **[Create Free RunPod Account](https://runpod.io?ref=lnnwdl3q)**
- Bonus credits are automatically applied to your account

## 📡 API Usage

### Simplified Edit API (Recommended)
```python
import requests
import json
import base64

url = "https://api.runpod.ai/v2/{endpoint_id}/runsync"
headers = {"Authorization": "Bearer YOUR_API_KEY"}

# Read and encode source image
with open("source.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "input": {
        "prompt": "Change the background to a sunset beach while keeping the person",
        "image": image_b64,
        "seed": 42,
        "steps": 4,
        "negative_prompt": ""
    }
}

response = requests.post(url, json=payload, headers=headers)
result = response.json()

# Decode edited image
image_data = base64.b64decode(result["images"][0]["data"])
with open("edited.png", "wb") as f:
    f.write(image_data)
```

### Multi-Image Edit (Person + Scene)
```python
payload = {
    "input": {
        "prompt": "Place the person from image 1 on the beach from image 2",
        "image": person_image_b64,
        "reference_image": beach_image_b64,
        "steps": 4
    }
}
```

### Simplified API Parameters

| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `prompt` | ✅ | — | Edit instruction text |
| `image` | ✅ | — | Base64-encoded source image |
| `reference_image` | ❌ | reuses source | Second image for multi-image edits |
| `seed` | ❌ | random | Reproducibility seed |
| `steps` | ❌ | 4 | Inference steps (any positive int). Auto-selects LoRA: ≤4→4-step, 5-8→8-step, >8→base |
| `negative_prompt` | ❌ | "" | What to avoid in editing |
| `lora` | ❌ | auto | Override LoRA: `"4step"`, `"8step"`, `"none"`. Auto-detect from steps: ≤4→4-step, 5-8→8-step, >8→base |
| `cfg` | ❌ | auto | CFG scale (auto: 1.0 for Lightning, 4.0 for base) |
| `shift` | ❌ | 3.1 | ModelSamplingAuraFlow shift — increase if blurry/dark, decrease for more detail |
| `sampler` | ❌ | `"euler"` | KSampler sampler name (e.g. `euler`, `res_multistep`) |
| `scheduler` | ❌ | `"simple"` | KSampler scheduler name |

### Raw Workflow Mode
For advanced users, pass a complete ComfyUI API-format workflow:
```python
payload = {
    "input": {
        "workflow": { ... },  # Full ComfyUI node graph
        "images": [           # Upload source images
            {"name": "source.png", "image": "base64_data"}
        ]
    }
}
```

## 🎨 Use Cases

### Single-Image Editing
- **Background replacement**: "Change the background to a mountain landscape"
- **Style transfer**: "Convert this photo to watercolor painting style"
- **Object modification**: "Change the car color to red"
- **Text editing**: "Replace the sign text with 'Open 24/7'"

### Multi-Image Editing
- **Person + Scene**: "Place the person in image 1 in the scene from image 2"
- **Product + Scene**: "Show this product in a modern living room setting"
- **Style Reference**: "Apply the artistic style of image 2 to image 1"

### Visual Consistency (Carousel/Series)
1. Generate slide 1 with Qwen Image 2512
2. Edit slide 1 → slide 2 with Qwen Image Edit 2511
3. Chain edits for slides 3, 4, 5...
4. The edit model preserves visual DNA while changing content

## 💰 Pricing & Deployment Costs

### RunPod Serverless
- **Per-Edit (4-step)**: ~$0.003-$0.006 per edit
- **Per-Edit (8-step)**: ~$0.005-$0.010 per edit
- **Per-Edit (40-step)**: ~$0.02-$0.04 per edit
- **Pay-per-second**: Only pay for actual editing time
- **Auto-scaling**: Zero cost when not in use

### Cost Comparison (per edit)
| Steps | Time/Edit | Cost/Edit | Monthly (1000 edits) |
|-------|-----------|-----------|----------------------|
| **4 (Lightning)** | 2-5s | $0.004 | $4.00 |
| **8 (Lightning)** | 4-8s | $0.008 | $8.00 |
| **40 (Full)** | 15-30s | $0.03 | $30.00 |

## 🔧 Configuration

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `COMFY_ORG_API_KEY` | Comfy.org API key for API Nodes |
| `BUCKET_ENDPOINT_URL` | S3 endpoint for image uploads |
| `HF_TOKEN` | HuggingFace token for faster model downloads |
| `COMFY_LOG_LEVEL` | ComfyUI verbosity (default: DEBUG) |
| `REFRESH_WORKER` | Restart worker after each job |

### Resource Requirements
- **GPU**: A10G (minimum) / A40 (recommended) / A100 / RTX 5090 (optimal)
- **GPU Memory**: 16GB+ required
- **Container Disk**: 50GB recommended (models download at runtime, ~29GB total)

## 📁 File Structure

```
qwen_img_edit_2511/
├── .runpod/               # RunPod Hub configuration
│   ├── Dockerfile         # Hub build configuration
│   └── hub.json           # Hub metadata and specs
├── src/
│   ├── start.sh           # Container entrypoint
│   ├── check-models.sh    # Model download/validation
│   └── extra_model_paths.yaml  # Network volume mapping
├── scripts/
│   ├── comfy-node-install.sh
│   └── comfy-manager-set-mode.sh
├── handler.py             # RunPod serverless handler
├── Dockerfile             # Container build configuration
├── docker-bake.hcl        # Docker Bake build targets
├── example-request.json   # Simplified edit API example
├── simplified-request.json # Multi-image edit example
├── test_input.json        # Test workflow
└── requirements.txt       # Python dependencies
```

## 🆚 Companion Projects

| Project | Purpose | Repo |
|---------|---------|------|
| **Qwen Image 8-Step** | Text-to-image generation (original) | [qwen-img-8step](https://github.com/ZeroClue/qwen-img-8step) |
| **Qwen Image 2512** | Text-to-image generation (newer model, 4-step) | [qwen-img-2512](https://github.com/ZeroClue/qwen-img-2512) |
| **Qwen Image Edit 2511** | Image editing with instructions | This repo |

## 📄 License

- **Models**: Apache-2.0 compatible licenses
- **Commercial Use**: ✅ Allowed with attribution

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/ZeroClue/qwen-img-edit-2511/issues)
- **Community**: Join the RunPod Discord for community support
