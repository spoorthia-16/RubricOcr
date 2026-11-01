import re
import difflib


# -------------------------------------------------------
# Group OCR tokens into columns
# -------------------------------------------------------

def group_by_columns(tokens, tolerance=45):
    """
    Groups OCR tokens into vertical columns.

    Parameters
    ----------
    tokens : list[OCRToken]
    tolerance : int
        Maximum horizontal distance (pixels) for tokens
        to belong to the same column.
    """

    columns = []

    # Sort from left to right
    tokens = sorted(tokens, key=lambda t: t.left)

    for token in tokens:

        matched = False

        for column in columns:

            # Running average of LEFT coordinates
            avg_left = sum(t.left for t in column) / len(column)

            if abs(token.left - avg_left) <= tolerance:

                column.append(token)
                matched = True
                break

        if not matched:
            columns.append([token])

    # Sort each column top-to-bottom
    for column in columns:
        column.sort(key=lambda t: t.top)

    return columns


# -------------------------------------------------------
# Merge all tokens in one column
# -------------------------------------------------------

def merge_columns(columns):

    merged_headers = []

    for column in columns:

        words = []

        previous = ""

        for token in column:

            text = token.text.strip()

            if not text:
                continue

            # Remove duplicates
            if text == previous:
                continue

            previous = text

            # OCR often misses "("
            if text.startswith("Max") and not text.startswith("(Max"):
                text = "(" + text

            words.append(text)

        header = " ".join(words)

        merged_headers.append(header)

    return merged_headers


# -------------------------------------------------------
# Clean OCR mistakes
# -------------------------------------------------------

def clean_headers(headers):

    corrections = {

        "Learner name": "Learner name",

        "Student no.": "Student no.",

        "Sub Total": "Sub-Total",

        "SubTotal": "Sub-Total",

        "Sub-Total": "Sub-Total",

        "Sterilisation Hygiene &":
            "Hygiene & Sterilisation",

        "Hygiene & Sterilisation":
            "Hygiene & Sterilisation",

        "Skin analysis":
            "Skin analysis",

        "Eyelash tinting":
            "Eyelash tinting",

        "Eyebrow shape":
            "Eyebrow shape",

        "Home care advice":
            "Home care advice",

        "Final Mark":
            "Final Mark",

        "Client Care":
            "Client Care",

        "Appearance":
            "Appearance",

        "Massage":
            "Massage",

        "Mask":
            "Mask",

        "Cleanse":
            "Cleanse"

    }

    cleaned = []

    for header in headers:

        header = header.strip()

        # Remove multiple spaces
        header = re.sub(r"\s+", " ", header)

        # Fix missing '('
        header = header.replace("Max 5)", "(Max 5)")
        header = header.replace("Max 10)", "(Max 10)")
        header = header.replace("Max 100)", "(Max 100)")

        # Remove duplicate brackets
        header = header.replace("((Max", "(Max")

        # OCR sometimes gives ') )'
        header = header.replace("))", ")")

        # Fuzzy correction
        words = header.split()

        rebuilt = []

        for word in words:

            match = difflib.get_close_matches(
                word,
                corrections.keys(),
                n=1,
                cutoff=0.88
            )

            if match:
                rebuilt.append(corrections[match[0]])
            else:
                rebuilt.append(word)

        header = " ".join(rebuilt)

        # Final phrase replacements
        for wrong, right in corrections.items():

            if wrong in header:
                header = header.replace(wrong, right)

        cleaned.append(header)

    return cleaned