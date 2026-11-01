from dataclasses import dataclass

@dataclass
class OCRToken:

    text: str

    confidence: float

    x: float

    y: float

    left: float

    right: float

    top: float

    bottom: float
