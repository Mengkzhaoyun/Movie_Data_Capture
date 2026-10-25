import dlib
import numpy as np
from PIL import Image

_hog_detector = None


def _get_hog_detector():
    global _hog_detector
    if _hog_detector is None:
        _hog_detector = dlib.get_frontal_face_detector()
    return _hog_detector


def face_center(filename, model):
    image = np.array(Image.open(filename).convert('RGB'))
    detector = _get_hog_detector()
    img_height, img_width = image.shape[:2]
    face_locations = [
        (
            max(rect.top(), 0),
            min(rect.right(), img_width),
            min(rect.bottom(), img_height),
            max(rect.left(), 0),
        )
        for rect in detector(image, 1)
    ]
    print('[+]Found person      [' + str(len(face_locations)) + ']      By model hog')
    maxRight = 0
    maxTop = 0
    for face_location in face_locations:
        top, right, bottom, left = face_location
        # 中心点
        x = int((right+left)/2)
        if x > maxRight:
            maxRight = x
            maxTop = top
    return maxRight,maxTop
