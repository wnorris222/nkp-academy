"""Prometheus metrics.

Exposes counters/histograms in the standard text exposition format at
``/metrics`` (wired up in :mod:`app.main`). NKP ships Prometheus as a platform
application, so these scrape cleanly once a ServiceMonitor/annotation is added.
"""
from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram

# A dedicated registry keeps the app's series isolated and test-friendly.
registry = CollectorRegistry()

http_requests_total = Counter(
    "nkp_academy_http_requests_total",
    "Total HTTP requests processed.",
    ["method", "path", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "nkp_academy_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
    registry=registry,
)

quiz_answers_total = Counter(
    "nkp_academy_quiz_answers_total",
    "Quiz answers submitted, partitioned by correctness.",
    ["result"],  # "correct" | "incorrect"
    registry=registry,
)

badges_awarded_total = Counter(
    "nkp_academy_badges_awarded_total",
    "Badges awarded to learners.",
    ["badge_id"],
    registry=registry,
)

logins_total = Counter(
    "nkp_academy_logins_total",
    "Login/session-start events.",
    registry=registry,
)

exams_submitted_total = Counter(
    "nkp_academy_exams_submitted_total",
    "Practice exams submitted, partitioned by pass/fail.",
    ["result"],  # "pass" | "fail"
    registry=registry,
)

flashcard_decks_served_total = Counter(
    "nkp_academy_flashcard_decks_served_total",
    "Flashcard decks served, partitioned by deck kind.",
    ["kind"],  # "all" | "track" | "module"
    registry=registry,
)
