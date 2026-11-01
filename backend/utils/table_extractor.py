import cv2
import os
import numpy as np


def detect_table(image_path):

    image = cv2.imread(image_path)

    if image is None:
        raise Exception("Cannot read image.")

    print(image.shape)

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    return image, gray

