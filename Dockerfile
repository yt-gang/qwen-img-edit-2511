# Build argument for base image selection
ARG BASE_IMAGE=nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04

# Stage 1: Base image with all dependencies
FROM ${BASE_IMAGE} AS base

ARG COMFYUI_VERSION=v0.3.76
ARG CUDA_VERSION_FOR_COMFY
ARG COMFY_CUSTOM_NODES=
ARG BUILD_VERSION=dev

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_PREFER_BINARY=1
ENV PYTHONUNBUFFERED=1
ENV CMAKE_BUILD_PARALLEL_LEVEL=8

# Install Python 3.12 (native in Ubuntu 24.04), git, and runtime libs
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    git \
    wget \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && ln -sf /usr/bin/python3.12 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

# Clean up to reduce image size
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install uv and create venv
RUN wget -qO- https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && ln -s /root/.local/bin/uvx /usr/local/bin/uvx \
    && uv venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"

# Install comfy-cli + dependencies
RUN uv pip install comfy-cli==1.20.0 pip==25.2 setuptools==80.9.0 wheel==0.45.1

# Install ComfyUI
RUN if [ -n "${CUDA_VERSION_FOR_COMFY}" ]; then \
      /usr/bin/yes | comfy --workspace /comfyui install --version "${COMFYUI_VERSION}" --cuda-version "${CUDA_VERSION_FOR_COMFY}" --nvidia --fast-deps; \
    else \
      /usr/bin/yes | comfy --workspace /comfyui install --version "${COMFYUI_VERSION}" --nvidia --fast-deps; \
    fi

# Install ComfyUI runtime requirements
RUN uv pip install -r /comfyui/requirements.txt

# Force-install PyTorch cu128 for Blackwell (RTX 5090) and backwards compatibility
RUN uv pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Support for the network volume
ADD src/extra_model_paths.yaml /comfyui/

# Install pinned Python runtime dependencies for the handler
COPY requirements.txt /tmp/worker-requirements.txt
RUN uv pip install -r /tmp/worker-requirements.txt

# Add custom node install script
COPY scripts/comfy-node-install.sh /usr/local/bin/comfy-node-install
RUN chmod +x /usr/local/bin/comfy-node-install

# Prevent pip from asking for confirmation during custom node installs
ENV PIP_NO_INPUT=1

# Install custom nodes
RUN if [ -n "${COMFY_CUSTOM_NODES}" ]; then \
      echo "Installing custom ComfyUI nodes: ${COMFY_CUSTOM_NODES}" && \
      /usr/local/bin/comfy-node-install ${COMFY_CUSTOM_NODES} || \
      (echo "Failed to install custom nodes" && exit 1); \
    else \
      echo "No custom ComfyUI nodes to install"; \
    fi

WORKDIR /comfyui

# Copy helper script to switch Manager network mode at container start
COPY scripts/comfy-manager-set-mode.sh /usr/local/bin/comfy-manager-set-mode
RUN chmod +x /usr/local/bin/comfy-manager-set-mode

COPY models.json scripts/verify_models.py scripts/seed_models.py /opt/catline/
RUN chmod +x /opt/catline/verify_models.py /opt/catline/seed_models.py

# Go back to root for handler files
WORKDIR /

ADD src/start.sh handler.py catline_worker.py test_input.json ./
RUN chmod +x /start.sh

# Enable high-performance downloads from HuggingFace (hf_xet chunk-based parallel transfers).
ENV HF_XET_HIGH_PERFORMANCE=1

# Stamp build version for runtime identification
ENV BUILD_VERSION=${BUILD_VERSION}

CMD ["/start.sh"]

FROM base AS baked-models
ARG BAKED_MODEL_BASE=/comfyui/models
RUN python /opt/catline/seed_models.py --base "${BAKED_MODEL_BASE}"

# Default image: models live on a pre-seeded Network Volume.
FROM base AS final
