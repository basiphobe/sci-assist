"""
Privacy management module for Discord LLM Bot.

This module provides GDPR-compliant data handling, retention policies,
and user consent management.
"""

from .manager import PrivacyManager, RetentionPolicy, UserConsent

__all__ = ['PrivacyManager', 'RetentionPolicy', 'UserConsent']
