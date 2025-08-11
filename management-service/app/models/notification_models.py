"""
Notification models for the management service API
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Notification(BaseModel):
    """Individual notification"""
    id: str = Field(..., description="Unique notification ID")
    account_id: str = Field(..., description="Account ID")
    strategy_name: str = Field(..., description="Strategy name")
    event_type: str = Field(..., description="Event type")
    message: str = Field(..., description="Notification message")
    timestamp: datetime = Field(..., description="Timestamp when notification was created")
    status: str = Field(..., description="Status: 'new' or 'read'")
    markdown_body: str = Field(..., description="Detailed markdown body")


class NotificationsResponse(BaseModel):
    """Response for notifications list"""
    notifications: List[Notification] = Field(..., description="List of notifications")
    total: int = Field(..., description="Total number of notifications")
    has_more: bool = Field(..., description="Whether there are more notifications")


class UnreadCountResponse(BaseModel):
    """Response for unread count"""
    count: int = Field(..., description="Number of unread notifications")


class MarkReadResponse(BaseModel):
    """Response for marking notification as read"""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Result message")


class MarkAllReadResponse(BaseModel):
    """Response for marking all notifications as read"""
    success: bool = Field(..., description="Whether operation was successful")
    marked_count: int = Field(..., description="Number of notifications marked as read")
    message: str = Field(..., description="Result message")


class DeleteNotificationResponse(BaseModel):
    """Response for deleting a notification"""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Result message")