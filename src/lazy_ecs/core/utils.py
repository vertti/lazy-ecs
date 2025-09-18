"""Utility functions for lazy-ecs."""

from __future__ import annotations


def extract_name_from_arn(arn: str) -> str:
    """Extract resource name from AWS ARN."""
    return arn.split("/")[-1]


def determine_service_status(running_count: int, desired_count: int, pending_count: int) -> tuple[str, str]:
    """Determine service status icon and text."""
    if running_count == desired_count and pending_count == 0:
        return "✅", "HEALTHY"
    if running_count < desired_count:
        return "⚠️", "SCALING"
    if running_count > desired_count:
        return "🔴", "OVER_SCALED"
    return "🟡", "PENDING"
