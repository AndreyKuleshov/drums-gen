"""Domain-level auth errors, mapped to HTTP responses in the router."""


class AuthError(Exception):
    """Base class for auth failures."""


class InvalidCredentialsError(AuthError):
    """Email/password did not match."""


class EmailNotVerifiedError(AuthError):
    """The account exists but its email is not yet confirmed."""


class InvalidTokenError(AuthError):
    """A verification / reset token is unknown, consumed, or expired."""
