from fps import FPS
from webcam import WebcamVideoStream
from inferencehelper import InferenceHelper
from drawinghelper import DrawingHelper
from imutils.video import VideoStream
from flask import Flask, render_template, session, request, Response, \
    copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, \
  	close_room, rooms, disconnect
import threading
from threading import Lock
import logging
import argparse
import time
from queue import Queue
import cv2
from flask_socketio import SocketIO, emit

# begin by pip installing flask_socketio following Miguel's instructions: https://blog.miguelgrinberg.com/post/easy-websockets-with-flask-and-gevent

#This will become our flask-socketio server

async_mode = None

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
drawn_frame = None
frame_data = None
lock = threading.Lock()

#initialise flask object
app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode) #socketio decorator
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

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("Server")

# Spawning the relevant threads
logger.info("Starting webcam thread")
webcam_thread = WebcamVideoStream(src=0).start()
fps = FPS().start()

logger.info("Starting inference thread")
INFERENCE_API = ""
inference_thread = InferenceHelper(INFERENCE_API).start()

logger.info("Starting drawing thread")
drawing_thread = DrawingHelper(webcam_thread.VID_WIDTH, webcam_thread.VID_HEIGHT).start()

# Run until quit.

# define a new function that we're going to run on a seperate thread:

def detect_motion():
	# grab global references to the output frame and lock variables
	global drawn_frame
	global frame_data

	# loop over frames from the output stream
	while True:
		frame = webcam_thread.read()
		frame_name = "./output/frame{}.jpg".format(fps.current_frame_number())

		# if cv2.waitKey(1) & 0xFF == ord('q'):
		# 	break
		# elif cv2.waitKey(1) & 0xFF == ord('c'):
		# # 	# Press c to restart the drawing thread to clear the screen.
		# 	drawing_thread = DrawingHelper(webcam_thread.VID_WIDTH, webcam_thread.VID_HEIGHT).stop()
		# 	drawing_thread = DrawingHelper(webcam_thread.VID_WIDTH, webcam_thread.VID_HEIGHT).start()

		# Queue up a new frame for inference every time the queue is empty.
		# This prevents the inference thread being queued with every single frame
		if inference_thread.queue.empty():
			inference_thread.enqueue({'name': frame_name, 'frame': frame, 'type': 'inference_queued'})

		# Everytime the inference thread processes a frame it returns the json_resp
		# This then adds the frame and json_resp to the drawing thread queue.
		drawing_thread.enqueue({'frame': frame, 'json_resp': inference_thread.json_resp})

		# The update function returns the drawn frame data which is then displayed on the screen.
		drawn_frame = drawing_thread.update()
		frame_data = inference_thread.json_resp
		try:
			frame_data[0]['label']
			logger.info(frame_data[0]['label'])
			socketio.emit('my_response',
                   	{'data': frame_data[0]['label']},
                   	namespace='/test')
		except:
			print("error")

		#write another socket.emit function that listens for when a letter is rendered to the screen. 

		#cv2.imshow("ASL Demo", drawn_frame)

		# # Press q to break the loop, and terminate the cv2 window.

				# update the FPS counter
		fps.update()
		#logger.info(frame_data)
		# wait until the lock is acquired
		#with lock:
			# check if the output frame is available, otherwise skip
			# the iteration of the loop

def generate():
	while True:
		#logger.info("wow")
		if drawn_frame is None:
			continue
			logger.info("nothing")
			# encode the frame in JPEG format
		(flag, encodedImage) = cv2.imencode(".jpg", drawn_frame)

			# ensure the frame was successfully encoded
		if not flag:
			continue
			logger.info("something")

		# yield the output frame in the byte format
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
			bytearray(encodedImage) + b'\r\n')

# def hello():
# 	while True:
# 		#logger.info("wow")
# 		if drawn_frame is None:
# 			continue
# 			#logger.info("nothing")
# 			# encode the frame in JPEG format
#
# 		logger.info(frame_data)

	# 	return frame_data
	# # yield "hello"

@app.route("/video_feed")
def video_feed():
	# return the response generated along with the specific media
	# type (mime type)
	return Response(generate(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

# @app.route("/letter")
# def letter():
# # if inference is returning something then ...
# 	return Response(hello())

# 	return Response(())

# @app.route("/dialogue")
# def dialogue():
# 	x="7"
# 	y="4"
# 	return Response(x=x, y=y)

# check to see if this is the main thread of execution
if __name__ == '__main__':
	#construct the argument parser and parse command line arguments
	# ap = argparse.ArgumentParser()
	# ap.add_argument("-i", "--ip", type=str, required=True,
	# 	help="ip address of the device")
	# ap.add_argument("-o", "--port", type=int, required=True,
	# 	help="ephemeral port number of the server (1024 to 65535)")
	# ap.add_argument("-f", "--frame-count", type=int, default=32,
	# 	help="# of frames used to construct the background model")
	# args = vars(ap.parse_args())

	t = threading.Thread(target=detect_motion,)
	t.daemon = True
	logger.info("started draw thread")
	t.start()

	# app.run(host=args["ip"], port=args["port"], debug=True,
	# 			threaded=True, use_reloader=False)
	app.run(host="0.0.0.0", port="8002", debug=True, threaded=True, use_reloader=False)
	# socketio.run(app, host="0.0.0.0", port="8001")
	 # does accept host and port arguments but I dont know how so just
	# navigate to localhost:5000 where it's listening on default


# while(True):
	# frame = webcam_thread.read()
	# frame_name = "./output/frame{}.jpg".format(fps.current_frame_number())
	#
	# # Queue up a new frame for inference every time the queue is empty.
	# # This prevents the inference thread being queued with every single frame
	# if inference_thread.queue.empty():
	# 	inference_thread.enqueue({'name': frame_name, 'frame': frame, 'type': 'inference_queued'})
	#
	# # Everytime the inference thread processes a frame it returns the json_resp
	# # This then adds the frame and json_resp to the drawing thread queue.
	# drawing_thread.enqueue({'frame': frame, 'json_resp': inference_thread.json_resp})
	#
	# # The update function returns the drawn frame data which is then displayed on the screen.
	# drawn_frame = drawing_thread.update()
	# cv2.imshow("ASL Demo", drawn_frame)
	#
	# # Press q to break the loop, and terminate the cv2 window.
	# if cv2.waitKey(1) & 0xFF == ord('q'):
	# 	break
	# elif cv2.waitKey(1) & 0xFF == ord('c'):
	# 	# Press c to restart the drawing thread to clear the screen.
	# 	drawing_thread = DrawingHelper(webcam_thread.VID_WIDTH, webcam_thread.VID_HEIGHT).stop()
	# 	drawing_thread = DrawingHelper(webcam_thread.VID_WIDTH, webcam_thread.VID_HEIGHT).start()
	# 		# update the FPS counter
	# fps.update()
	# logger.info("drawing")
fps.stop()
#logger.info("Camera FPS: {}".format(fps.end_to_end_fps()))

# Cleaning up the windows
webcam_thread.stop()
cv2.destroyAllWindows()
