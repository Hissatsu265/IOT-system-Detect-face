import requests
import json
import random
import time
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from flask import Flask
from flask import render_template , request
from flask_cors import CORS, cross_origin
import tensorflow as tf
import argparse
import facenet
import os
import sys
import math
import pickle
import align.detect_face
import numpy as np
import cv2
import collections
from sklearn.svm import SVC
import base64
import matplotlib.pyplot as plt

from kafka import KafkaProducer
from kafka import KafkaConsumer

access_token = "icJhhFu0gyxOyYAVG69n"
url = f"http://172.31.11.215:8080/api/v1/LsnleSLtCI6DSxCqCx7L/telemetry"
index=0

MINSIZE = 20
THRESHOLD = [0.6, 0.7, 0.7]
FACTOR = 0.709
IMAGE_SIZE = 182
INPUT_IMAGE_SIZE = 160
CLASSIFIER_PATH = 'Models/facemodel.pkl'
FACENET_MODEL_PATH = './Models/20180402-114759.pb'
def detect_faces(frame):
    bounding_boxes, _ = align.detect_face.detect_face(frame, MINSIZE, pnet, rnet, onet, THRESHOLD, FACTOR)
    faces_found = bounding_boxes.shape[0]
    faces = []

    if faces_found > 0:
        det = bounding_boxes[:, 0:4]
        bb = np.zeros((faces_found, 4), dtype=np.int32)
        for i in range(faces_found):
            bb[i][0] = det[i][0]
            bb[i][1] = det[i][1]
            bb[i][2] = det[i][2]
            bb[i][3] = det[i][3]
            cropped = frame
            scaled = cv2.resize(cropped, (INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE), interpolation=cv2.INTER_CUBIC)
            scaled = facenet.prewhiten(scaled)
            scaled_reshape = scaled.reshape(-1, INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE, 3)
            feed_dict = {images_placeholder: scaled_reshape, phase_train_placeholder: False}
            emb_array = sess.run(embeddings, feed_dict=feed_dict)
            faces.append(emb_array)

    return faces

def Send(name, roomID):
    data = {
        "name":name,
        "RoomID":roomID,
    }

    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print("Dữ liệu đã được gửi thành công!")
    else:
        print(f"Gửi dữ liệu thất bại. Status code: {response.status_code}")
        print(response.text)
# ======================================================================================
with open(CLASSIFIER_PATH, 'rb') as file:
    model, class_names = pickle.load(file)
print("Custom Classifier, Successfully loaded")

with tf.Graph().as_default():
    # Set up GPU if available
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

# ==================================================================================================
topic_name = "send_image"
c = KafkaConsumer(
    topic_name,
    bootstrap_servers = ["172.31.11.215"],
    auto_offset_reset = 'latest',
    enable_auto_commit = True
)
p = KafkaProducer(
    bootstrap_servers=["172.31.11.215:9092"],
    max_request_size = 9000000,
)

for message in c:
    image_data = message.value
    print("Start Recognizing...!")
    print("=============================================================================")
    frame = np.frombuffer(message.value, dtype=np.uint8).reshape((100, 100, 3))
    faces = detect_faces(frame)
    if len(faces) > 0:
        embeddings = np.concatenate(faces, axis=0)
        predictions = model.predict_proba(embeddings)
        best_class_indices = np.argmax(predictions, axis=1)
        best_class_probabilities = predictions[np.arange(len(best_class_indices)), best_class_indices]
        best_name = class_names[best_class_indices[0]]
        if(best_name=='hung'):
            best_name='Nguyễn Đức Thụy Hưng'
            best_name1='Nguyen Duc Thuy Hung'
        elif(best_name=='luan'):
            best_name='Nguyễn Thành Luân'
            best_name1='Nguyen Thanh Luan'
        elif (best_name=='toan'):
            best_name1='Le Minh Toan'
            best_name='Lê Minh Toàn'

        p.send(topic_name,best_name1)
        p.flush() 
        print("Name: {}, Probability: {}".format(best_name, best_class_probabilities))
        print("=============================================================================")
        print("Tiến hành gửi lên Thingsboard")
        Send(best_name,"E3.1")
        print("Done")


