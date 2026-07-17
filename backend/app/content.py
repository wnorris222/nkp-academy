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


@dataclass(frozen=True)
class Flashcard:
    """One study card. Purpose-written to teach, not derived from a question."""

    id: str
    kind: str  # term | concept | command | fact
    front: str
    back: str
    detail: str = ""
    code: str = ""
    ref: str = ""  # where to read more, e.g. "NKP 2.17 Guide · p.18"


@dataclass(frozen=True)
class FlashcardDeck:
    id: str
    title: str
    icon: str
    order: int
    summary: str
    cards: tuple[Flashcard, ...]


@dataclass
class ContentStore:
    """In-memory index of all loaded content."""

    modules: tuple[Module, ...] = field(default_factory=tuple)
    badges: tuple[Badge, ...] = field(default_factory=tuple)
    flashcard_decks: tuple[FlashcardDeck, ...] = field(default_factory=tuple)

    def module(self, module_id: str) -> Module | None:
        return next((m for m in self.modules if m.id == module_id), None)

    def flashcard_deck(self, deck_id: str) -> FlashcardDeck | None:
        return next((d for d in self.flashcard_decks if d.id == deck_id), None)

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


def _parse_flashcard(raw: dict) -> Flashcard:
    """Build a card, deriving the human-readable doc reference from page/section."""
    bits = []
    if raw.get("page"):
        page = str(raw["page"])
        bits.append(page if page.lower().startswith("p.") else f"p.{page}")
    if raw.get("section"):
        bits.append(str(raw["section"]))
    ref = "NKP 2.17 Guide · " + " · ".join(bits) if bits else ""

    return Flashcard(
        id=raw["id"],
        kind=raw.get("kind", "concept"),
        front=raw["front"],
        back=raw["back"],
        detail=raw.get("detail", "") or "",
        code=(raw.get("code", "") or "").rstrip("\n"),
        ref=ref,
    )


def _parse_flashcard_deck(raw: dict) -> FlashcardDeck:
    return FlashcardDeck(
        id=raw["id"],
        title=raw["title"],
        icon=raw.get("icon", "book"),
        order=int(raw.get("order", 0)),
        summary=raw.get("summary", ""),
        cards=tuple(_parse_flashcard(c) for c in raw.get("cards", [])),
    )


def load_content(content_dir: Path) -> ContentStore:
    """Load modules from ``<content_dir>/modules``, plus badges and flashcards.

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

    # Flashcard decks are optional — the quiz works without them.
    decks: list[FlashcardDeck] = []
    flashcards_dir = content_dir / "flashcards"
    if flashcards_dir.is_dir():
        for path in sorted(flashcards_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if data:
                decks.append(_parse_flashcard_deck(data))
        decks.sort(key=lambda d: (d.order, d.id))

    return ContentStore(
        modules=tuple(modules),
        badges=tuple(badges),
        flashcard_decks=tuple(decks),
    )
