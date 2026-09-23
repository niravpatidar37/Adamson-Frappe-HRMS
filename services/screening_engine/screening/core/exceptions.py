"""Domain-level exceptions shared across services and API layers."""


class HRScreeningError(Exception):
    """Base class for all domain errors."""


class NotAuthorizedError(HRScreeningError):
    """Raised when a caller lacks permission for the requested tenant/job/resource."""


class NotFoundError(HRScreeningError):
    """Raised when a resource does not exist, or exists in another tenant.

    Deliberately conflated: a cross-tenant lookup must be indistinguishable
    from a missing record, or the API confirms which ids exist elsewhere.
    Denial WITHIN the caller's own tenant uses NotAuthorizedError (403),
    which leaks nothing across the tenant boundary.
    """


class ValidationFailedError(HRScreeningError):
    """Raised when input fails schema or business-rule validation."""


class UntrustedContentError(HRScreeningError):
    """Raised when uploaded content fails malware/type/signature checks."""


class ParserOutputInvalidError(HRScreeningError):
    """Raised when the resume parser returns invalid/unparseable JSON.

    Callers must route the affected application to manual review rather
    than silently rejecting the candidate (system-design.md, principle 8).
    """
