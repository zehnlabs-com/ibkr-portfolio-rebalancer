"""
Custom exceptions for Event Broker service
"""


class EventBrokerException(Exception):
    """Base exception for Event Broker service"""
    pass


class EventDeduplicationError(EventBrokerException):
    """Raised when event already exists in queue"""
    pass