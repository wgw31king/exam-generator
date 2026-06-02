from dataclasses import dataclass, field


@dataclass
class Option:
    label: str
    text: str


@dataclass
class Question:
    type: str
    original_id: str
    stem: str
    options: list[Option] = field(default_factory=list)
    answer: str = ""


@dataclass
class Paper:
    single: list[Question] = field(default_factory=list)
    multiple: list[Question] = field(default_factory=list)
    judge: list[Question] = field(default_factory=list)
    short: list[Question] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
