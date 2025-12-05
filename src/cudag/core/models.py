# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Rails-like DSL for model definitions.

Simple, readable model definitions with convention over configuration.

Example:
    class Patient(Model):
        first_name = string(faker="first_name")
        last_name = string(faker="last_name")
        dob = date(min_year=1940, max_year=2010)

        full_name = computed("first_name", "last_name")
        age = years_since("dob")

        appointments = has_many("Appointment")
        primary_provider = belongs_to("Provider")
"""

from __future__ import annotations

import random
import string as string_module
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import date, datetime, timedelta
from typing import Any, ClassVar, Generic, TypeVar

# =============================================================================
# Built-in Data (used by fakers)
# =============================================================================

FIRST_NAMES = [
    "James",
    "Mary",
    "John",
    "Patricia",
    "Robert",
    "Jennifer",
    "Michael",
    "Linda",
    "William",
    "Elizabeth",
    "David",
    "Barbara",
    "Richard",
    "Susan",
    "Joseph",
    "Jessica",
    "Thomas",
    "Sarah",
    "Charles",
    "Karen",
    "Christopher",
    "Nancy",
    "Daniel",
    "Lisa",
    "Matthew",
    "Betty",
    "Anthony",
    "Margaret",
    "Mark",
    "Sandra",
    "Donald",
    "Ashley",
]

LAST_NAMES = [
    # Train surnames (first ~90%)
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
    "Hill",
    "Flores",
    "Green",
    "Adams",
    "Nelson",
    "Baker",
    "Hall",
    "Rivera",
    # Test surnames (last ~10% - held out for evaluation)
    "Campbell",
    "Mitchell",
    "Roberts",
    "Carter",
    "Phillips",
]

# Index where test surnames start (for train/test split)
_LAST_NAME_TEST_START = 46


def get_last_name(
    rng: random.Random,
    augment: bool = False,
    split: str = "train",
) -> str:
    """Get a last name with optional augmentation and train/test split.

    Args:
        rng: Random number generator
        augment: If True, may add augmentation (Jr., III, etc.)
        split: "train" uses first 90% of surnames, "test" uses held-out 10%

    Returns:
        Last name string, optionally augmented
    """
    if split == "test":
        names = LAST_NAMES[_LAST_NAME_TEST_START:]
    else:
        names = LAST_NAMES[:_LAST_NAME_TEST_START]

    name = rng.choice(names)

    if augment and rng.random() < 0.1:
        suffix = rng.choice(["Jr.", "Sr.", "II", "III", "IV"])
        name = f"{name} {suffix}"

    return name


def get_first_name(rng: random.Random) -> str:
    """Get a random first name.

    Args:
        rng: Random number generator

    Returns:
        First name string
    """
    return rng.choice(FIRST_NAMES)

US_STATES = [
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
]

CITIES = [
    "New York",
    "Los Angeles",
    "Chicago",
    "Houston",
    "Phoenix",
    "Philadelphia",
    "San Antonio",
    "San Diego",
    "Dallas",
    "San Jose",
]

STREET_SUFFIXES = ["St", "Ave", "Blvd", "Dr", "Ln", "Rd", "Way", "Ct", "Pl"]


# =============================================================================
# Field DSL - lowercase functions that return Field instances
# =============================================================================


@dataclass
class Field:
    """Base field - use the DSL functions below instead of this directly."""

    _type: str = "base"
    required: bool = True
    default: Any = None

    def generate(self, rng: random.Random) -> Any:
        """Generate a value. Override in subclasses."""
        return self.default


# --- String Fields ---


@dataclass
class StringField(Field):
    """String field implementation."""

    _type: str = "string"
    faker: str | None = None
    pattern: str | None = None
    choices: list[str] | None = None
    min_length: int = 5
    max_length: int = 20

    def generate(self, rng: random.Random) -> str:
        if self.choices:
            return rng.choice(self.choices)
        if self.faker:
            return _generate_faker(self.faker, rng)
        if self.pattern:
            return _generate_pattern(self.pattern, rng)
        length = rng.randint(self.min_length, self.max_length)
        return "".join(rng.choices(string_module.ascii_letters, k=length))


def string(
    faker: str | None = None,
    pattern: str | None = None,
    choices: list[str] | None = None,
    default: str | None = None,
    required: bool = True,
) -> StringField:
    """Define a string field.

    Examples:
        first_name = string(faker="first_name")
        member_id = string(pattern=r"[A-Z]{3}[0-9]{6}")
        status = string(choices=["active", "inactive"])
    """
    return StringField(
        faker=faker, pattern=pattern, choices=choices, default=default, required=required
    )


# --- Numeric Fields ---


@dataclass
class IntField(Field):
    """Integer field implementation."""

    _type: str = "int"
    min_value: int = 0
    max_value: int = 100

    def generate(self, rng: random.Random) -> int:
        return rng.randint(self.min_value, self.max_value)


def integer(
    min_value: int = 0,
    max_value: int = 100,
    default: int | None = None,
    required: bool = True,
) -> IntField:
    """Define an integer field.

    Example:
        age = integer(min_value=18, max_value=100)
    """
    return IntField(min_value=min_value, max_value=max_value, default=default, required=required)


@dataclass
class FloatField(Field):
    """Float field implementation."""

    _type: str = "float"
    min_value: float = 0.0
    max_value: float = 100.0
    precision: int = 2

    def generate(self, rng: random.Random) -> float:
        value = rng.uniform(self.min_value, self.max_value)
        return round(value, self.precision)


def decimal(
    min_value: float = 0.0,
    max_value: float = 100.0,
    precision: int = 2,
    default: float | None = None,
    required: bool = True,
) -> FloatField:
    """Define a decimal field.

    Example:
        price = decimal(min_value=0.01, max_value=999.99, precision=2)
    """
    return FloatField(
        min_value=min_value,
        max_value=max_value,
        precision=precision,
        default=default,
        required=required,
    )


def money(
    min_value: float = 0.0,
    max_value: float = 1000.0,
    default: float | None = None,
) -> MoneyField:
    """Define a money field (formatted as $X.XX).

    Example:
        fee = money(min_value=50.0, max_value=2500.0)
    """
    return MoneyField(min_value=min_value, max_value=max_value, default=default)


@dataclass
class MoneyField(Field):
    """Money field - formats as $X.XX."""

    _type: str = "money"
    min_value: float = 0.0
    max_value: float = 1000.0

    def generate(self, rng: random.Random) -> str:
        value = rng.uniform(self.min_value, self.max_value)
        return f"${value:.2f}"


# --- Date/Time Fields ---


@dataclass
class DateField(Field):
    """Date field implementation."""

    _type: str = "date"
    min_year: int = 2000
    max_year: int = 2025
    format: str = "%Y-%m-%d"

    def generate(self, rng: random.Random) -> str:
        start = date(self.min_year, 1, 1)
        end = date(self.max_year, 12, 31)
        days_between = (end - start).days
        random_days = rng.randint(0, days_between)
        result_date = start + timedelta(days=random_days)
        return result_date.strftime(self.format)


def date_field(
    min_year: int = 2000,
    max_year: int = 2025,
    format: str = "%Y-%m-%d",
    default: str | None = None,
    required: bool = True,
) -> DateField:
    """Define a date field.

    Example:
        dob = date_field(min_year=1940, max_year=2010, format="%m/%d/%Y")
    """
    return DateField(
        min_year=min_year, max_year=max_year, format=format, default=default, required=required
    )


@dataclass
class TimeField(Field):
    """Time field implementation."""

    _type: str = "time"
    min_hour: int = 0
    max_hour: int = 23
    format: str = "%I:%M %p"

    def generate(self, rng: random.Random) -> str:
        hour = rng.randint(self.min_hour, self.max_hour)
        minute = rng.choice([0, 15, 30, 45])
        dt = datetime(2000, 1, 1, hour, minute)
        return dt.strftime(self.format)


def time_field(
    min_hour: int = 0,
    max_hour: int = 23,
    format: str = "%I:%M %p",
    default: str | None = None,
    required: bool = True,
) -> TimeField:
    """Define a time field.

    Example:
        appointment_time = time_field(min_hour=8, max_hour=17)
    """
    return TimeField(
        min_hour=min_hour, max_hour=max_hour, format=format, default=default, required=required
    )


# --- Boolean Field ---


@dataclass
class BoolField(Field):
    """Boolean field implementation."""

    _type: str = "bool"
    probability: float = 0.5

    def generate(self, rng: random.Random) -> bool:
        return rng.random() < self.probability


def boolean(probability: float = 0.5, default: bool | None = None) -> BoolField:
    """Define a boolean field.

    Example:
        is_active = boolean(probability=0.8)  # 80% chance True
    """
    return BoolField(probability=probability, default=default)


# --- Choice Field ---


@dataclass
class ChoiceField(Field):
    """Choice field implementation."""

    _type: str = "choice"
    choices: list[Any] = dataclass_field(default_factory=list)
    weights: list[float] | None = None

    def generate(self, rng: random.Random) -> Any:
        if not self.choices:
            raise ValueError("choice() requires at least one option")
        if self.weights:
            return rng.choices(self.choices, weights=self.weights, k=1)[0]
        return rng.choice(self.choices)


def choice(
    *options: Any,
    weights: list[float] | None = None,
    default: Any = None,
) -> ChoiceField:
    """Define a choice field.

    Example:
        status = choice("pending", "approved", "denied")
        status = choice("pending", "approved", weights=[0.7, 0.3])
    """
    return ChoiceField(choices=list(options), weights=weights, default=default)


# --- List Field ---


@dataclass
class ListField(Field):
    """List field implementation."""

    _type: str = "list"
    item_field: Field = dataclass_field(default_factory=lambda: StringField())
    min_items: int = 1
    max_items: int = 5

    def generate(self, rng: random.Random) -> list[Any]:
        count = rng.randint(self.min_items, self.max_items)
        return [self.item_field.generate(rng) for _ in range(count)]


def list_of(
    item_field: Field,
    min_items: int = 1,
    max_items: int = 5,
) -> ListField:
    """Define a list field.

    Example:
        phones = list_of(string(faker="phone"), min_items=1, max_items=3)
    """
    return ListField(item_field=item_field, min_items=min_items, max_items=max_items)


# =============================================================================
# Computed Fields - derive values from other fields
# =============================================================================


@dataclass
class ComputedField(Field):
    """Computed field that derives value from other fields."""

    _type: str = "computed"
    sources: tuple[str, ...] = ()
    formula: str = "concat"
    separator: str = " "

    def generate(self, rng: random.Random) -> Any:
        return None  # Computed after generation

    def compute(self, instance: Model) -> Any:
        """Compute value from instance fields."""
        if self.formula == "concat":
            values = [str(getattr(instance, s, "")) for s in self.sources]
            return self.separator.join(values)
        elif self.formula == "years_since":
            if len(self.sources) != 1:
                return 0
            source_val = getattr(instance, self.sources[0], None)
            return _compute_years_since(source_val)
        return None


def computed(*sources: str, separator: str = " ") -> ComputedField:
    """Define a computed field that concatenates other fields.

    Example:
        full_name = computed("first_name", "last_name")
        full_address = computed("street", "city", "state", separator=", ")
    """
    return ComputedField(sources=sources, formula="concat", separator=separator)


def years_since(source: str) -> ComputedField:
    """Define a computed field that calculates years since a date.

    Example:
        age = years_since("dob")
    """
    return ComputedField(sources=(source,), formula="years_since")


# =============================================================================
# Relationships - Rails-style with convention over configuration
# =============================================================================


@dataclass
class Relationship:
    """Base relationship class."""

    model: str
    foreign_key: str | None = None  # Convention: model_name_id

    def resolve(self, registry: dict[str, type[Model]]) -> type[Model] | None:
        return registry.get(self.model)

    def inferred_foreign_key(self) -> str:
        """Infer foreign key from model name (Rails convention)."""
        if self.foreign_key:
            return self.foreign_key
        # Convert CamelCase to snake_case_id
        name = self.model
        result: list[str] = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        return "".join(result) + "_id"


@dataclass
class HasManyRel(Relationship):
    """Has-many relationship."""

    min_count: int = 1
    max_count: int = 10


@dataclass
class BelongsToRel(Relationship):
    """Belongs-to relationship."""

    pass


@dataclass
class HasOneRel(Relationship):
    """Has-one relationship."""

    pass


def has_many(
    model: str,
    foreign_key: str | None = None,
    min_count: int = 1,
    max_count: int = 10,
) -> HasManyRel:
    """Define a has-many relationship.

    Example:
        appointments = has_many("Appointment")
        appointments = has_many("Appointment", min_count=0, max_count=20)
    """
    return HasManyRel(
        model=model, foreign_key=foreign_key, min_count=min_count, max_count=max_count
    )


def belongs_to(model: str, foreign_key: str | None = None) -> BelongsToRel:
    """Define a belongs-to relationship.

    Example:
        patient = belongs_to("Patient")
        treating_provider = belongs_to("Provider", foreign_key="treating_provider_id")
    """
    return BelongsToRel(model=model, foreign_key=foreign_key)


def has_one(model: str, foreign_key: str | None = None) -> HasOneRel:
    """Define a has-one relationship.

    Example:
        primary_provider = has_one("Provider")
    """
    return HasOneRel(model=model, foreign_key=foreign_key)


# =============================================================================
# Rails-like attribute() DSL
# =============================================================================

# Pending attributes registered by attribute() calls during class body execution
_pending_attributes: list[tuple[str, Field | Relationship]] = []


def attribute(name: str, field_type: str, *args: Any, **kwargs: Any) -> None:
    """Register an attribute on the model being defined.

    Rails-like DSL for defining model attributes:

        class User(Model):
            attribute("name", "string")
            attribute("age", "integer")
            attribute("email", "email")
            attribute("status", "choice", "active", "inactive", "pending")

    Args:
        name: Attribute name
        field_type: Type of field (string, integer, choice, email, npi, etc.)
        *args: Positional args passed to field constructor
        **kwargs: Keyword args passed to field constructor
    """
    field = _make_field(field_type, *args, **kwargs)
    _pending_attributes.append((name, field))


def _make_field(field_type: str, *args: Any, **kwargs: Any) -> Field:
    """Create a field from type name."""
    # Semantic types (no args needed)
    semantic_types: dict[str, Any] = {
        "first_name": FirstName,
        "last_name": LastName,
        "full_name": FullName,
        "dob": DOB,
        "npi": NPI,
        "ssn": SSN,
        "phone": Phone,
        "email": Email,
        "street": Street,
        "city": City,
        "state": State,
        "zip": ZipCode,
        "zip_code": ZipCode,
        "member_id": MemberID,
        "claim_number": ClaimNumber,
        "procedure_code": ProcedureCode,
        "license_number": LicenseNumber,
        "specialty": Specialty,
        "claim_status": ClaimStatus,
        "fee": Fee,
    }

    # Base types
    base_types: dict[str, Any] = {
        "string": string,
        "integer": integer,
        "int": integer,
        "decimal": decimal,
        "float": decimal,
        "money": money,
        "date": date_field,
        "time": time_field,
        "boolean": boolean,
        "bool": boolean,
        "choice": choice,
        "list": list_of,
        "computed": computed,
    }

    field_type_lower = field_type.lower()

    # Check semantic types first
    if field_type_lower in semantic_types:
        return semantic_types[field_type_lower](*args, **kwargs)

    # Check base types
    if field_type_lower in base_types:
        return base_types[field_type_lower](*args, **kwargs)

    raise ValueError(f"Unknown field type: {field_type}")


# =============================================================================
# Model Base Class
# =============================================================================


class ModelMeta(type):
    """Metaclass that collects field definitions."""

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> ModelMeta:
        global _pending_attributes

        fields: dict[str, Field] = {}
        relationships: dict[str, Relationship] = {}

        # Inherit from parents
        for base in bases:
            if hasattr(base, "_fields"):
                fields.update(base._fields)
            if hasattr(base, "_relationships"):
                relationships.update(base._relationships)

        # Process pending attributes from attribute() calls
        for attr_name, attr_value in _pending_attributes:
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value
            elif isinstance(attr_value, Relationship):
                relationships[attr_name] = attr_value
        _pending_attributes = []

        # Collect from class attributes (original style still works)
        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value
            elif isinstance(attr_value, Relationship):
                relationships[attr_name] = attr_value

        namespace["_fields"] = fields
        namespace["_relationships"] = relationships
        return super().__new__(mcs, name, bases, namespace)


T = TypeVar("T", bound="Model")


class Model(metaclass=ModelMeta):
    """Base class for data models.

    Example:
        class Patient(Model):
            first_name = string(faker="first_name")
            last_name = string(faker="last_name")
            dob = date_field(min_year=1940, max_year=2010)

            full_name = computed("first_name", "last_name")
            age = years_since("dob")

            appointments = has_many("Appointment")

        patient = Patient.generate()
    """

    _fields: ClassVar[dict[str, Field]] = {}
    _relationships: ClassVar[dict[str, Relationship]] = {}

    def __init__(self, **kwargs: Any) -> None:
        for name, field_def in self._fields.items():
            # Skip computed fields - they're computed after init
            if isinstance(field_def, ComputedField):
                continue
            if name in kwargs:
                setattr(self, name, kwargs[name])
            elif field_def.default is not None:
                setattr(self, name, field_def.default)
            elif not field_def.required:
                setattr(self, name, None)
            else:
                raise ValueError(f"Missing required field: {name}")

        # Compute derived fields
        for name, field_def in self._fields.items():
            if isinstance(field_def, ComputedField):
                setattr(self, name, field_def.compute(self))

    @classmethod
    def generate(cls: type[T], rng: random.Random | None = None) -> T:
        """Generate a single model instance with random data.

        Args:
            rng: Optional seeded random generator for reproducibility

        Returns:
            Single model instance
        """
        if rng is None:
            rng = random.Random()

        kwargs = {}
        for name, field_def in cls._fields.items():
            if not isinstance(field_def, ComputedField):
                kwargs[name] = field_def.generate(rng)

        return cls(**kwargs)

    @classmethod
    def generate_many(
        cls: type[T],
        count: int,
        rng: random.Random | None = None,
    ) -> list[T]:
        """Generate multiple model instances with random data.

        Args:
            count: Number of instances to generate
            rng: Optional seeded random generator for reproducibility

        Returns:
            List of model instances
        """
        if rng is None:
            rng = random.Random()
        return [cls.generate(rng) for _ in range(count)]

    @classmethod
    def generator(cls: type[T], rng: random.Random | None = None) -> "ModelGenerator[T]":
        """Get a generator instance for this model.

        Args:
            rng: Optional seeded random generator

        Returns:
            ModelGenerator that yields instances
        """
        return ModelGenerator(cls, rng)

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {name: getattr(self, name) for name in self._fields}

    def __repr__(self) -> str:
        fields_str = ", ".join(f"{k}={getattr(self, k)!r}" for k in self._fields)
        return f"{self.__class__.__name__}({fields_str})"


class ModelGenerator(Generic[T]):
    """Generator wrapper for creating model instances.

    Provides iterator-based generation and batch methods.

    Example:
        gen = Patient.generator(rng)
        patient = gen.one()
        patients = gen.many(10)

        # Or iterate
        for patient in gen.take(5):
            print(patient)
    """

    def __init__(self, model_class: type[T], rng: random.Random | None = None) -> None:
        self.model_class = model_class
        self.rng = rng or random.Random()

    def one(self) -> T:
        """Generate a single instance."""
        return self.model_class.generate(self.rng)

    def many(self, count: int) -> list[T]:
        """Generate multiple instances."""
        return self.model_class.generate_many(count, self.rng)

    def take(self, count: int) -> list[T]:
        """Alias for many()."""
        return self.many(count)

    def __iter__(self) -> "ModelGenerator[T]":
        return self

    def __next__(self) -> T:
        return self.one()


# =============================================================================
# Helper Functions
# =============================================================================


def _generate_faker(faker_type: str, rng: random.Random) -> str:
    """Generate value using built-in faker."""
    match faker_type:
        case "first_name":
            return rng.choice(FIRST_NAMES)
        case "last_name":
            return rng.choice(LAST_NAMES)
        case "full_name":
            return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        case "city":
            return rng.choice(CITIES)
        case "state":
            return rng.choice(US_STATES)
        case "street":
            num = rng.randint(100, 9999)
            name = rng.choice(LAST_NAMES)
            suffix = rng.choice(STREET_SUFFIXES)
            return f"{num} {name} {suffix}"
        case "phone":
            area = rng.randint(200, 999)
            prefix = rng.randint(200, 999)
            line = rng.randint(1000, 9999)
            return f"({area}) {prefix}-{line}"
        case "email":
            first = rng.choice(FIRST_NAMES).lower()
            last = rng.choice(LAST_NAMES).lower()
            domain = rng.choice(["gmail.com", "yahoo.com", "outlook.com"])
            return f"{first}.{last}@{domain}"
        case "ssn":
            return f"{rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}"
        case "npi":
            return "".join(str(rng.randint(0, 9)) for _ in range(10))
        case "zip":
            return f"{rng.randint(10000, 99999)}"
        case _:
            raise ValueError(f"Unknown faker: {faker_type}")


def _generate_pattern(pattern: str, rng: random.Random) -> str:
    """Generate string from simple regex pattern."""
    result: list[str] = []
    i = 0

    while i < len(pattern):
        char = pattern[i]

        if char == "[":
            end = pattern.index("]", i)
            char_class = pattern[i + 1 : end]
            chars = _parse_char_class(char_class)

            i = end + 1
            count = 1
            if i < len(pattern) and pattern[i] == "{":
                end_q = pattern.index("}", i)
                count = int(pattern[i + 1 : end_q])
                i = end_q + 1

            result.extend(rng.choice(chars) for _ in range(count))
        else:
            result.append(char)
            i += 1

    return "".join(result)


def _parse_char_class(char_class: str) -> list[str]:
    """Parse character class like A-Z or 0-9."""
    chars: list[str] = []
    j = 0
    while j < len(char_class):
        if j + 2 < len(char_class) and char_class[j + 1] == "-":
            start_char = char_class[j]
            end_char = char_class[j + 2]
            chars.extend(chr(c) for c in range(ord(start_char), ord(end_char) + 1))
            j += 3
        else:
            chars.append(char_class[j])
            j += 1
    return chars


def _compute_years_since(date_value: Any) -> int:
    """Compute years since a date value."""
    if not date_value:
        return 0
    try:
        if isinstance(date_value, str):
            for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    birth = datetime.strptime(date_value, fmt)
                    today = date.today()
                    born_later = (today.month, today.day) < (birth.month, birth.day)
                    return today.year - birth.year - int(born_later)
                except ValueError:
                    continue
    except Exception:
        pass
    return 0


# =============================================================================
# Semantic Field Types - Django-like convenience classes
# =============================================================================


def FirstName() -> StringField:
    """First name field."""
    return string(faker="first_name")


def LastName() -> StringField:
    """Last name field."""
    return string(faker="last_name")


def FullName() -> StringField:
    """Full name field."""
    return string(faker="full_name")


def DOB(min_year: int = 1940, max_year: int = 2010) -> DateField:
    """Date of birth field."""
    return date_field(min_year=min_year, max_year=max_year, format="%m/%d/%Y")


def NPI() -> StringField:
    """National Provider Identifier (10 digits)."""
    return string(faker="npi")


def SSN() -> StringField:
    """Social Security Number."""
    return string(faker="ssn")


def Phone() -> StringField:
    """Phone number."""
    return string(faker="phone")


def Email() -> StringField:
    """Email address."""
    return string(faker="email")


def Street() -> StringField:
    """Street address."""
    return string(faker="street")


def City() -> StringField:
    """City name."""
    return string(faker="city")


def State() -> StringField:
    """US state abbreviation."""
    return string(faker="state")


def ZipCode() -> StringField:
    """ZIP code."""
    return string(faker="zip")


def MemberID(prefix: str = "", digits: int = 6) -> StringField:
    """Member/account ID with pattern."""
    if prefix:
        return string(pattern=f"{prefix}[0-9]{{{digits}}}")
    return string(pattern=f"[A-Z]{{3}}[0-9]{{{digits}}}")


def ClaimNumber() -> StringField:
    """Claim number."""
    return string(pattern=r"CLM[0-9]{8}")


def ProcedureCode() -> StringField:
    """Dental procedure code (D####)."""
    return string(pattern=r"D[0-9]{4}")


def LicenseNumber() -> StringField:
    """License number."""
    return string(pattern=r"[A-Z]{2}[0-9]{6}")


def Specialty(*options: str) -> ChoiceField:
    """Provider specialty."""
    if not options:
        options = (
            "General Dentistry",
            "Orthodontics",
            "Periodontics",
            "Endodontics",
            "Oral Surgery",
        )
    return choice(*options)


def ClaimStatus() -> ChoiceField:
    """Claim status."""
    return choice("Pending", "Approved", "Denied", "In Review", "Paid")


def Fee(min_value: float = 50.0, max_value: float = 2500.0) -> MoneyField:
    """Fee/charge amount."""
    return money(min_value=min_value, max_value=max_value)


# =============================================================================
# Common Healthcare Models
# =============================================================================


class Patient(Model):
    """Patient with common healthcare fields."""

    first_name = FirstName()
    last_name = LastName()
    dob = DOB()
    member_id = MemberID()
    ssn = SSN()
    phone = Phone()
    email = Email()
    street = Street()
    city = City()
    state = State()
    zip_code = ZipCode()

    full_name = computed("first_name", "last_name")
    age = years_since("dob")


class Provider(Model):
    """Provider (treating or billing)."""

    first_name = FirstName()
    last_name = LastName()
    npi = NPI()
    license_number = LicenseNumber()
    specialty = Specialty()
    phone = Phone()

    full_name = computed("first_name", "last_name")


class Procedure(Model):
    """Dental procedure."""

    code = ProcedureCode()
    description = choice(
        "Periodic oral evaluation",
        "Comprehensive oral evaluation",
        "Prophylaxis - adult",
        "Topical fluoride",
        "Bitewing - single film",
        "Panoramic film",
        "Amalgam - one surface",
        "Resin composite - one surface",
        "Crown - porcelain/ceramic",
        "Root canal - anterior",
        "Extraction - single tooth",
    )
    tooth = choice(*[str(i) for i in range(1, 33)])
    surface = choice("M", "O", "D", "B", "L", "I", "MO", "DO", "MOD")
    fee = Fee()


class Claim(Model):
    """Insurance claim."""

    claim_number = ClaimNumber()
    date_of_service = date_field(min_year=2023, max_year=2025, format="%m/%d/%Y")
    date_submitted = date_field(min_year=2023, max_year=2025, format="%m/%d/%Y")
    status = ClaimStatus()
    total_charge = Fee(min_value=100.0, max_value=5000.0)
    insurance_paid = Fee(min_value=50.0, max_value=4000.0)
    patient_responsibility = Fee(min_value=0.0, max_value=1000.0)


class Attachment(Model):
    """Document attachment."""

    filename = string(pattern=r"[a-z]{8}.[a-z]{3}")
    file_type = choice("PDF", "JPG", "PNG", "TIFF", "DOC")
    date_uploaded = date_field(min_year=2023, max_year=2025, format="%m/%d/%Y")
    description = choice(
        "X-Ray",
        "Periodontal Chart",
        "Treatment Plan",
        "Insurance Card",
        "EOB",
        "Referral",
        "Clinical Notes",
    )
