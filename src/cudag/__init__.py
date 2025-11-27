# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""CUDAG - ComputerUseDataAugmentedGeneration framework.

A Rails-like DSL for generating VLM training data.

Example model:
    class Patient(Model):
        first_name = string(faker="first_name")
        last_name = string(faker="last_name")
        dob = date_field(min_year=1940, max_year=2010)

        full_name = computed("first_name", "last_name")
        appointments = has_many("Appointment")

Example screen:
    class CalendarScreen(Screen):
        name = "calendar"
        base_image = "calendar.png"
        size = (224, 208)

        day_grid = grid((10, 50, 210, 150), rows=6, cols=7)
        back_month = button((7, 192, 20, 12), label="Back")

CLI:
    cudag new <project-name>
    cudag generate --config config/dataset.yaml
"""

__version__ = "0.1.0"

# Core classes and DSL functions
from cudag.core import (
    # Coordinates
    RU_MAX,
    # Model DSL - classes
    Attachment,
    # Renderer
    BaseRenderer,
    # State
    BaseState,
    # Task
    BaseTask,
    BelongsToRel,
    BoolField,
    # Screen DSL - classes
    Bounds,
    ButtonRegion,
    ChoiceField,
    Claim,
    ClickRegion,
    ComputedField,
    # Dataset
    DatasetBuilder,
    DatasetConfig,
    DateField,
    DropdownRegion,
    EvalCase,
    Field,
    FloatField,
    GridRegion,
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
    Region,
    Relationship,
    Screen,
    ScreenBase,
    ScreenMeta,
    ScrollRegion,
    ScrollState,
    StringField,
    TaskContext,
    TaskSample,
    TimeField,
    # Model DSL - functions
    attribute,
    belongs_to,
    boolean,
    # Screen DSL - functions
    button,
    choice,
    clamp_coord,
    computed,
    coord_distance,
    coord_within_tolerance,
    date_field,
    decimal,
    dropdown,
    grid,
    has_many,
    has_one,
    integer,
    list_of,
    money,
    normalize_coord,
    pixel_from_normalized,
    region,
    scrollable,
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

# Prompts
from cudag.prompts import (
    COMPUTER_USE_TOOL,
    SYSTEM_PROMPT_COMPACT,
    SYSTEM_PROMPT_OSWORLD,
    TOOL_ACTIONS,
    ToolCall,
    format_tool_call,
    get_system_prompt,
    parse_tool_call,
    validate_tool_call,
)

__all__ = [
    # Version
    "__version__",
    # Coordinates
    "RU_MAX",
    "normalize_coord",
    "pixel_from_normalized",
    "clamp_coord",
    "coord_distance",
    "coord_within_tolerance",
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
    # State
    "BaseState",
    "ScrollState",
    # Renderer
    "BaseRenderer",
    # Task
    "BaseTask",
    "TaskSample",
    "TaskContext",
    "EvalCase",
    # Dataset
    "DatasetBuilder",
    "DatasetConfig",
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
    # Prompts
    "COMPUTER_USE_TOOL",
    "TOOL_ACTIONS",
    "ToolCall",
    "format_tool_call",
    "parse_tool_call",
    "validate_tool_call",
    "SYSTEM_PROMPT_OSWORLD",
    "SYSTEM_PROMPT_COMPACT",
    "get_system_prompt",
]
