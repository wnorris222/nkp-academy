"""Learning-content loader.

Content (modules, questions, badges) is authored as YAML under ``content/`` so
Nutanix can add or edit enablement material without touching code or the
database. This module parses those files into immutable dataclasses and exposes
a small in-memory :class:`ContentStore` for lookups.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

QuestionType = Literal["multiple_choice", "true_false", "scenario"]

# Correct answers must reference option ids; scenario "best answer" is still an
# option id but options may carry per-option feedback.


@dataclass(frozen=True)
class Option:
    id: str
    text: str
    feedback: str | None = None


@dataclass(frozen=True)
class Source:
    """A citation to the Nutanix docs so learners can verify the answer."""

    label: str
    url: str
    page: str = ""
    quote: str = ""
    # Optional second citation (some answers are documented across two pages).
    label2: str = ""
    url2: str = ""


@dataclass(frozen=True)
class Question:
    id: str
    type: QuestionType
    prompt: str
    options: tuple[Option, ...]
    correct: tuple[str, ...]  # one id for single-answer, many for multi
    explanation: str
    points: int = 10
    difficulty: str = "core"
    source: Source | None = None

    @property
    def correct_set(self) -> frozenset[str]:
        return frozenset(self.correct)


@dataclass(frozen=True)
class Module:
    id: str
    title: str
    track: str
    order: int
    summary: str
    icon: str
    questions: tuple[Question, ...]

    @property
    def total_points(self) -> int:
        return sum(q.points for q in self.questions)


@dataclass(frozen=True)
class Badge:
    id: str
    name: str
    description: str
    icon: str
    # Criteria: award when a module or track is completed, or an XP threshold.
    criteria_type: Literal["module_complete", "track_complete", "xp_threshold"]
    criteria_value: str  # module_id, track name, or XP integer (as string)


@dataclass
class ContentStore:
    """In-memory index of all loaded content."""

    modules: tuple[Module, ...] = field(default_factory=tuple)
    badges: tuple[Badge, ...] = field(default_factory=tuple)

    def module(self, module_id: str) -> Module | None:
        return next((m for m in self.modules if m.id == module_id), None)

    def question(self, module_id: str, question_id: str) -> Question | None:
        module = self.module(module_id)
        if not module:
            return None
        return next((q for q in module.questions if q.id == question_id), None)

    def tracks(self) -> list[str]:
        # Preserve first-seen order.
        seen: list[str] = []
        for m in self.modules:
            if m.track not in seen:
                seen.append(m.track)
        return seen

    def modules_in_track(self, track: str) -> list[Module]:
        return [m for m in self.modules if m.track == track]


def _parse_question(raw: dict) -> Question:
    options = tuple(
        Option(id=o["id"], text=o["text"], feedback=o.get("feedback"))
        for o in raw.get("options", [])
    )
    correct = raw["correct"]
    correct_tuple = tuple(correct) if isinstance(correct, list) else (correct,)

    src = raw.get("source")
    source = None
    if src and src.get("url"):
        source = Source(
            label=src.get("label", "Nutanix docs"),
            url=src["url"],
            page=src.get("page", ""),
            quote=src.get("quote", ""),
            label2=src.get("label2", ""),
            url2=src.get("url2", ""),
        )

    return Question(
        id=raw["id"],
        type=raw["type"],
        prompt=raw["prompt"],
        options=options,
        correct=tuple(str(c) for c in correct_tuple),
        explanation=raw.get("explanation", ""),
        points=int(raw.get("points", 10)),
        difficulty=raw.get("difficulty", "core"),
        source=source,
    )


def _parse_module(raw: dict) -> Module:
    questions = tuple(_parse_question(q) for q in raw.get("questions", []))
    return Module(
        id=raw["id"],
        title=raw["title"],
        track=raw.get("track", "NKP Fundamentals"),
        order=int(raw.get("order", 0)),
        summary=raw.get("summary", ""),
        icon=raw.get("icon", "book"),
        questions=questions,
    )


def load_content(content_dir: Path) -> ContentStore:
    """Load every ``*.yaml`` module from ``<content_dir>/modules`` plus badges.

    Raises ``FileNotFoundError`` if the content directory is missing so
    misconfiguration fails loudly at startup rather than serving an empty app.
    """
    content_dir = Path(content_dir)
    modules_dir = content_dir / "modules"
    if not modules_dir.is_dir():
        raise FileNotFoundError(f"Content modules directory not found: {modules_dir}")

    modules: list[Module] = []
    for path in sorted(modules_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data:
            modules.append(_parse_module(data))
    modules.sort(key=lambda m: (m.order, m.id))

    badges: list[Badge] = []
    badges_path = content_dir / "badges.yaml"
    if badges_path.is_file():
        data = yaml.safe_load(badges_path.read_text(encoding="utf-8")) or {}
        for raw in data.get("badges", []):
            badges.append(
                Badge(
                    id=raw["id"],
                    name=raw["name"],
                    description=raw.get("description", ""),
                    icon=raw.get("icon", "trophy"),
                    criteria_type=raw["criteria_type"],
                    criteria_value=str(raw["criteria_value"]),
                )
            )

    return ContentStore(modules=tuple(modules), badges=tuple(badges))
