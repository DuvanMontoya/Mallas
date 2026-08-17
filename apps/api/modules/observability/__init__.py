"""Operational telemetry primitives for the API.

This module intentionally has no Django models.  Telemetry is process-local by
default and can be exported through OpenTelemetry when an OTLP collector is
configured.  It must never become a second source of academic truth.
"""
