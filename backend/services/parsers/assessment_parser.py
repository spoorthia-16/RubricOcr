import re

from models.co import CO
from models.rubric import Rubric
from models.criterion import Criterion


def normalize_text(text):

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if line:
            line = " ".join(line.split())
            lines.append(line)

    return lines


def split_columns(lines):
    """
    Split OCR lines separated by '|'
    into individual cleaned items.
    """

    cleaned_lines = []

    for line in lines:

        if "|" in line:

            parts = line.split("|")

            for part in parts:

                part = part.strip()

                if part:
                    cleaned_lines.append(part)

        else:
            cleaned_lines.append(line)

    return cleaned_lines


def merge_criteria_lines(lines):

    merged = []

    i = 0

    while i < len(lines):

        line = lines[i]

        # Case 1: Current line is only "(Max XX)"
        if line.startswith("(Max"):

            if merged:
                merged[-1] = merged[-1] + " " + line

            i += 1
            continue

        merged.append(line)

        i += 1

    return merged


def get_criteria_section(lines):

    criteria_lines = []

    start_collecting = False

    for line in lines:

        lower = line.lower()

        # Start after Student Details
        if "appearance" in lower:
            start_collecting = True

        if start_collecting:
            criteria_lines.append(line)

        # Stop before comments section
        if "comment" in lower:
            break

    return criteria_lines


def extract_criteria(lines, rubric):

    i = 0

    while i < len(lines):

        line = lines[i]

        # Skip non-criteria fields
        ignore = [
            "Learner name",
            "Student no.",
            "Comment",
            "Sub-Total",
            "Final Mark"
        ]

        if line in ignore:
            i += 1
            continue

        # Look ahead for Max marks
        if i + 1 < len(lines):

            next_line = lines[i + 1]

            match = re.search(
                r"Max\s*(\d+)",
                next_line,
                re.IGNORECASE
            )

            if match:

                rubric.criteria.append(
                    Criterion(
                        name=line,
                        max_marks=int(match.group(1))
                    )
                )

                i += 2
                continue

        i += 1

    return rubric


def extract_metadata(lines, rubric):
    for i, line in enumerate(lines):
        # Title
        if rubric.title == "":
            rubric.title = line

        # Course Code
        if rubric.course_code == "":
            match = re.search(r"\b[A-Za-z]{1,5}\d{3,5}\b", line)
            if match:
                rubric.course_code = match.group()
                if i + 1 < len(lines):
                    rubric.course_name = lines[i + 1]
    return rubric


def extract_course_outcomes(lines, rubric):
    for line in lines:
        if re.match(r"^CO\d+", line.upper()):
            rubric.course_outcomes.append(CO(code=line))
    return rubric


def parse_assessment(text):
    
    lines = normalize_text(text)
    lines = split_columns(lines)
    lines = merge_criteria_lines(lines)

    print("\n========== MERGED LINES ==========\n")
    for line in lines:
        print(line)
    print("\n=================================\n")

    rubric = Rubric()

    rubric = extract_metadata(lines, rubric)
    rubric = extract_course_outcomes(lines, rubric)
    
    # Get just the criteria lines so we don't accidentally parse metadata/body as criteria
    criteria_lines = get_criteria_section(lines)
    rubric = extract_criteria(criteria_lines, rubric)

    return rubric
