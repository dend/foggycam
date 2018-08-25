#!/usr/bin/env python

"""Module to start FoggyCam processing."""
import argparse
import json
import os
from collections import namedtuple
from foggycam import FoggyCam

print ('Welcome to FoggyCam 1.0 - Nest video/image capture tool')

parser = argparse.ArgumentParser("Utilities for NEST CAM")
parser.add_argument("-c", "--config", help="config file", default='config.json')
parser.add_argument("-u","--username", help="nest username", default=None)
parser.add_argument("-p", "--password", help="nest password", default=None)
parser.add_argument("-o", "--path", help="output path for images and videos", default=None)
parser.add_argument("-f","--frame-rate", help="frame rate", default=None)
parser.add_argument("-w","--width",help="image width (in pixel)", default=None)
parser.add_argument("-C","--clear-images", help="clean images after making the video", default=None)
parser.add_argument("-V","--video",help="Generate videos",default=None,action="store_true")
parser.add_argument("-U","--upload",help="Upload result to Azure",default=None)
parser.add_argument("--cloud_user",help="azure username", default=None)
parser.add_argument("--cloud_password",help="azure password", default=None)

args = parser.parse_args()
CONFIG_PATH = args.config

CONFIG = json.load(open(CONFIG_PATH))

for att in dir(args):
    if att[0] == "_":
        continue
    key = att
    if key == "cloud_user":
        key = "az_account_name"
    elif key == "cloud_password":
        key = "az_sas_token"
    elif key == "upload":
        key = "upload_to_azure"
    if getattr(args,att) is not None and key in CONFIG:
        CONFIG[key] = getattr(args,att)

CONFIG = namedtuple("X",CONFIG.keys())(*CONFIG.values())
CAM = FoggyCam(username=CONFIG.username, password=CONFIG.password)
CAM.capture_images(CONFIG)
