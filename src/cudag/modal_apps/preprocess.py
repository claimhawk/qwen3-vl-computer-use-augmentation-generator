#!/usr/bin/env python3
# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""
CUDAG Dataset Preprocessing on Modal

Preprocess the raw JSONL + images dataset on Modal's CPU instances.
Saves preprocessed tensors to a Modal volume for reuse across training runs.

Usage:
    modal run preprocess.py --dataset-name my-dataset
"""

import json
import multiprocessing
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import modal

# System prompt injected during preprocessing (not stored in training data)
# fmt: off
# ruff: noqa: E501
SYSTEM_PROMPT = """# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{
\t"type": "function",
\t"function": {
\t\t"name_for_human": "computer_use",
\t\t"name": "computer_use",
\t\t"description": "Perform computer actions",
\t\t"parameters": {
\t\t\t"properties": {
\t\t\t\t"action": {
\t\t\t\t\t"description": "* `key`: Press keys in order, release in reverse.\\n* `type`: Type a string of text.\\n* `mouse_move`: Move the cursor to (x, y).\\n* `left_click`: Left click at (x, y).\\n* `left_click_drag`: Click and drag from current to (x, y).\\n* `right_click`: Right click at (x, y).\\n* `middle_click`: Middle click at (x, y).\\n* `double_click`: Double-click at (x, y).\\n* `triple_click`: Triple-click at (x, y) (simulated as double-click).\\n* `scroll`: Scroll the mouse wheel.\\n* `hscroll`: Horizontal scroll.\\n* `wait`: Wait N seconds.\\n* `terminate`: End the task with a status.\\n* `answer`: Answer a question.",
\t\t\t\t\t"enum": ["key", "type", "mouse_move", "left_click", "left_click_drag", "right_click", "middle_click", "double_click", "scroll", "wait", "terminate"],
\t\t\t\t\t"type": "string"
\t\t\t\t},
\t\t\t\t"keys": {"description": "Required only by `action=key`.", "type": "array"},
\t\t\t\t"text": {"description": "Required only by `action=type`.", "type": "string"},
\t\t\t\t"coordinate": {"description": "Mouse coordinates (1000x1000 normalized).", "type": "array"},
\t\t\t\t"pixels": {"description": "The amount of scrolling.", "type": "number"},
\t\t\t\t"time": {"description": "The seconds to wait.", "type": "number"},
\t\t\t\t"status": {"description": "The status of the task.", "type": "string", "enum": ["success", "failure"]}
\t\t\t},
\t\t\t"required": ["action"],
\t\t\t"type": "object"
\t\t},
\t\t"args_format": "Format the arguments as a JSON object."
\t}
}
</tools>

For each function call, return a json object with function name and arguments within
<tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>

# Response format

Response format for every step:
1) Action: a short imperative describing what to do in the UI.
2) One or more <tool_call>...</tool_call> blocks, one per line, each containing only the JSON:
\t{"name": <function-name>, "arguments": <args-json-object>}.

Rules:
- Output exactly in the order: Action, <tool_call>(s).
- Be brief: one sentence for Action.
- Multiple tool calls can be output, one per line.
- Do not output anything else outside those parts.
- If finishing, use action=terminate in the tool call."""
# fmt: on

# =============================================================================
# CENTRALIZED CONFIGURATION
# =============================================================================
# Volume names and model info are loaded from config/adapters.yaml via the SDK.
# Users can customize these by editing the YAML file.

try:
    from sdk.modal_compat import get_base_vlm, get_volume_name

    DEFAULT_VOLUME = get_volume_name("lora_training")
    BASE_MODEL = get_base_vlm()
except ImportError:
    # Fallback when SDK not available
    DEFAULT_VOLUME = "claimhawk-lora-training"
    BASE_MODEL = "Qwen/Qwen3-VL-8B-Instruct"


def _get_generator_name() -> str:
    """Extract generator name from --dataset-name arg for dynamic app naming."""
    for i, arg in enumerate(sys.argv):
        if arg == "--dataset-name" and i + 1 < len(sys.argv):
            ds_name = sys.argv[i + 1]
            # Generator name is first part before dash (e.g., "desktop" from "desktop-mike-...")
            return ds_name.split("-")[0] if ds_name else "cudag"
    return "cudag"


# Modal App Setup - dynamically named based on generator
app = modal.App(f"{_get_generator_name()}-preprocess")

# Volume - matches modal-volumes.md structure
VOLUME = modal.Volume.from_name(DEFAULT_VOLUME, create_if_missing=True)

# Docker Image with Dependencies (CPU-only, no GPU needed)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch==2.4.0",
        "torchvision==0.19.0",
    )
    .pip_install(
        "transformers>=4.57.0",
        "qwen-vl-utils",
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        "tqdm>=4.65.0",
    )
)


@app.function(
    image=image,
    cpu=16,
    memory=32768,  # 32GB RAM
    timeout=7200,  # 2 hours max
    volumes={
        "/data": VOLUME,
    },
)
def preprocess_dataset_impl(dataset_name: str):
    """
    Preprocess the dataset on Modal CPU instance.

    Reads from: /data/datasets/{dataset_name}/
    Writes to:  /data/preprocessed/{dataset_name}/
    """
    import torch
    from PIL import Image
    from qwen_vl_utils import process_vision_info
    from tqdm import tqdm
    from transformers import AutoProcessor

    # Reload the mounted volume to see latest committed data
    VOLUME.reload()

    # Paths - preprocessed folder lives inside dataset folder
    data_root = Path("/data")
    dataset_path = data_root / "datasets" / dataset_name
    preprocessed_path = dataset_path / "preprocessed"

    print(f"\n{'='*80}")
    print(f"Starting CUDAG Preprocessing: {dataset_name}")
    print(f"{'='*80}\n")
    print(f"Dataset: {dataset_name}")
    print(f"Dataset path: {dataset_path}")
    print(f"Output path: {preprocessed_path}")

    # Debug: List what's in the directory
    print(f"\nListing contents of {dataset_path}:")
    if dataset_path.exists():
        all_files = list(dataset_path.iterdir())
        print(f"Found {len(all_files)} items:")
        for item in all_files[:20]:
            print(f"   - {item.name} ({'dir' if item.is_dir() else 'file'})")
    else:
        print("Directory does not exist!")
        print("Available in datasets/:")
        datasets_dir = data_root / "datasets"
        if datasets_dir.exists():
            for item in datasets_dir.iterdir():
                print(f"   - {item.name}")
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    # Find train and val files
    train_files = list(dataset_path.glob("train*.jsonl"))
    val_files = list(dataset_path.glob("val*.jsonl"))
    test_files = list(dataset_path.glob("test*.jsonl"))
    data_files = list(dataset_path.glob("data.jsonl"))

    def load_jsonl(path):
        data = []
        with open(path) as f:
            for line in f:
                data.append(json.loads(line))
        return data

    # Priority: Use existing train/val or train/test splits if available
    if train_files and (val_files or test_files):
        train_path = train_files[0]
        val_path = val_files[0] if val_files else test_files[0]
        print("\nUsing existing dataset split:")
        print(f"   Train: {train_path.name}")
        print(f"   Val: {val_path.name}")
        train_data = load_jsonl(train_path)
        val_data = load_jsonl(val_path)
    elif data_files:
        print("\nFound single data.jsonl, auto-splitting 90/10...")
        all_data = load_jsonl(data_files[0])
        split_idx = int(len(all_data) * 0.9)
        train_data = all_data[:split_idx]
        val_data = all_data[split_idx:]
    else:
        raise FileNotFoundError(
            f"Could not find train*.jsonl/val*.jsonl or data.jsonl in {dataset_path}"
        )

    print("\nDataset size:")
    print(f"   Train samples: {len(train_data)}")
    print(f"   Val samples: {len(val_data)}")

    # Load Processor
    print(f"\n{'='*80}")
    print("Loading Processor")
    print(f"{'='*80}\n")

    model_name = BASE_MODEL
    print(f"Loading processor: {model_name}")
    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    print("Processor loaded")

    # Cache Image Embeddings
    print(f"\n{'='*80}")
    print("Caching Image Embeddings")
    print(f"{'='*80}\n")

    unique_images = set()
    for sample in train_data + val_data:
        unique_images.add(sample["image"])

    total_samples = len(train_data) + len(val_data)
    print(f"Found {len(unique_images)} unique images (from {total_samples} total)")
    print(
        f"Reuse ratio: {total_samples / max(len(unique_images), 1):.1f}x"
    )

    image_cache = {}

    # Helper function for parallel image processing
    def process_single_image(img_path: str) -> tuple[str, dict | None]:
        """Process a single image and return (path, cached_data) or (path, None) on error."""
        img_path_str = str(img_path)

        # Handle nested paths - strip dataset name prefix if present
        base_name = dataset_name.split("/")[0] if "/" in dataset_name else dataset_name
        if img_path_str.startswith(f"{base_name}/"):
            img_path_str = img_path_str[len(base_name) + 1 :]

        full_path = dataset_path / img_path_str
        if not full_path.exists():
            return (img_path, None)

        try:
            image = Image.open(full_path)
            image_inputs, _ = process_vision_info(
                [
                    {
                        "role": "user",
                        "content": [{"type": "image", "image": f"file://{full_path}"}],
                    }
                ],
                image_patch_size=16,
            )

            return (
                img_path,
                {
                    "pixel_values": image_inputs[0] if image_inputs else None,
                    "image": image,
                },
            )
        except Exception as e:
            print(f"Warning: Failed to process {full_path}: {e}")
            return (img_path, None)

    # Process images in parallel using ThreadPoolExecutor
    print("\nProcessing unique images in parallel...")
    num_workers = min(8, multiprocessing.cpu_count())
    print(f"Using {num_workers} workers")

    sorted_images = sorted(unique_images)
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_path = {
            executor.submit(process_single_image, p): p for p in sorted_images
        }
        for future in tqdm(
            as_completed(future_to_path),
            total=len(sorted_images),
            desc="Caching images",
        ):
            img_path, cached_data = future.result()
            if cached_data is not None:
                image_cache[img_path] = cached_data

    print(f"Cached {len(image_cache)} images")

    # Preprocess Data
    print(f"\n{'='*80}")
    print("Preprocessing Data")
    print(f"{'='*80}\n")

    def prepare_sample(sample, image_cache):
        """Prepare a single sample for training."""
        img_path = sample["image"]
        if img_path not in image_cache:
            raise FileNotFoundError(f"Image not in cache: {img_path}")

        cached_image = image_cache[img_path]
        old_conversations = sample["conversations"]

        # Inject system prompt (not stored in training data)
        messages = [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]}
        ]

        # Convert to Qwen-VL format, skipping any system prompts from dataset
        for msg in old_conversations:
            if msg["from"] == "system":
                # Skip - we inject our own system prompt above
                continue
            elif msg["from"] == "human":
                role = "user"
            else:
                role = "assistant"

            content_list = []
            value = msg["value"]

            if "<image>" in value:
                content_list.append({"type": "image"})
                text = value.replace("<image>", "").strip()
                if text:
                    content_list.append({"type": "text", "text": text})
            else:
                content_list.append({"type": "text", "text": value})

            messages.append({"role": role, "content": content_list})

        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )

        image_inputs = (
            [cached_image["pixel_values"]]
            if cached_image["pixel_values"] is not None
            else None
        )

        model_inputs = processor(
            text=[text],
            images=image_inputs,
            videos=None,
            return_tensors="pt",
            padding=False,
            do_resize=False,
        )

        input_ids = (
            model_inputs["input_ids"][0]
            if isinstance(model_inputs["input_ids"][0], torch.Tensor)
            else torch.tensor(model_inputs["input_ids"][0])
        )
        attention_mask = (
            model_inputs["attention_mask"][0]
            if isinstance(model_inputs["attention_mask"][0], torch.Tensor)
            else torch.tensor(model_inputs["attention_mask"][0])
        )

        # Create labels: Only train on assistant responses
        ignore_index = -100
        labels = torch.full_like(input_ids, ignore_index)

        input_ids_list = input_ids.tolist()
        seq_len = len(input_ids_list)
        pos = 0

        while pos < seq_len:
            # Look for <|im_start|>assistant (token ID 77091)
            if input_ids_list[pos] == 77091:
                ans_start = pos + 2
                ans_end = ans_start

                # Find <|im_end|> (token ID 151645)
                while ans_end < seq_len and input_ids_list[ans_end] != 151645:
                    ans_end += 1

                if ans_end < seq_len:
                    labels[ans_start : ans_end + 2] = input_ids[ans_start : ans_end + 2]
                    pos = ans_end
            pos += 1

        result = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }

        if "pixel_values" in model_inputs:
            result["pixel_values"] = model_inputs["pixel_values"]
            result["image_grid_thw"] = model_inputs["image_grid_thw"]

        return result

    # Helper to process and save a single sample
    def process_and_save_sample(
        args: tuple[int, dict, Path],
    ) -> tuple[int, str | None, str | None]:
        """Process a single sample and save to disk. Returns (idx, path, error)."""
        idx, sample, output_dir = args
        try:
            processed = prepare_sample(sample, image_cache)

            processed_cpu = {
                "input_ids": processed["input_ids"].cpu(),
                "attention_mask": processed["attention_mask"].cpu(),
                "labels": processed["labels"].cpu(),
            }
            if "pixel_values" in processed:
                processed_cpu["pixel_values"] = processed["pixel_values"].cpu()
                processed_cpu["image_grid_thw"] = processed["image_grid_thw"].cpu()

            sample_path = output_dir / f"sample_{idx:06d}.pt"
            torch.save(processed_cpu, sample_path)
            return (idx, str(sample_path), None)
        except Exception as e:
            return (idx, None, str(e))

    # Process training data in parallel
    print("Processing training data in parallel...")
    train_output_dir = preprocessed_path / "train"
    train_output_dir.mkdir(parents=True, exist_ok=True)

    train_args = [(i, sample, train_output_dir) for i, sample in enumerate(train_data)]
    train_processed = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_and_save_sample, arg): arg[0] for arg in train_args}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Train"):
            idx, path, error = future.result()
            if error:
                print(f"\nError processing train sample {idx}: {error}")
                raise RuntimeError(f"Failed to process sample {idx}: {error}")
            if path:
                train_processed.append(path)

    # Process validation data in parallel
    print("\nProcessing validation data in parallel...")
    val_output_dir = preprocessed_path / "val"
    val_output_dir.mkdir(parents=True, exist_ok=True)

    val_args = [(i, sample, val_output_dir) for i, sample in enumerate(val_data)]
    val_processed = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_and_save_sample, arg): arg[0] for arg in val_args}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Val"):
            idx, path, error = future.result()
            if error:
                print(f"\nError processing val sample {idx}: {error}")
                raise RuntimeError(f"Failed to process sample {idx}: {error}")
            if path:
                val_processed.append(path)

    # Save metadata
    metadata = {
        "train_samples": len(train_processed),
        "val_samples": len(val_processed),
        "model_name": model_name,
        "dataset_name": dataset_name,
    }

    metadata_path = preprocessed_path / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print("\nPreprocessing complete!")
    print(f"   Train samples: {len(train_processed)}")
    print(f"   Val samples: {len(val_processed)}")

    total_size = (
        sum(f.stat().st_size for f in preprocessed_path.rglob("*.pt")) / (1024**3)
    )
    print(f"   Total preprocessed size: {total_size:.2f} GB")

    # Commit volume changes
    VOLUME.commit()

    print(f"\nPreprocessed data saved to Modal volume: datasets/{dataset_name}/preprocessed")

    print(f"\n{'='*80}")
    print("PREPROCESSING COMPLETE!")
    print(f"{'='*80}\n")

    return {
        "train_samples": len(train_processed),
        "val_samples": len(val_processed),
        "total_size_gb": total_size,
    }


@app.local_entrypoint()
def main(dataset_name: str):
    """
    Local entrypoint for running preprocessing.

    Usage:
        modal run preprocess.py --dataset-name my-dataset
    """
    print(f"\n{'='*80}")
    print("Submitting preprocessing job to Modal...")
    print(f"Dataset: {dataset_name}")
    print(f"{'='*80}\n")

    result = preprocess_dataset_impl.remote(dataset_name)

    print(f"\n{'='*80}")
    print("Preprocessing job completed!")
    print(f"{'='*80}\n")
    print(f"Results: {result}")
