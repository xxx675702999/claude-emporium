"""Verify typed exception module exists and has expected hierarchy."""
from lib.pipeline_errors import (
    DeltaValidationError,
    HookIdFormatError,
    HookStatusEnumError,
    ResourceLedgerFieldError,
    PredicateAliasError,
)


def test_all_errors_inherit_from_delta_validation_error():
    for cls in (HookIdFormatError, HookStatusEnumError,
                ResourceLedgerFieldError, PredicateAliasError):
        assert issubclass(cls, DeltaValidationError), (
            f"{cls.__name__} must inherit from DeltaValidationError"
        )


def test_delta_validation_error_inherits_from_exception():
    assert issubclass(DeltaValidationError, Exception)


def test_errors_carry_messages():
    err = HookIdFormatError("bad id H15 (新增)")
    assert "bad id H15 (新增)" in str(err)
