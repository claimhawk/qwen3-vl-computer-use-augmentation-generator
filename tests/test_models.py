# Copyright (c) 2025 Tylt LLC. All rights reserved.
"""Tests for models.py DSL functions."""

import random

import pytest

from cudag.core.models import (
    BelongsToRel,
    BoolField,
    ChoiceField,
    ComputedField,
    DateField,
    FloatField,
    HasManyRel,
    HasOneRel,
    IntField,
    ListField,
    Model,
    MoneyField,
    Patient,
    Provider,
    StringField,
    TimeField,
    belongs_to,
    boolean,
    choice,
    computed,
    date_field,
    decimal,
    has_many,
    has_one,
    integer,
    list_of,
    money,
    string,
    time_field,
    years_since,
)


class TestStringField:
    """Tests for string() DSL function."""

    def test_string_with_faker(self) -> None:
        field = string(faker="first_name")
        assert isinstance(field, StringField)
        assert field.faker == "first_name"

    def test_string_with_pattern(self) -> None:
        field = string(pattern=r"[A-Z]{3}[0-9]{6}")
        assert field.pattern == r"[A-Z]{3}[0-9]{6}"

    def test_string_with_choices(self) -> None:
        field = string(choices=["a", "b", "c"])
        assert field.choices == ["a", "b", "c"]

    def test_string_generate_with_faker(self) -> None:
        field = string(faker="first_name")
        rng = random.Random(42)
        value = field.generate(rng)
        assert isinstance(value, str)
        assert len(value) > 0

    def test_string_generate_with_pattern(self) -> None:
        field = string(pattern=r"[A-Z]{3}[0-9]{3}")
        rng = random.Random(42)
        value = field.generate(rng)
        assert len(value) == 6
        assert value[:3].isupper()
        assert value[3:].isdigit()

    def test_string_generate_with_choices(self) -> None:
        field = string(choices=["x", "y", "z"])
        rng = random.Random(42)
        value = field.generate(rng)
        assert value in ["x", "y", "z"]

    def test_string_generate_random(self) -> None:
        field = string()
        rng = random.Random(42)
        value = field.generate(rng)
        assert isinstance(value, str)
        assert 5 <= len(value) <= 20


class TestIntegerField:
    """Tests for integer() DSL function."""

    def test_integer_default_range(self) -> None:
        field = integer()
        assert isinstance(field, IntField)
        assert field.min_value == 0
        assert field.max_value == 100

    def test_integer_custom_range(self) -> None:
        field = integer(min_value=10, max_value=50)
        assert field.min_value == 10
        assert field.max_value == 50

    def test_integer_generate(self) -> None:
        field = integer(min_value=1, max_value=10)
        rng = random.Random(42)
        for _ in range(20):
            value = field.generate(rng)
            assert 1 <= value <= 10


class TestDecimalField:
    """Tests for decimal() DSL function."""

    def test_decimal_default(self) -> None:
        field = decimal()
        assert isinstance(field, FloatField)
        assert field.precision == 2

    def test_decimal_generate(self) -> None:
        field = decimal(min_value=0.0, max_value=10.0, precision=2)
        rng = random.Random(42)
        value = field.generate(rng)
        assert 0.0 <= value <= 10.0
        # Check precision
        str_val = str(value)
        if "." in str_val:
            decimals = len(str_val.split(".")[1])
            assert decimals <= 2


class TestMoneyField:
    """Tests for money() DSL function."""

    def test_money_returns_formatted_string(self) -> None:
        field = money(min_value=10.0, max_value=100.0)
        assert isinstance(field, MoneyField)
        rng = random.Random(42)
        value = field.generate(rng)
        assert value.startswith("$")
        # Check format $X.XX
        assert "." in value
        dollars, cents = value[1:].split(".")
        assert len(cents) == 2


class TestDateField:
    """Tests for date_field() DSL function."""

    def test_date_field_default(self) -> None:
        field = date_field()
        assert isinstance(field, DateField)
        assert field.min_year == 2000
        assert field.max_year == 2025

    def test_date_field_custom_format(self) -> None:
        field = date_field(format="%m/%d/%Y")
        assert field.format == "%m/%d/%Y"

    def test_date_field_generate(self) -> None:
        field = date_field(min_year=2020, max_year=2020, format="%Y-%m-%d")
        rng = random.Random(42)
        value = field.generate(rng)
        assert value.startswith("2020-")


class TestTimeField:
    """Tests for time_field() DSL function."""

    def test_time_field_default(self) -> None:
        field = time_field()
        assert isinstance(field, TimeField)

    def test_time_field_generate(self) -> None:
        field = time_field(min_hour=9, max_hour=17)
        rng = random.Random(42)
        value = field.generate(rng)
        assert isinstance(value, str)
        # Should contain AM or PM
        assert "AM" in value or "PM" in value


class TestBooleanField:
    """Tests for boolean() DSL function."""

    def test_boolean_default_probability(self) -> None:
        field = boolean()
        assert isinstance(field, BoolField)
        assert field.probability == 0.5

    def test_boolean_custom_probability(self) -> None:
        field = boolean(probability=0.9)
        assert field.probability == 0.9

    def test_boolean_generate(self) -> None:
        field = boolean(probability=1.0)
        rng = random.Random(42)
        assert field.generate(rng) is True

        field = boolean(probability=0.0)
        assert field.generate(rng) is False


class TestChoiceField:
    """Tests for choice() DSL function."""

    def test_choice_basic(self) -> None:
        field = choice("a", "b", "c")
        assert isinstance(field, ChoiceField)
        assert field.choices == ["a", "b", "c"]

    def test_choice_with_weights(self) -> None:
        field = choice("rare", "common", weights=[0.1, 0.9])
        assert field.weights == [0.1, 0.9]

    def test_choice_generate(self) -> None:
        field = choice("x", "y", "z")
        rng = random.Random(42)
        value = field.generate(rng)
        assert value in ["x", "y", "z"]

    def test_choice_empty_raises(self) -> None:
        field = ChoiceField(choices=[])
        rng = random.Random(42)
        with pytest.raises(ValueError):
            field.generate(rng)


class TestListField:
    """Tests for list_of() DSL function."""

    def test_list_of_basic(self) -> None:
        inner = string(faker="first_name")
        field = list_of(inner, min_items=2, max_items=5)
        assert isinstance(field, ListField)
        assert field.min_items == 2
        assert field.max_items == 5

    def test_list_of_generate(self) -> None:
        inner = integer(min_value=1, max_value=10)
        field = list_of(inner, min_items=3, max_items=3)
        rng = random.Random(42)
        value = field.generate(rng)
        assert isinstance(value, list)
        assert len(value) == 3
        for item in value:
            assert 1 <= item <= 10


class TestComputedField:
    """Tests for computed() and years_since() DSL functions."""

    def test_computed_concat(self) -> None:
        field = computed("first_name", "last_name")
        assert isinstance(field, ComputedField)
        assert field.sources == ("first_name", "last_name")
        assert field.formula == "concat"

    def test_years_since(self) -> None:
        field = years_since("dob")
        assert field.sources == ("dob",)
        assert field.formula == "years_since"


class TestRelationships:
    """Tests for relationship DSL functions."""

    def test_has_many(self) -> None:
        rel = has_many("Appointment", min_count=1, max_count=5)
        assert isinstance(rel, HasManyRel)
        assert rel.model == "Appointment"
        assert rel.min_count == 1
        assert rel.max_count == 5

    def test_belongs_to(self) -> None:
        rel = belongs_to("Patient")
        assert isinstance(rel, BelongsToRel)
        assert rel.model == "Patient"

    def test_has_one(self) -> None:
        rel = has_one("Provider")
        assert isinstance(rel, HasOneRel)
        assert rel.model == "Provider"

    def test_inferred_foreign_key(self) -> None:
        rel = has_many("AppointmentNote")
        assert rel.inferred_foreign_key() == "appointment_note_id"

    def test_explicit_foreign_key(self) -> None:
        rel = belongs_to("Provider", foreign_key="treating_provider_id")
        assert rel.inferred_foreign_key() == "treating_provider_id"


class TestModel:
    """Tests for Model base class."""

    def test_model_generate(self) -> None:
        rng = random.Random(42)
        patient = Patient.generate(rng)
        assert isinstance(patient, Patient)
        assert patient.first_name
        assert patient.last_name
        assert patient.dob

    def test_model_computed_fields(self) -> None:
        rng = random.Random(42)
        patient = Patient.generate(rng)
        # full_name should be computed from first + last
        assert patient.full_name == f"{patient.first_name} {patient.last_name}"

    def test_model_to_dict(self) -> None:
        rng = random.Random(42)
        patient = Patient.generate(rng)
        d = patient.to_dict()
        assert isinstance(d, dict)
        assert "first_name" in d
        assert "last_name" in d
        assert "full_name" in d

    def test_custom_model(self) -> None:
        class TestPerson(Model):
            name = string(faker="first_name")
            age = integer(min_value=18, max_value=65)
            active = boolean(probability=0.8)

        rng = random.Random(42)
        person = TestPerson.generate(rng)
        assert isinstance(person.name, str)
        assert 18 <= person.age <= 65
        assert isinstance(person.active, bool)

    def test_provider_generate(self) -> None:
        rng = random.Random(42)
        provider = Provider.generate(rng)
        assert provider.npi
        assert len(provider.npi) == 10
        assert provider.specialty


class TestFakers:
    """Tests for built-in faker types."""

    def test_faker_phone(self) -> None:
        field = string(faker="phone")
        rng = random.Random(42)
        value = field.generate(rng)
        assert "(" in value and ")" in value and "-" in value

    def test_faker_email(self) -> None:
        field = string(faker="email")
        rng = random.Random(42)
        value = field.generate(rng)
        assert "@" in value
        assert "." in value

    def test_faker_ssn(self) -> None:
        field = string(faker="ssn")
        rng = random.Random(42)
        value = field.generate(rng)
        parts = value.split("-")
        assert len(parts) == 3

    def test_faker_npi(self) -> None:
        field = string(faker="npi")
        rng = random.Random(42)
        value = field.generate(rng)
        assert len(value) == 10
        assert value.isdigit()

    def test_faker_street(self) -> None:
        field = string(faker="street")
        rng = random.Random(42)
        value = field.generate(rng)
        assert any(s in value for s in ["St", "Ave", "Blvd", "Dr", "Ln", "Rd", "Way", "Ct", "Pl"])

    def test_faker_unknown_raises(self) -> None:
        field = string(faker="unknown_faker")
        rng = random.Random(42)
        with pytest.raises(ValueError, match="Unknown faker"):
            field.generate(rng)


class TestAttributeDSL:
    """Tests for attribute() DSL function."""

    def test_attribute_string(self) -> None:
        from cudag.core.models import attribute, _pending_attributes

        # Clear any pending attributes
        _pending_attributes.clear()

        # Register an attribute
        attribute("username", "string", faker="first_name")

        assert len(_pending_attributes) == 1
        name, field = _pending_attributes[0]
        assert name == "username"
        assert isinstance(field, StringField)
        assert field.faker == "first_name"

        _pending_attributes.clear()

    def test_attribute_integer(self) -> None:
        from cudag.core.models import attribute, _pending_attributes

        _pending_attributes.clear()

        attribute("age", "integer", min_value=18, max_value=100)

        assert len(_pending_attributes) == 1
        name, field = _pending_attributes[0]
        assert name == "age"
        assert isinstance(field, IntField)
        assert field.min_value == 18
        assert field.max_value == 100

        _pending_attributes.clear()

    def test_attribute_date(self) -> None:
        from cudag.core.models import attribute, _pending_attributes

        _pending_attributes.clear()

        attribute("birth_date", "date", min_year=1950, max_year=2000)

        assert len(_pending_attributes) == 1
        name, field = _pending_attributes[0]
        assert name == "birth_date"
        assert isinstance(field, DateField)
        assert field.min_year == 1950
        assert field.max_year == 2000

        _pending_attributes.clear()

    def test_attribute_semantic_types(self) -> None:
        from cudag.core.models import attribute, _pending_attributes

        _pending_attributes.clear()

        attribute("first", "first_name")
        attribute("last", "last_name")
        attribute("dob", "dob")
        attribute("npi", "npi")
        attribute("phone", "phone")
        attribute("email", "email")

        assert len(_pending_attributes) == 6

        # first_name is a StringField with faker="first_name"
        name, field = _pending_attributes[0]
        assert name == "first"
        assert isinstance(field, StringField)

        _pending_attributes.clear()

    def test_attribute_invalid_type_raises(self) -> None:
        from cudag.core.models import attribute, _pending_attributes

        _pending_attributes.clear()

        with pytest.raises(ValueError, match="Unknown field type"):
            attribute("foo", "unknown_type")

        _pending_attributes.clear()


class TestModelGenerator:
    """Tests for ModelGenerator class."""

    def test_generator_one(self) -> None:
        from cudag.core.models import ModelGenerator

        gen = ModelGenerator(Patient, random.Random(42))
        patient = gen.one()

        assert isinstance(patient, Patient)
        assert patient.first_name
        assert patient.last_name

    def test_generator_many(self) -> None:
        from cudag.core.models import ModelGenerator

        gen = ModelGenerator(Patient, random.Random(42))
        patients = gen.many(5)

        assert len(patients) == 5
        for p in patients:
            assert isinstance(p, Patient)

    def test_model_generator_factory(self) -> None:
        gen = Patient.generator(random.Random(42))
        patient = gen.one()

        assert isinstance(patient, Patient)

    def test_generate_many_class_method(self) -> None:
        patients = Patient.generate_many(3, random.Random(42))

        assert len(patients) == 3
        for p in patients:
            assert isinstance(p, Patient)

    def test_generator_uses_same_rng(self) -> None:
        from cudag.core.models import ModelGenerator

        # Same seed should produce same results
        gen1 = ModelGenerator(Patient, random.Random(42))
        gen2 = ModelGenerator(Patient, random.Random(42))

        p1 = gen1.one()
        p2 = gen2.one()

        assert p1.first_name == p2.first_name
        assert p1.last_name == p2.last_name

    def test_generator_iteration(self) -> None:
        gen = Patient.generator(random.Random(42))

        # Generate several in sequence
        first = gen.one()
        second = gen.one()

        # They should be different instances
        assert first is not second


class TestSemanticFieldTypes:
    """Tests for semantic field type functions."""

    def test_first_name(self) -> None:
        from cudag.core.models import FirstName

        field = FirstName()
        assert isinstance(field, StringField)
        rng = random.Random(42)
        value = field.generate(rng)
        assert isinstance(value, str)
        assert len(value) > 0

    def test_last_name(self) -> None:
        from cudag.core.models import LastName

        field = LastName()
        assert isinstance(field, StringField)
        rng = random.Random(42)
        value = field.generate(rng)
        assert isinstance(value, str)

    def test_npi(self) -> None:
        from cudag.core.models import NPI

        field = NPI()
        rng = random.Random(42)
        value = field.generate(rng)
        assert len(value) == 10
        assert value.isdigit()

    def test_phone(self) -> None:
        from cudag.core.models import Phone

        field = Phone()
        rng = random.Random(42)
        value = field.generate(rng)
        assert "(" in value and ")" in value

    def test_email(self) -> None:
        from cudag.core.models import Email

        field = Email()
        rng = random.Random(42)
        value = field.generate(rng)
        assert "@" in value

    def test_ssn(self) -> None:
        from cudag.core.models import SSN

        field = SSN()
        rng = random.Random(42)
        value = field.generate(rng)
        assert value.count("-") == 2

    def test_dob(self) -> None:
        from cudag.core.models import DOB

        field = DOB()
        rng = random.Random(42)
        value = field.generate(rng)
        # Should be in MM/DD/YYYY format
        parts = value.split("/")
        assert len(parts) == 3

    def test_full_name(self) -> None:
        from cudag.core.models import FullName

        field = FullName()
        # FullName uses faker, not computed
        assert isinstance(field, StringField)
        assert field.faker == "full_name"

    def test_street(self) -> None:
        from cudag.core.models import Street

        field = Street()
        rng = random.Random(42)
        value = field.generate(rng)
        assert isinstance(value, str)
        assert len(value) > 0

    def test_city(self) -> None:
        from cudag.core.models import City

        field = City()
        rng = random.Random(42)
        value = field.generate(rng)
        assert isinstance(value, str)

    def test_state(self) -> None:
        from cudag.core.models import State

        field = State()
        rng = random.Random(42)
        value = field.generate(rng)
        assert len(value) == 2  # Two-letter state code

    def test_zip_code(self) -> None:
        from cudag.core.models import ZipCode

        field = ZipCode()
        rng = random.Random(42)
        value = field.generate(rng)
        assert len(value) == 5
        assert value.isdigit()
