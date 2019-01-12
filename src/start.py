"""Module to start FoggyCam processing."""

import json
import os
from collections import namedtuple
from foggycam import FoggyCam

print('Welcome to FoggyCam 1.0 - Nest video/image capture tool')

CONFIG_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        '..',
        'config.json'))
print(CONFIG_PATH)

CONFIG = json.load(
    open(CONFIG_PATH),
    object_hook=lambda d: namedtuple(
        'X',
        d.keys())(
            *d.values()))

CAM = FoggyCam(username=CONFIG.username, password=CONFIG.password)
CAM.capture_images(CONFIG)
