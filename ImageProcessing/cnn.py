from ImageProcessing.hog import face_center as hog_face_center
import sys
sys.path.append('../')


def face_center(filename, model):
    return hog_face_center(filename, model)
