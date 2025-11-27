# CUDAG - ComputerUseDataAugmentedGeneration

A Rails-like framework for building VLM (Vision-Language Model) training data generators.

## Overview

CUDAG provides a convention-over-configuration approach to generating training data for computer use models. It uses a domain-specific MVC-like pattern:

- **Screen** - Declarative UI definition (like Model in Rails)
- **State** - Dynamic data for rendering
- **Renderer** - Image generation (like View in Rails)
- **Task** - Interaction logic (like Controller in Rails)
- **Model** - Domain data types with generators (Patient, Provider, etc.)

## Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install CUDAG and dev dependencies
make install
make dev
```

## Quality Checks

Always run quality checks during development:

```bash
make check      # Run all checks (lint, typecheck, complexity)
make lint       # Ruff linting and format checking
make typecheck  # Mypy strict type checking
make complexity # Radon cyclomatic complexity analysis
make format     # Auto-format code
```

## Development Workflow

Building a CUDAG generator follows this process:

### Step 1: Generate New App

```bash
# Install CUDAG globally
uvx pip install cudag

# Create a new generator project
cudag new claim-window-generator

# Navigate into the project
cd claim-window-generator
```

This creates:
```
claim-window-generator/
├── assets/               # Base images, fonts
├── config/
│   └── dataset.yaml
├── models/               # Domain model definitions
├── tasks/                # Task implementations
├── screen.py             # Screen definition
├── state.py              # State dataclass
├── renderer.py           # Image renderer
└── datasets/             # Output (gitignored)
```

### Step 2: Add Base Images

Copy your blank screen images and fonts:
- **Full screen blank**: `assets/base.png` - The base UI template
- **Region blanks**: `assets/grid_blank.png` - Headers, overlays, etc.
- **Fonts**: `assets/fonts/font.ttf` - Font for rendering text

### Step 3: Generate Data Models

Use Claude to generate domain models for your data:

```python
from cudag import Model, FirstName, LastName, DOB, NPI, Phone, Email
from cudag import string, date_field, money, choice, computed

class Patient(Model):
    first_name = FirstName()
    last_name = LastName()
    dob = DOB()
    member_id = string(pattern=r"[A-Z]{3}[0-9]{6}")
    phone = Phone()
    email = Email()

    # Computed fields
    full_name = computed("first_name", "last_name")
    age = years_since("dob")

class Procedure(Model):
    code = string(pattern=r"D[0-9]{4}")
    description = choice("Exam", "Cleaning", "X-Ray", "Crown")
    fee = money(min_value=50.0, max_value=2500.0)

class Provider(Model):
    first_name = string(faker="first_name")
    last_name = string(faker="last_name")
    npi = string(faker="npi")
    specialty = choice("General", "Orthodontics", "Oral Surgery")
```

**Field Types:**
- `string(faker=..., pattern=..., choices=...)` - Text
- `integer(min_value, max_value)` - Numbers
- `decimal(min_value, max_value, precision)` - Floats
- `money(min_value, max_value)` - Currency ($X.XX)
- `date_field(min_year, max_year, format)` - Dates
- `time_field(min_hour, max_hour, format)` - Times
- `boolean(probability)` - True/False
- `choice(*options, weights)` - Pick from list
- `computed(*sources)` - Derived from other fields
- `years_since(field)` - Age calculation

### Step 4: Define Screen Layout

Declare your screen structure with regions:

```python
from cudag import Screen, grid, button, scrollable, dropdown

class ClaimWindowScreen(Screen):
    name = "claim-window"
    base_image = "images/screen_blank.png"
    size = (1155, 853)

    # Grid region - bounds are (x, y, width, height)
    procedure_grid = grid(
        (0, 217, 1155, 167),
        rows=8,
        cols=17,
    )

    # Scrollable area
    scroll_area = scrollable(
        (0, 217, 1155, 167),
        step=300,
        direction="vertical",
    )

    # Buttons
    billing_provider = button((85, 95, 200, 20), label="Billing Provider")
    save_button = button((100, 800, 80, 30), label="Save")
```

**Region Types:**
- `region(bounds)` - Simple clickable area
- `button(bounds, label, description)` - Clickable button
- `grid(bounds, rows, cols)` - Grid of cells
- `scrollable(bounds, step, direction)` - Scrollable area
- `dropdown(bounds, items)` - Dropdown menu

### Step 5: Build Screen Renderer

Render your screen with PIL, drawing data onto the base image:

```python
from PIL import Image, ImageDraw, ImageFont
from cudag import BaseRenderer
from .screens import ClaimWindowScreen
from .state import GridState

class ClaimWindowRenderer(BaseRenderer[GridState]):
    screen_class = ClaimWindowScreen

    def load_assets(self) -> None:
        self.font = ImageFont.truetype(
            str(self.asset_path("fonts", "font.ttf")), 9
        )

    def render(self, state: GridState) -> tuple[Image.Image, dict]:
        image = self.load_base_image()
        draw = ImageDraw.Draw(image)

        # Render grid rows
        self._render_grid(image, draw, state)

        # Render scrollbar
        self._render_scrollbar(image, state)

        metadata = self.build_metadata(state)
        return image, metadata
```

### Step 6: Build Region Renderers

For complex regions (grids, tables), create dedicated rendering methods:

```python
def _render_grid(self, image, draw, state):
    for idx, row in enumerate(state.visible_rows):
        y = GRID_Y_START + idx * ROW_HEIGHT
        for col in COLUMNS:
            value = getattr(row, col["id"], "")
            x = col["x"]
            draw.text((x, y), str(value), font=self.font, fill=(0, 0, 0))

def _render_scrollbar(self, image, state):
    # Calculate thumb position based on scroll state
    thumb_y = calculate_thumb_position(state)
    draw.rectangle([track_x, thumb_y, track_x + width, thumb_y + height],
                   fill=(100, 100, 100))
```

### Step 7: Test and Align Data

This is critical - manually verify that:
- Grid columns align with data
- Text fits within column widths
- Row wrapping works correctly
- Scroll positions show correct content
- All UI elements render properly

```bash
# Generate a small test batch
python -m my_generator.generator --config config/dataset.yaml

# View generated images
open datasets/my-dataset/images/
```

### Step 8: Create Tasks

Define tasks that generate training samples:

```python
from cudag import BaseTask, TaskSample, TaskContext, ToolCall

class ScrollGridTask(BaseTask):
    task_type = "scroll-grid"

    def generate_sample(self, ctx: TaskContext) -> TaskSample:
        # Generate state
        state = GridState.generate(ctx.rng, min_rows=15, max_rows=28)

        # Render image
        image, metadata = self.renderer.render(state)
        image_path = self.save_image(image, ctx)

        # Get scroll coordinates
        grid_center = self.renderer.get_grid_center()

        return TaskSample(
            id=self.build_id(ctx),
            image_path=image_path,
            human_prompt="Scroll down in the grid.",
            tool_call=ToolCall.scroll(grid_center, pixels=300),
            pixel_coords=grid_center,
            image_size=self.renderer.screen_class.meta().size,
            metadata={"task_type": self.task_type, **metadata},
        )
```

### Step 9: Create Dataset Generator

Wire everything together:

```python
from pathlib import Path
import yaml
from cudag import DatasetBuilder, DatasetConfig
from .renderer import ClaimWindowRenderer
from .tasks import ScrollGridTask

def main():
    with open("config/dataset.yaml") as f:
        config = yaml.safe_load(f)

    dataset_config = DatasetConfig(
        name_prefix=config["name_prefix"],
        seed=config["seed"],
        task_counts=config["tasks"],
        train_split=config["train_split"],
    )

    renderer = ClaimWindowRenderer(Path("assets"))
    tasks = [ScrollGridTask(config.get("task_config", {}), renderer)]

    builder = DatasetBuilder(config=dataset_config, tasks=tasks)
    builder.build()

if __name__ == "__main__":
    main()
```

### Step 10: Generate Production Dataset

```bash
# Generate full dataset
PYTHONPATH=src python -m my_generator.generator

# Verify output
ls datasets/my-dataset/
# images/  data.jsonl  train.jsonl  test.jsonl  config.json

# Check JSONL format
head -1 datasets/my-dataset/data.jsonl | python -m json.tool
```

## Output Format

Generated JSONL structure:

```json
{
  "id": "my-dataset_00000",
  "image": "images/my-dataset_00000.jpg",
  "conversations": [
    {"from": "system", "value": "...tool definitions..."},
    {"from": "human", "value": "<image>\nScroll down in the grid."},
    {"from": "gpt", "value": "<tool_call>{\"name\": \"computer_use\", \"arguments\": {\"action\": \"scroll\", \"coordinate\": [500, 352], \"pixels\": 300}}</tool_call>"}
  ],
  "metadata": {
    "task_type": "scroll-grid",
    "real_coords": [577, 300]
  }
}
```

## Coordinate System

All coordinates use RU (Resolution Units) normalized to [0, 1000]:
- Conversion: `normalized = (pixel / image_dimension) * 1000`
- Real pixel coords stored in `metadata.real_coords`

## Tool Call Actions

- `left_click` - Click at coordinate
- `scroll` - Scroll at coordinate with pixels
- `type` - Type text
- `key` - Press key combination
- `wait` - Wait for duration
- `terminate` - End interaction

## Example Projects

See `test-claim-window/` for a complete example implementing:
- Procedure grid with scrolling
- Provider names and procedure codes
- Multi-column data rendering
- Scroll task generation

## Configuration Reference

```yaml
# config/dataset.yaml
name_prefix: "my-dataset"
seed: 1337

tasks:
  scroll-grid: 100
  click-button: 50

task_config:
  min_rows: 15
  max_rows: 28
  tolerance: 50

train_split: 0.8
system_prompt: "compact"
output_dir: "datasets/my-dataset"
```

## License

Copyright (c) 2025 Tylt LLC. All rights reserved.
