from services.parsers.parser_selector import select_parser


def parse_rubric(text):

    parser = select_parser(text)

    return parser(text)