class AusUtilException(Exception):
    """Base exception for aus-utils."""

    pass


class TwoFAException(AusUtilException):
    """Base exception for two-factor authentication related errors."""

    pass