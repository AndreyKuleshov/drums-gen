"""Domain-level auth errors, mapped to HTTP responses in the router."""


class AuthError(Exception):
    """Base class for auth failures."""


class InvalidCredentialsError(AuthError):
    """Email/password did not match."""


class EmailNotVerifiedError(AuthError):
    """The account exists but its email is not yet confirmed."""


class AccountBlockedError(AuthError):
    """An admin has blocked this account from signing in."""


class InvalidTokenError(AuthError):
    """A verification / reset token is unknown, consumed, or expired."""


class PasswordReusedError(AuthError):
    """The new password matches one of the user's recent passwords."""
