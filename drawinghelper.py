# import the necessary packages
import os
import time
from threading import Thread
import requests
import json
from collections import deque

import numpy as np
import logging
import cv2
import queue


logger = logging.getLogger("DrawingHelper")

class DrawingHelper:
    def __init__(self, VID_HEIGHT, VID_WIDTH):

        # Thread management and queueing
        self.stopped = False
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.queue = queue.Queue()

        # Video dimensions
        self.VID_HEIGHT = VID_HEIGHT
        self.VID_WIDTH = VID_WIDTH

        # ASL
        # # Drawing constants
        # # Possibly replace with a namespace?
        # self.FONT = cv2.FONT_HERSHEY_SIMPLEX
        # self.FONT_SCALE = 1
        # self.THICKNESS = 1
        # self.FONT_COLOUR = (255,255,255)
        # self.BB_COLOUR = (255, 98, 0)   # IBM blue
        # self.BB_THICKNESS = 3
        # self.RECTANGLE_BACKGROUND = (0, 0, 0)
        # self.TEXT_HEIGHT = 75
        # self.TEXT_WIDTH = int(self.VID_HEIGHT*0.95)
        # self.WIDTH_FACTOR = 5
        #
        # # Letter tracking constants
        # # NOTE: Alot of these values are chosen through trial and error for
        # # a nice looking visual effect. Do not read too much into the values.
        # self.FRAME_THRESHOLD = 300  # This should be an even number.
        # self.WIDE_LETTER_LIST = ["g", "j", "k", "m", "u"]
        # self.WIDE_LETTER_FACTOR = 11
        # self.SLIM_LETTER_FACTOR = 7
        # self.MAX_LETTERS_TO_DISPLAY = 20
        #
        # # Letter tracking variables
        # self.letter_deque = deque(maxlen=self.FRAME_THRESHOLD)
        # self.constant_letter_count = 0
        # self.count_slim_letter = 0
        # self.count_wide_letter = 0
        # self.constant_letter_dict = {}

        # Drawing constants
        # Possibly replace with a namespace?
        self.FONT = cv2.FONT_HERSHEY_SIMPLEX
        self.FONT_SCALE = 0.2
        self.THICKNESS = 1
        self.BB_THICKNESS = 4
        self.FRAME_THRESHOLD = 600  # This should be an even number.

        # The different font and bbox colours- dependent on cell type.
        self.FONT_COLOUR_BLUE = (3, 83, 233)
        self.FONT_COLOUR_RED = (238, 83, 139)
        self.FONT_COLOUR_YELLOW = (105, 41, 196)

        self.BB_COLOUR_BLUE = (3, 83, 233)   # IBM blue
        self.BB_COLOUR_RED = (238, 83, 139)
        self.BB_COLOUR_YELLOW = (105, 41, 196)

        #nuclei labels
        self.cell_type_a = 'epithelial'
        self.cell_type_b = 'fibroblast'
        self.cell_type_c = 'lymphocyte'

        #confidence threshold
        self.confidence_thresh_a = 0.95
        self.confidence_thresh_b = 0.90
        self.confidence_thresh_c = 0.95

    def start(self):
        # start the thread to read frames from the queue
        self.thread.start()
        return self

    def enqueue(self, item):
        self.queue.put_nowait(item)

    def update(self):
        try:
            # keep looping infinitely until the thread is stopped
            while True:
                # if the thread indicator variable is set, stop the thread
                if self.stopped:
                    return

                try:
                    inferred_frame = self.queue.get(block=True)
                    json_resp = inferred_frame['json_resp']
                    frame_data = inferred_frame['frame']

                    if json_resp:
                        current_letter = json_resp[0]['label']
                    else:
                        current_letter = ''
                        json_resp = [{'xmin': 0, 'ymin': 0, 'xmax': 0, 'ymax': 0, 'confidence': 0, 'label': ''}]

                        frame_data = self.draw_bounding_box(json_resp, frame_data)

                    return frame_data, json_resp

                except queue.Empty:
                    logger.debug("Slept and nothing to do... Trying again.")
                    time.sleep(1)
                    continue

        except Exception as e:
            logger.error("Exception occurred = {}".format(e))

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True

    def draw_bounding_box(self, json_resp, image):
        x = "hello";
        for i in range(len(json_resp)):
            #apply confidence thresholds to json response then execute
            if (json_resp[i]['confidence'] >= self.confidence_thresh_a) & (json_resp[i]['confidence'] >= self.confidence_thresh_b) & (json_resp[i]['confidence'] >= self.confidence_thresh_c):

                #print('CONFIDENCE:', json_resp[i]['confidence'])

                x_max = json_resp[i]['xmax']
                y_max = json_resp[i]['ymax']

                x_min = json_resp[i]['xmin']
                y_min = json_resp[i]['ymin']

                #assign bounding box colours to each class
                if json_resp[i]['label'] == 'epithelial':
                    display_BB_colour = self.BB_COLOUR_BLUE

                elif json_resp[i]['label'] == 'fibroblast':
                    display_BB_colour = self.BB_COLOUR_RED

                elif json_resp[i]['label'] == 'lymphocyte':
                    display_BB_colour = self.BB_COLOUR_YELLOW

                else:

                    return(0)

                cv2.rectangle(image, (x_max,y_max), (x_min, y_min), display_BB_colour, self.BB_THICKNESS)

                #put text label on bounding box
                if json_resp[i]['label'] == 'epithelial':
                    display_label = self.cell_type_a

                elif json_resp[i]['label'] == 'fibroblast':
                    display_label = self.cell_type_b

                elif json_resp[i]['label'] == 'lymphocyte':
                    display_label = self.cell_type_c

                else:

                    return(0)

                #assign corresponding font colours to each class
                if json_resp[i]['label'] == 'epithelial':
                    font_colour = self.FONT_COLOUR_BLUE

                elif json_resp[i]['label'] == 'fibroblast':
                    font_colour = self.FONT_COLOUR_RED

                elif json_resp[i]['label'] == 'lymphocyte':
                    font_colour = self.FONT_COLOUR_YELLOW

                else:
                    return(0)


                cv2.putText(image, display_label, (x_min, y_min), self.FONT, 0.35, font_colour, lineType=cv2.LINE_AA)
            # else:
            #     try:
            #         json_resp.remove(json_resp[i])
            #     except:
            #         print("out of range")

        return image
