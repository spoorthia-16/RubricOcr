import os
from pdf2image import convert_from_path

from config import POPPLER_PATH, TEMP_FOLDER


def pdf_to_images(pdf_path):

    os.makedirs(TEMP_FOLDER, exist_ok=True)

    pages = convert_from_path(
        pdf_path,
        dpi=400,
        poppler_path=POPPLER_PATH
    )

    image_paths = []

    for index, page in enumerate(pages):

        image_path = os.path.join(
            TEMP_FOLDER,
            f"page_{index + 1}.png"
        )

        page.save(image_path, "PNG")

        image_paths.append(image_path)

    return image_paths
