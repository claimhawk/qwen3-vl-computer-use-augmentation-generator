# Qwen3-VL Training Data Format

## Relative Coordinates (Ground Truth)

- **Training Input**: Use relative [0, 1000] coordinates, NOT absolute pixel coordinates
- **Range**: [0, 1000] normalized coordinates
- **Format**: `[x_min, y_min, x_max, y_max]`
- **Critical**: Coordinates are scaled ONCE and remain constant regardless of image resizing
- **Conversion**: `normalized_coord = (pixel_coord / image_dimension) * 1000`
- **Reverse**: `pixel_coord = (normalized_coord / 1000) * image_dimension`
- **Example**: 100�100 image with bbox (25, 25, 50, 50) � (250, 250, 500, 500) in [0, 1000]
- **Auto-conversion**: Tools like ms-swift auto-convert absolute to relative if needed

### Training Data Format
```json
{
  "messages": [
    {"role": "user", "content": "<image>Locate the <ref-object>"},
    {"role": "assistant", "content": "[{\"bbox_2d\": <bbox>, \"label\": \"<ref-object>\"}]"}
  ],
  "images": ["image.png"],
  "objects": {"bbox": [[x1, y1, x2, y2]]}
}
```

## Image Resizing

- **Parameters**: `resized_height`, `resized_width` (optional)
- **Dynamic**: Model auto-adjusts if not specified
- **Usage**: `{"type": "image", "image": "file:///path.jpg", "resized_height": 280, "resized_width": 420}`
- **Coordinates**: NO adjustment needed after resize[0, 1000] scale persists
- **Processor param**: `do_resize=False` when calling processor
- **Patch size**: `image_patch_size=16` required for `process_vision_info()`

## Think Tags

- **Syntax**: `<think>...</think>`
- **Activation**: `enable_thinking=True`
- **Soft switches**: `/think` (enable), `/no_think` (disable) in user prompts
- **Behavior**: Always outputs `<think>` block when enabled (may be empty)
- **Output**: Think content followed by final response
- **Compatibility**: Soft switches invalid when `enable_thinking=False`

## Tool Calls

- **Format**: Hermes-style recommended
- **Framework**: Qwen-Agent (official, wraps OpenAI API)
- **vLLM**: `--enable-auto-tool-choice --tool-call-parser hermes`
- **Definition**: JSON Schema (function name, description, parameters)
- **WARNING**: Not guaranteedmodel may deviate from protocol
- **Think mode**: Avoid stopword-based templates (ReAct) due to reasoning output
- **Error handling**: Required for malformed tool calls

## Official Resources

- Repo: https://github.com/QwenLM/Qwen3-VL
- Utils: https://github.com/QwenLM/Qwen3-VL/blob/main/qwen-vl-utils/README.md
- Function calling: https://qwen.readthedocs.io/en/latest/framework/function_call.html
