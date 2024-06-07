from __future__ import absolute_import, division, print_function

import tensorflow as tf
import facenet
import os
import math
import pickle
import align.detect_face
import numpy as np
import cv2
import collections
from sklearn.svm import SVC
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt

MINSIZE = 20
THRESHOLD = [0.6, 0.7, 0.7]
FACTOR = 0.709
IMAGE_SIZE = 182
INPUT_IMAGE_SIZE = 160
CLASSIFIER_PATH = 'Models/facemodel.pkl'
FACENET_MODEL_PATH = './Models/20180402-114759.pb'
DATASET_PATH = 'D:\source\Dataset\\test'  # Path to the dataset folder

# Load the Custom Classifier
with open(CLASSIFIER_PATH, 'rb') as file:
    model, class_names = pickle.load(file)
print("Custom Classifier, Successfully loaded")

with tf.Graph().as_default():
    gpu_options = tf.compat.v1.GPUOptions(per_process_gpu_memory_fraction=0.6)
    sess = tf.compat.v1.Session(config=tf.compat.v1.ConfigProto(gpu_options=gpu_options, log_device_placement=False))

    with sess.as_default():
        # Load the model
        print('Loading feature extraction model')
        facenet.load_model(FACENET_MODEL_PATH)

        images_placeholder = tf.compat.v1.get_default_graph().get_tensor_by_name("input:0")
        embeddings = tf.compat.v1.get_default_graph().get_tensor_by_name("embeddings:0")
        phase_train_placeholder = tf.compat.v1.get_default_graph().get_tensor_by_name("phase_train:0")
        embedding_size = embeddings.get_shape()[1]

        pnet, rnet, onet = align.detect_face.create_mtcnn(sess, "src/align")

        true_labels = []
        pred_labels = []

        for class_folder in os.listdir(DATASET_PATH):
            class_folder_path = os.path.join(DATASET_PATH, class_folder)
            if os.path.isdir(class_folder_path):
                for image_name in os.listdir(class_folder_path):
                    image_path = os.path.join(class_folder_path, image_name)
                    frame = cv2.imread(image_path)

                    bounding_boxes, _ = align.detect_face.detect_face(frame, MINSIZE, pnet, rnet, onet, THRESHOLD, FACTOR)
                    faces_found = bounding_boxes.shape[0]

                    if faces_found > 0:
                        det = bounding_boxes[:, 0:4]
                        for i in range(faces_found):
                            bb = np.zeros((faces_found, 4), dtype=np.int32)
                            bb[i][0] = det[i][0]
                            bb[i][1] = det[i][1]
                            bb[i][2] = det[i][2]
                            bb[i][3] = det[i][3]
                            cropped = frame[bb[i][1]:bb[i][3], bb[i][0]:bb[i][2], :]
                            scaled = cv2.resize(cropped, (INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE),
                                                interpolation=cv2.INTER_CUBIC)
                            scaled = facenet.prewhiten(scaled)
                            scaled_reshape = scaled.reshape(-1, INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE, 3)
                            feed_dict = {images_placeholder: scaled_reshape, phase_train_placeholder: False}
                            emb_array = sess.run(embeddings, feed_dict=feed_dict)
                            predictions = model.predict_proba(emb_array)
                            best_class_indices = np.argmax(predictions, axis=1)
                            best_class_probabilities = predictions[
                                np.arange(len(best_class_indices)), best_class_indices]
                            best_name = class_names[best_class_indices[0]]

                            true_labels.append(class_folder)
                            if best_class_probabilities > 0.5:
                                pred_labels.append(best_name)
                            else:
                                pred_labels.append("Unknown")

        # Generate and print classification report
        report = classification_report(true_labels, pred_labels, target_names=class_names)
        print(report)
        print(true_labels)
        print(pred_labels)
