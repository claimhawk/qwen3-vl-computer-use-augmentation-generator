#!/usr/bin/env python3
# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""
Chandra OCR Inference on Modal

Deploys Chandra 7B OCR model on Modal for text extraction from screenshots.
Uses centralized configuration from sdk.modal_compat with fallback values
for remote execution.

Usage:
    # Run OCR on a single image
    modal run scripts/chandra_ocr_modal.py --image path/to/screenshot.png

    # Run OCR with JSON output format
    modal run scripts/chandra_ocr_modal.py --image path/to/screenshot.png \
        --output-format json

    # Run OCR and save to file
    modal run scripts/chandra_ocr_modal.py --image path/to/screenshot.png \
        --output extracted_data.md

    # Run OCR on multiple images (batch mode)
    modal run scripts/chandra_ocr_modal.py --image-dir path/to/images/ \
        --output-dir output/

    # Deploy as a persistent endpoint (writes URL to annotator .env)
    modal deploy scripts/chandra_ocr_modal.py

    # Deploy and specify custom .env path
    ENV_PATH=/path/to/.env modal deploy scripts/chandra_ocr_modal.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import modal

# =============================================================================
# CONFIGURATION
# =============================================================================
# Use centralized config with fallback for Modal remote execution

try:
    from sdk.modal_compat import get_ocr_model

    CHANDRA_MODEL = get_ocr_model()
except ImportError:
    CHANDRA_MODEL = "datalab-to/chandra"

# Default .env path for annotator project
DEFAULT_ENV_PATH = Path(__file__).parent.parent.parent.parent.parent / "annotator" / ".env"
ENV_VAR_NAME = "OCR_INFERENCE_URL"


# =============================================================================
# MODAL APP SETUP
# =============================================================================

app = modal.App("chandra-ocr-inference")

# Docker image with Chandra OCR dependencies
image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.1.0-devel-ubuntu22.04",
        add_python="3.11",
    )
    .pip_install(
        "torch>=2.0.0",
        "transformers>=4.45.0",
        "accelerate>=0.27.0",
        "Pillow>=10.0.0",
        "chandra-ocr",
        "fastapi",
    )
)


# =============================================================================
# INFERENCE FUNCTIONS
# =============================================================================


@app.function(
    image=image,
    gpu="A100:1",
    timeout=600,
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
def run_ocr(
    image_base64: str,
    prompt_type: str = "ocr_layout",
    output_format: str = "markdown",
) -> dict:
    """
    Run Chandra OCR on a single image.

    Args:
        image_base64: Base64-encoded image data
        prompt_type: Chandra prompt type:
            - 'ocr_layout': Preserve layout structure (default)
            - 'ocr_with_region': Include region coordinates
            - 'ocr': Simple text extraction
        output_format: Output format ('markdown', 'json', 'html')

    Returns:
        dict with keys:
            - text: Extracted text in requested format
            - format: Output format used
            - prompt_type: Prompt type used
            - image_size: (width, height) tuple
    """
    import base64
    from io import BytesIO

    from PIL import Image

    print(f"\n{'='*80}")
    print("Chandra OCR Inference")
    print(f"Model: {CHANDRA_MODEL}")
    print(f"{'='*80}\n")

    # Decode image
    print("Decoding image...")
    image_data = base64.b64decode(image_base64)
    pil_image = Image.open(BytesIO(image_data)).convert("RGB")
    print(f"  Image size: {pil_image.size}")

    # Load Chandra model
    print("\nLoading Chandra model...")
    from chandra.model import InferenceManager
    from chandra.model.schema import BatchInputItem

    manager = InferenceManager(method="hf")
    print("  Model loaded successfully")

    # Run OCR
    print(f"\nRunning OCR (prompt_type={prompt_type})...")
    batch = [BatchInputItem(image=pil_image, prompt_type=prompt_type)]
    results = manager.generate(batch)
    result = results[0]
    print("  OCR complete")

    # Extract output based on format
    output: dict = {
        "prompt_type": prompt_type,
        "image_size": pil_image.size,
    }

    if output_format == "markdown":
        output["text"] = result.markdown
        output["format"] = "markdown"
    elif output_format == "json":
        output["text"] = result.json if hasattr(result, "json") else result.markdown
        output["format"] = "json"
    elif output_format == "html":
        output["text"] = result.html if hasattr(result, "html") else result.markdown
        output["format"] = "html"
    else:
        output["text"] = result.markdown
        output["format"] = "markdown"

    # Preview output
    print(f"\n{'='*80}")
    print("Extracted Text Preview:")
    print(f"{'='*80}\n")
    preview_len = 2000
    print(output["text"][:preview_len])
    if len(output["text"]) > preview_len:
        print(f"\n... ({len(output['text']) - preview_len} more characters)")

    return output


@app.function(
    image=image,
    gpu="A100:1",
    timeout=1800,
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
def batch_ocr(
    images_base64: list[str],
    prompt_type: str = "ocr_layout",
    output_format: str = "markdown",
) -> list[dict]:
    """
    Run Chandra OCR on multiple images in batch.

    More efficient than calling run_ocr multiple times as the model
    is loaded once and reused.

    Args:
        images_base64: List of base64-encoded images
        prompt_type: Chandra prompt type
        output_format: Output format for all images

    Returns:
        List of dicts with extracted text and metadata
    """
    import base64
    from io import BytesIO

    from PIL import Image

    print(f"\n{'='*80}")
    print(f"Chandra OCR Batch Processing ({len(images_base64)} images)")
    print(f"Model: {CHANDRA_MODEL}")
    print(f"{'='*80}\n")

    # Decode all images
    print("Decoding images...")
    pil_images = []
    for i, img_b64 in enumerate(images_base64):
        image_data = base64.b64decode(img_b64)
        pil_image = Image.open(BytesIO(image_data)).convert("RGB")
        pil_images.append(pil_image)
        print(f"  [{i+1}/{len(images_base64)}] Size: {pil_image.size}")

    # Load Chandra model
    print("\nLoading Chandra model...")
    from chandra.model import InferenceManager
    from chandra.model.schema import BatchInputItem

    manager = InferenceManager(method="hf")
    print("  Model loaded successfully")

    # Run OCR on batch
    print(f"\nRunning batch OCR (prompt_type={prompt_type})...")
    batch = [BatchInputItem(image=img, prompt_type=prompt_type) for img in pil_images]
    results = manager.generate(batch)
    print("  Batch OCR complete")

    # Format outputs
    outputs = []
    for i, result in enumerate(results):
        text = result.markdown
        if output_format == "json" and hasattr(result, "json"):
            text = result.json
        elif output_format == "html" and hasattr(result, "html"):
            text = result.html

        outputs.append({
            "index": i,
            "text": text,
            "format": output_format,
            "image_size": pil_images[i].size,
            "prompt_type": prompt_type,
        })

    print(f"\nProcessed {len(outputs)} images")
    return outputs


# =============================================================================
# WEB ENDPOINT (for deployment)
# =============================================================================


@app.function(
    image=image,
    gpu="A100:1",
    timeout=300,
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
@modal.fastapi_endpoint(method="POST")
def ocr_endpoint(request: dict) -> dict:
    """
    Web endpoint for OCR inference.

    POST body:
        {
            "image_base64": "<base64 encoded image>",
            "prompt_type": "ocr_layout",  # optional
            "output_format": "markdown"   # optional
        }

    Returns:
        {
            "text": "<extracted text>",
            "format": "markdown",
            "prompt_type": "ocr_layout",
            "image_size": [width, height]
        }
    """
    image_base64 = request.get("image_base64")
    if not image_base64:
        return {"error": "image_base64 is required"}

    prompt_type = request.get("prompt_type", "ocr_layout")
    output_format = request.get("output_format", "markdown")

    return run_ocr.local(
        image_base64=image_base64,
        prompt_type=prompt_type,
        output_format=output_format,
    )


# =============================================================================
# ENV FILE MANAGEMENT
# =============================================================================


def _update_env_file(env_path: Path, var_name: str, value: str) -> None:
    """Update or add a variable in a .env file."""
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing content
    existing_lines: list[str] = []
    if env_path.exists():
        with open(env_path) as f:
            existing_lines = f.readlines()

    # Check if variable already exists
    pattern = re.compile(rf"^{re.escape(var_name)}=")
    found = False
    new_lines: list[str] = []

    for line in existing_lines:
        if pattern.match(line):
            new_lines.append(f"{var_name}={value}\n")
            found = True
        else:
            new_lines.append(line)

    # Add if not found
    if not found:
        # Ensure newline before adding if file doesn't end with one
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"{var_name}={value}\n")

    # Write back
    with open(env_path, "w") as f:
        f.writelines(new_lines)

    print(f"Updated {env_path}: {var_name}={value}")


def _get_deployed_url() -> str | None:
    """Get the deployed endpoint URL from Modal."""
    try:
        result = subprocess.run(
            ["python3", "-m", "modal", "app", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Look for our app in the output
        for line in result.stdout.split("\n"):
            if "chandra-ocr-inference" in line:
                # App is deployed, get the URL
                url_result = subprocess.run(
                    ["python3", "-m", "modal", "app", "show", "chandra-ocr-inference"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                # Parse URL from output
                for url_line in url_result.stdout.split("\n"):
                    if "https://" in url_line and "modal.run" in url_line:
                        # Extract URL
                        match = re.search(r"(https://[^\s]+\.modal\.run[^\s]*)", url_line)
                        if match:
                            return match.group(1)
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# =============================================================================
# LOCAL ENTRYPOINT
# =============================================================================


@app.local_entrypoint()
def main(
    image: str | None = None,
    image_dir: str | None = None,
    output: str | None = None,
    output_dir: str | None = None,
    output_format: str = "markdown",
    prompt_type: str = "ocr_layout",
):
    """
    Local entrypoint for running Chandra OCR.

    Args:
        image: Path to single image file
        image_dir: Path to directory of images (for batch processing)
        output: Path to save output (for single image)
        output_dir: Path to save outputs (for batch processing)
        output_format: Output format (markdown, json, html)
        prompt_type: Chandra prompt type (ocr_layout, ocr_with_region, ocr)
    """
    import base64

    if not image and not image_dir:
        print("Error: Either --image or --image-dir is required")
        print("\nUsage:")
        print("  # Single image")
        print("  modal run scripts/chandra_ocr_modal.py --image screenshot.png")
        print()
        print("  # Batch processing")
        print("  modal run scripts/chandra_ocr_modal.py --image-dir ./images/")
        print()
        print("  # With output")
        print("  modal run scripts/chandra_ocr_modal.py --image screenshot.png "
              "--output extracted.md")
        print()
        print("Options:")
        print("  --output-format: markdown, json, html (default: markdown)")
        print("  --prompt-type: ocr_layout, ocr_with_region, ocr "
              "(default: ocr_layout)")
        return

    # Single image mode
    if image:
        image_path = Path(image)
        if not image_path.exists():
            print(f"Error: Image not found: {image}")
            return

        print(f"Loading image: {image_path}")
        with open(image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode()

        result = run_ocr.remote(
            image_base64=img_base64,
            prompt_type=prompt_type,
            output_format=output_format,
        )

        # Save or print output
        if output:
            _save_result(result, Path(output), output_format)
        else:
            print(f"\n{'='*80}")
            print("Full Extracted Text:")
            print(f"{'='*80}\n")
            print(result["text"])

    # Batch mode
    elif image_dir:
        dir_path = Path(image_dir)
        if not dir_path.exists():
            print(f"Error: Directory not found: {image_dir}")
            return

        # Find all images
        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        image_files = sorted([
            f for f in dir_path.iterdir()
            if f.suffix.lower() in image_extensions
        ])

        if not image_files:
            print(f"No images found in {image_dir}")
            return

        print(f"Found {len(image_files)} images")

        # Encode all images
        images_base64 = []
        for img_file in image_files:
            with open(img_file, "rb") as f:
                images_base64.append(base64.b64encode(f.read()).decode())

        # Run batch OCR
        results = batch_ocr.remote(
            images_base64=images_base64,
            prompt_type=prompt_type,
            output_format=output_format,
        )

        # Save outputs
        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)

            for i, result in enumerate(results):
                img_name = image_files[i].stem
                ext = ".json" if output_format == "json" else ".md"
                result_path = out_path / f"{img_name}{ext}"
                _save_result(result, result_path, output_format)

            print(f"\nSaved {len(results)} results to {output_dir}")
        else:
            # Print all results
            for i, result in enumerate(results):
                print(f"\n{'='*80}")
                print(f"Image {i+1}: {image_files[i].name}")
                print(f"{'='*80}\n")
                print(result["text"][:1000])
                if len(result["text"]) > 1000:
                    print(f"\n... ({len(result['text']) - 1000} more characters)")


def _save_result(result: dict, output_path: Path, output_format: str) -> None:
    """Save OCR result to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "json" or output_path.suffix == ".json":
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
    else:
        with open(output_path, "w") as f:
            f.write(result["text"])

    print(f"Saved: {output_path}")


# =============================================================================
# POST-DEPLOY HOOK
# =============================================================================
# This runs after `modal deploy` completes

if __name__ == "__main__":
    import sys

    # Check if this is being run after deployment (not via modal run/deploy)
    if len(sys.argv) > 1 and sys.argv[1] == "--write-env":
        # Get URL from Modal
        url = _get_deployed_url()
        if url:
            env_path = Path(os.environ.get("ENV_PATH", str(DEFAULT_ENV_PATH)))
            _update_env_file(env_path, ENV_VAR_NAME, url)
        else:
            print("Warning: Could not retrieve deployed URL from Modal")
        sys.exit(0)
