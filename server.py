from fps import FPS
from webcam import WebcamVideoStream
from inferencehelper import InferenceHelper
from drawinghelper import DrawingHelper
from imutils.video import VideoStream
from flask import Flask, render_template, session, request, Response, \
    copy_current_request_context
import threading
import numpy as np
from threading import Lock
import logging
import argparse
import time
from queue import Queue
import cv2
from flask_socketio import SocketIO, emit



def similarity_factor(sim_list):
	sim_np = np.subtract(sim_list[0],sim_list[1])
	sim_np = np.absolute(sim_np)
	return np.mean(sim_np)

def threshold(sim_thresh_list):
	'''This functions is to calculate the similarity threshold'''
	for k in range(32):
		if k > 1:
			frame = webcam_thread.read()
			sim_thresh_list.append(frame)
			time.sleep(0.2)
			similarity = similarity_factor(sim_thresh_list)
			sim_bucket.append(similarity)
			del sim_thresh_list[0]
	
	sim_mean = np.mean(np.asarray(sim_bucket))
	sim_std = np.std(sim_bucket)
	return sim_mean + 1.75*sim_std

def save_file(frame):
	cv2.iwrite()
	pass

async_mode = None

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
drawn_frame = None
frame_data = None
lock = threading.Lock()

#initialise flask object
app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()
#from app import routes

@app.route("/")
def index():
	# return the rendered template
	return render_template("index.html", async_mode=socketio.async_mode)
	#return render_template("index.html")

# below are event handlers, they allow app to recieve messages from the client
#data is passed to the client through either send() [for sending standards messages of string
# or JSON] and emit() [for sending message under custom event name]

# @socketio.on('my event', namespace='/test') #here we're defining the event - allows for multiple connections to the server multiplexed on a single socket
# def test_message(message):
#     emit('my response', {'data': message['data']}) #message event delivers a string payload
# you can also send JSON rather than string
#
# @socketio.on('my broadcast event', namespace='/test')
# def test_message(message):
#     emit('my response', {'data': message['data']}, broadcast=True)
#
# @socketio.on('connect', namespace='/test')
# def test_connect():
#     emit('my response', {'data': 'Connected'})
#
# @socketio.on('disconnect', namespace='/test')
# def test_disconnect():
#     print('Client disconnected')

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger("Server")

# Spawning the relevant threads
#logger.info("Starting webcam thread")
# webcam_thread = WebcamVideoStream(src=0).start()
webcam_thread = WebcamVideoStream(src=1).start()
fps = FPS().start()

#logger.info("Starting inference thread")
INFERENCE_API = ""
inference_thread = InferenceHelper(INFERENCE_API).start()

#logger.info("Starting drawing thread")
drawing_thread = DrawingHelper(webcam_thread.VID_WIDTH, webcam_thread.VID_HEIGHT).start()

# Run until quit.

# define a new function that we're going to run on a seperate thread:

frame = webcam_thread.read()
frame_name = "./output/frame{}.jpg".format(fps.current_frame_number())
similarity_list = [frame]


"""Need to be tested"""
sim_bucket = []
sim_thresh_list = [frame]
sim_threshold = threshold(sim_thresh_list)
print("threshold: ", sim_threshold)


# Everytime the inference thread processes a frame it returns the json_resp
# This then adds the frame and json_resp to the drawing thread queue.

if inference_thread.queue.empty():
    inference_thread.enqueue({'name': frame_name, 'frame': frame, 'type': 'inference_queued'})

drawing_thread.enqueue({'frame': frame, 'json_resp': inference_thread.json_resp})
drawn_frame, json_resp = drawing_thread.update()

def detect_motion():
	# grab global references to the output frame
    global drawn_frame
    global frame_data
    global frame_name
    global frame
    global json_resp

    while True:

        frame = webcam_thread.read()
        frame_name = "./output/frame{}.jpg".format(fps.current_frame_number())
        similarity_list.append(frame)
        time.sleep(0.2)
        similarity = similarity_factor(similarity_list)

    	#print(fps.current_frame_number(), similarity)
    	# cv2.imwrite(frame_name, frame)

        del similarity_list[0]
        print(similarity)

        if similarity < sim_threshold: # Check if image is stable.

            drawn_frame = drawing_thread.draw_bounding_box(json_resp, frame) #return new json_resp and pass to websocket
            new_frame = cv2.resize(drawn_frame, (1285, 690))
            try:
                # inference_thread.json_resp[0]['label']
                socketio.emit('my_response',
                        {'data': json_resp},
                        namespace='/test')
                # fps.update()
            except:
                print("nothing")

            # logger.info(json_resp)
    		#print(similarity)

        else: #if not, send image for inferencing
    		#print(similarity)
    		#frame = webcam_thread.read()
            if inference_thread.queue.empty():
                inference_thread.enqueue({'name': frame_name, 'frame': frame, 'type': 'inference_queued'})

            drawing_thread.enqueue({'frame': frame, 'json_resp': inference_thread.json_resp})

            drawn_frame, json_resp = drawing_thread.update()
            frame_data = inference_thread.json_resp
            # logger.info("here")
            #logger.info(frame_data.count('epithelial'))

        fps.update()


def generate():
	while True:
		#logger.info("wow")
		if drawn_frame is None:
			continue
			#logger.info("nothing")
			# encode the frame in JPEG format
		(flag, encodedImage) = cv2.imencode(".jpg", drawn_frame)

			# ensure the frame was successfully encoded
		if not flag:
			continue
			#logger.info("something")

		# yield the output frame in the byte format
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
			bytearray(encodedImage) + b'\r\n')


@app.route("/video_feed")
def video_feed():
	# return the response generated along with the specific media
	# type (mime type)
	return Response(generate(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

if __name__ == '__main__':

	t = threading.Thread(target=detect_motion,)
	t.daemon = True
	#logger.info("started draw thread")
	t.start()
	app.run(host="0.0.0.0", port="8002", debug=True, threaded=True, use_reloader=False)
	# socketio.run(app, host="0.0.0.0", port="8001")

fps.stop()

webcam_thread.stop()
cv2.destroyAllWindows()
