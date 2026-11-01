from dataclasses import dataclass


@dataclass
class Criterion:
    name: str
    max_marks: float = 0
    obtained_marks: float = 0