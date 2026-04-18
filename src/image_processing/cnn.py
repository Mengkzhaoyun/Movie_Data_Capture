import sys
sys.path.append('../')

from image_processing.hog import face_center as hog_face_center


def face_center(filename, model):
    return hog_face_center(filename, model)
