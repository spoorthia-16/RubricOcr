from services.parsers.assessment_parser import parse_assessment
from services.parsers.matrix_parser import parse_matrix
from services.parsers.generic_parser import parse_generic


def select_parser(text):

    lower_text = text.lower()

    if "examiner" in lower_text and "assessment" in lower_text:
        return parse_assessment

    elif "excellent" in lower_text and "good" in lower_text:
        return parse_matrix

    else:
        return parse_generic
