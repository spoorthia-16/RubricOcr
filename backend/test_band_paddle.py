import cv2
from paddleocr import PaddleOCR
import logging
logging.getLogger('ppocr').setLevel(logging.ERROR)

paddle_reader = PaddleOCR(use_angle_cls=True, lang='en')

band_path = "c:/Users/spoor/EXCEL works/Project1/backend/debug/test_band.png"
band_crop = cv2.imread(band_path)
pad = 15
padded_band = cv2.copyMakeBorder(band_crop, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
rotated_band = cv2.rotate(padded_band, cv2.ROTATE_90_CLOCKWISE)

band_result = paddle_reader.ocr(rotated_band)
print("BAND RESULT:", band_result)
