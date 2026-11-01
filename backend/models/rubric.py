from dataclasses import dataclass, field
from typing import List

from models.criterion import Criterion
from models.co import CO


@dataclass
class Rubric:
    title: str = ""
    course_code: str = ""
    course_name: str = ""

    criteria: List[Criterion] = field(default_factory=list)
    course_outcomes: List[CO] = field(default_factory=list)