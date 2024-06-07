import time
import subprocess
from kafka import KafkaProducer
import time
from kafka import KafkaConsumer

topic_name_re = "TEST"
c = KafkaConsumer(
    "result",
    bootstrap_servers = ["172.31.11.215"],
    auto_offset_reset = 'latest',
    enable_auto_commit = True
)

topic_name = "send_image"
p = KafkaProducer(
    bootstrap_servers=["172.31.11.215:9092"],
    max_request_size = 9000000,
)

def capture_image():
    subprocess.run(['sudo', 'raspistill', '-o', 'test.jpg'])
    # return

def send_image():
    with open('/home/pi/test.jpg', 'rb') as image_file:
        image_data = image_file.read()
        p.send(topic_name, image_data)
        p.flush() 

while True:
    print("bat dau chup hinh")
    capture_image()
    send_image()
    print("da gui anh")
    for message in c:
        if(message.value !=null):
            print("Nhận diện được: ", message.value)
            print("=============================================")
            break
    time.sleep(5)