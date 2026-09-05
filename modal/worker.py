"""Modal GPU seams for Video Forge.

This file intentionally exposes contracts, not a fake finished model pipeline.
Training/image backends are added after model and dataset licenses are pinned.
"""

import modal

app = modal.App("video-forge-gpu")
model_volume = modal.Volume.from_name("video-forge-models", create_if_missing=True)

image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "accelerate",
    "datasets",
    "diffusers",
    "peft",
    "safetensors",
    "transformers",
    "trl",
)


@app.function(image=image, gpu="L40S", timeout=60 * 60, volumes={"/models": model_volume})
def worker_info() -> dict[str, str]:
    return {
        "status": "ready",
        "purpose": "image generation / LoRA-QLoRA training / export worker seam",
        "model_volume": "/models",
    }
