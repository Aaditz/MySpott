"""Database models. Importing them here makes sure the app knows about every table."""

from .user import User

__all__ = ["User"]