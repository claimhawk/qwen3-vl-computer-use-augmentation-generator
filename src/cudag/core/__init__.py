# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Core framework classes and DSL functions."""

from cudag.core.coords import (
    RU_MAX,
    bounds_to_tolerance,
    calculate_tolerance_ru,
    clamp_coord,
    coord_distance,
    coord_within_tolerance,
    get_normalized_bounds,
    normalize_coord,
    pixel_from_normalized,
    tolerance_to_ru,
)
from cudag.core.button import (
    DIALOG_CANCEL,
    DIALOG_OK,
    LARGE_RECT,
    LARGE_SQUARE,
    MEDIUM_RECT,
    MEDIUM_SQUARE,
    NAV_BUTTON,
    SMALL_RECT,
    SMALL_SQUARE,
    TOOLBAR_BUTTON,
    ButtonPlacement,
    ButtonShape,
    ButtonSpec,
)
from cudag.core.canvas import CanvasConfig, RegionConfig
from cudag.core.grid import Grid, GridCell, GridGeometry
from cudag.core.scrollable_grid import (
    ColumnDef,
    RowLayout,
    ScrollableGrid,
    ScrollableGridGeometry,
    ScrollState as GridScrollState,
)
from cudag.core.data_grid import (
    ColumnDef as DataColumnDef,
    Grid as DataGrid,
    GridGeometry as DataGridGeometry,
    RowLayout as DataRowLayout,
    ScrollableGrid as DataScrollableGrid,
    ScrollState as DataScrollState,
    SelectableRowGrid,
    SelectionState,
    wrap_text as grid_wrap_text,
)
from cudag.core.icon import (
    APP_ICON_LARGE,
    APP_ICON_SMALL,
    DESKTOP_ICON,
    TASKBAR_ICON,
    TOOLBAR_ICON,
    IconLayout,
    IconPlacement,
    IconSpec,
)
from cudag.core.taskbar import TaskbarRenderer, TaskbarState
from cudag.core.dataset import DatasetBuilder, DatasetConfig
from cudag.core.distribution import DistributionSampler
from cudag.core.scroll_task import ScrollTaskBase, ScrollTaskConfig
from cudag.core.iconlist_task import IconListTaskBase, make_tool_call
from cudag.core.grounding_task import GroundingTaskBase, bbox_to_ru, scale_bbox
from cudag.core.verification_task import (
    VerificationPair,
    VerificationSample,
    VerificationTaskBase,
    VerificationTestCase,
)
from cudag.core.models import (
    # Classes
    Attachment,
    BelongsToRel,
    BoolField,
    ChoiceField,
    Claim,
    ComputedField,
    DateField,
    Field,
    FloatField,
    HasManyRel,
    HasOneRel,
    IntField,
    ListField,
    Model,
    ModelGenerator,
    MoneyField,
    Patient,
    Procedure,
    Provider,
    Relationship,
    StringField,
    TimeField,
    # DSL functions
    attribute,
    belongs_to,
    boolean,
    choice,
    computed,
    date_field,
    decimal,
    get_first_name,
    get_last_name,
    has_many,
    has_one,
    integer,
    list_of,
    money,
    string,
    time_field,
    years_since,
    # Semantic field types
    City,
    ClaimNumber,
    ClaimStatus,
    DOB,
    Email,
    Fee,
    FirstName,
    FullName,
    LastName,
    LicenseNumber,
    MemberID,
    NPI,
    Phone,
    ProcedureCode,
    SSN,
    Specialty,
    State,
    Street,
    ZipCode,
)
from cudag.core.renderer import BaseRenderer
from cudag.core.screen import (
    # Classes
    Bounds,
    ButtonRegion,
    ClickRegion,
    DropdownRegion,
    GridRegion,
    Region,
    Screen,
    ScreenBase,
    ScreenMeta,
    ScrollRegion,
    # DSL functions
    button,
    dropdown,
    grid,
    region,
    scrollable,
)
from cudag.core.config import get_config_path, load_yaml_config
from cudag.core.drawing import render_scrollbar
from cudag.core.fonts import SYSTEM_FONTS, load_font, load_font_family
from cudag.core.generator import run_generator
from cudag.core.random import amount, choose, date_in_range, weighted_choice
from cudag.core.state import BaseState, ScrollState
from cudag.core.task import BaseTask, TaskContext, TaskSample, TestCase
from cudag.core.text import (
    center_text_position,
    draw_centered_text,
    measure_text,
    ordinal_suffix,
    truncate_text,
    wrap_text,
)
from cudag.core.utils import check_script_invocation, get_researcher_name

__all__ = [
    # Coordinates
    "RU_MAX",
    "normalize_coord",
    "pixel_from_normalized",
    "get_normalized_bounds",
    "clamp_coord",
    "coord_distance",
    "coord_within_tolerance",
    "tolerance_to_ru",
    "bounds_to_tolerance",
    "calculate_tolerance_ru",
    # Screen DSL - classes
    "Screen",
    "ScreenBase",
    "ScreenMeta",
    "Region",
    "Bounds",
    "ClickRegion",
    "ButtonRegion",
    "GridRegion",
    "ScrollRegion",
    "DropdownRegion",
    # Screen DSL - functions
    "region",
    "button",
    "grid",
    "scrollable",
    "dropdown",
    # Canvas/Region
    "CanvasConfig",
    "RegionConfig",
    # Grid
    "Grid",
    "GridCell",
    "GridGeometry",
    # Scrollable Grid (legacy)
    "ScrollableGrid",
    "ScrollableGridGeometry",
    "ColumnDef",
    "RowLayout",
    "GridScrollState",
    # Data Grid (composable)
    "DataGrid",
    "DataGridGeometry",
    "DataColumnDef",
    "DataRowLayout",
    "DataScrollableGrid",
    "DataScrollState",
    "SelectableRowGrid",
    "SelectionState",
    "grid_wrap_text",
    # Icons
    "IconSpec",
    "IconPlacement",
    "IconLayout",
    "DESKTOP_ICON",
    "TASKBAR_ICON",
    "TOOLBAR_ICON",
    "APP_ICON_LARGE",
    "APP_ICON_SMALL",
    # Taskbar
    "TaskbarState",
    "TaskbarRenderer",
    # Buttons
    "ButtonSpec",
    "ButtonPlacement",
    "ButtonShape",
    "SMALL_SQUARE",
    "MEDIUM_SQUARE",
    "LARGE_SQUARE",
    "SMALL_RECT",
    "MEDIUM_RECT",
    "LARGE_RECT",
    "NAV_BUTTON",
    "TOOLBAR_BUTTON",
    "DIALOG_OK",
    "DIALOG_CANCEL",
    # State
    "BaseState",
    "ScrollState",
    # Renderer
    "BaseRenderer",
    # Task
    "BaseTask",
    "TaskSample",
    "TaskContext",
    "TestCase",
    # Dataset
    "DatasetBuilder",
    "DatasetConfig",
    # Distribution
    "DistributionSampler",
    # Scroll Tasks
    "ScrollTaskBase",
    "ScrollTaskConfig",
    # IconList Tasks
    "IconListTaskBase",
    "make_tool_call",
    # Grounding Tasks
    "GroundingTaskBase",
    "bbox_to_ru",
    "scale_bbox",
    # Verification Tasks
    "VerificationTaskBase",
    "VerificationPair",
    "VerificationSample",
    "VerificationTestCase",
    # Model DSL - classes
    "Model",
    "ModelGenerator",
    "Field",
    "StringField",
    "IntField",
    "FloatField",
    "BoolField",
    "DateField",
    "TimeField",
    "ChoiceField",
    "ListField",
    "MoneyField",
    "ComputedField",
    # Model DSL - functions
    "attribute",
    "string",
    "integer",
    "decimal",
    "money",
    "date_field",
    "time_field",
    "boolean",
    "choice",
    "list_of",
    "computed",
    "years_since",
    # Name generation functions
    "get_first_name",
    "get_last_name",
    # Relationship DSL - classes
    "Relationship",
    "HasManyRel",
    "BelongsToRel",
    "HasOneRel",
    # Relationship DSL - functions
    "has_many",
    "belongs_to",
    "has_one",
    # Common healthcare models
    "Patient",
    "Provider",
    "Procedure",
    "Claim",
    "Attachment",
    # Semantic field types
    "FirstName",
    "LastName",
    "FullName",
    "DOB",
    "NPI",
    "SSN",
    "Phone",
    "Email",
    "Street",
    "City",
    "State",
    "ZipCode",
    "MemberID",
    "ClaimNumber",
    "ProcedureCode",
    "LicenseNumber",
    "Specialty",
    "ClaimStatus",
    "Fee",
    # Utils
    "check_script_invocation",
    "get_researcher_name",
    # Generator
    "run_generator",
    # Fonts
    "load_font",
    "load_font_family",
    "SYSTEM_FONTS",
    # Random utilities
    "choose",
    "date_in_range",
    "amount",
    "weighted_choice",
    # Text utilities
    "measure_text",
    "center_text_position",
    "draw_centered_text",
    "wrap_text",
    "truncate_text",
    "ordinal_suffix",
    # Drawing utilities
    "render_scrollbar",
    # Config utilities
    "load_yaml_config",
    "get_config_path",
]
