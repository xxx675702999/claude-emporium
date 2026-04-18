"""Pipeline-wide typed errors for fail-fast contract enforcement.

Every DeltaValidationError subclass surfaces at the apply-delta.py boundary
as exit code 1 with the error message on stderr. The existing
state-manager.py recovery flow listens for non-zero exit codes and retries
settlement once with the error as feedback.
"""


class DeltaValidationError(Exception):
    """Base: delta.json failed contract validation. apply-delta exits 1."""


class HookIdFormatError(DeltaValidationError):
    """A hookId does not match the required pattern ^H\\d+(_\\d+)?$."""


class HookStatusEnumError(DeltaValidationError):
    """A hook status value is not in VALID_HOOK_STATUSES."""


class ResourceLedgerFieldError(DeltaValidationError):
    """A resourceLedgerOp is missing required fields or has an invalid op."""


class PredicateAliasError(DeltaValidationError):
    """current_state.json contains both zh and en forms of the same predicate."""
