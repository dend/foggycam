"""FoggyCam captures Nest camera images and generates a video."""

import pickle
import tempfile
import urllib
import json
from http.cookiejar import CookieJar
import os
from collections import defaultdict
import traceback
from subprocess import Popen, PIPE
import uuid
import threading
import time
import shlex
from datetime import datetime
try:
    from azurestorageprovider import AzureStorageProvider
    has_azure = True
except Exception:
    has_azure = False
import shutil


class FoggyCam(object):
    """FoggyCam client class that performs capture operations."""


    nest_username = ''
    nest_password = ''

    nest_user_id = ''
    nest_access_token = ''
    nest_access_token_expiration = ''
    nest_current_user = None

    nest_session_url = 'https://home.nest.com/session'
    nest_user_url = 'https://home.nest.com/api/0.1/user/{USERID}/app_launch'
    nest_api_login_url = 'https://webapi.camera.home.nest.com/api/v1/' +\
        'login.login_nest'
    nest_image_url = 'https://nexusapi-us1.camera.home.nest.com/' +\
        'get_image?uuid={CAMERAID}&width={WIDTH}&cachebuster={CBUSTER}'
    nest_verify_pin_url = 'https://home.nest.com/api/0.1/2fa/verify_pin'

    nest_user_request_payload = {
        "known_bucket_types": ["quartz"],
        "known_bucket_versions": []
    }

    nest_camera_array = []
    nest_camera_buffer_threshold = 50

    is_capturing = False

    def __init__(self, username, password):
        self.nest_password = password
        self.nest_username = username
        self.cookie_jar = CookieJar()
        self.merlin = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar))

        if not os.path.exists('_temp'):
            os.makedirs('_temp')

        self.local_path = os.getcwd()
        self.temp_dir_path = tempfile.mkdtemp()

        # It's important to try and load the cookies first to check
        # if we can avoid logging in.
        try:
            self.unpickle_cookies()

            utc_date = datetime.utcnow()
            utc_millis_str = str(int(utc_date.timestamp())*1000)
            self.initialize_twof_session(utc_millis_str)
        except Exception:
            print("Failed to re-use the cookies. Re-initializing session...")
            self.initialize_session()

        self.login()
        self.initialize_user()

    def unpickle_cookies(self):
        """Get local cookies and load them into the cookie jar."""

        print("Unpickling cookies...")
        with open("cookies.bin", 'rb') as f:
            pickled_cookies = pickle.load(f)

            for pickled_cookie in pickled_cookies:
                self.cookie_jar.set_cookie(pickled_cookie)

            cookie_data = dict((cookie.name, cookie.value)
                               for cookie in self.cookie_jar)

            self.nest_access_token = cookie_data["cztoken"]

    def pickle_cookies(self):
        """Store the cookies locally to reduce auth calls."""

        print("Pickling cookies...")
        pickle.dump([c for c in self.cookie_jar], open("cookies.bin", "wb"))

    def initialize_twof_session(self, time_token):
        """Creates the first session to get the access token and cookie,
           with 2FA enabled."""

        print("Intializing 2FA session...")

        target_url = self.nest_session_url + "?=_" + time_token
        print(target_url)

        try:
            request = urllib.request.Request(target_url)
            request.add_header('Authorization', 'Basic %s' %
                               self.nest_access_token)

            response = self.merlin.open(request)
            session_data = response.read()

            session_json = json.loads(session_data)

            self.nest_access_token = session_json['access_token']
            self.nest_access_token_expiration = session_json['expires_in']
            self.nest_user_id = session_json['userid']

            self.pickle_cookies()
        except urllib.request.HTTPError as err:
            print(err)

    def initialize_session(self):
        """Creates the first session to get the access token and cookie."""

        print('INFO: Initializing session...')

        payload = {'email': self.nest_username, 'password': self.nest_password}
        binary_data = json.dumps(payload).encode('utf-8')

        request = urllib.request.Request(self.nest_session_url, binary_data)
        request.add_header('Content-Type', 'application/json')

        try:
            response = self.merlin.open(request)
            session_data = response.read()
            session_json = json.loads(session_data)

            self.nest_access_token = session_json['access_token']
            self.nest_access_token_expiration = session_json['expires_in']
            self.nest_user_id = session_json['userid']

            print('INFO: [PARSED] Captured authentication token:')
            print(self.nest_access_token)

            print('INFO: [PARSED] Captured expiration date for token:')
            print(self.nest_access_token_expiration)

            cookie_data = dict((cookie.name, cookie.value)
                               for cookie in self.cookie_jar)
            for cookie in cookie_data:
                print(cookie)

            print('INFO: [COOKIE] Captured authentication token:')
            print(cookie_data["cztoken"])
        except urllib.request.HTTPError as err:
            if err.code == 401:
                error_message = err.read()
                unauth_content = json.loads(error_message)

                if unauth_content["status"].lower() == "verification_pending":
                    print("Pending 2FA verification!")

                    two_factor_token = unauth_content["2fa_token"]
                    phone_truncated = unauth_content["truncated_phone_number"]

                    print("Enter PIN you just received on number ending with",
                          phone_truncated)
                    pin = input()

                    payload = {"pin": pin, "2fa_token": two_factor_token}
                    binary_data = json.dumps(payload).encode('utf-8')

                    request = urllib.request.Request(
                        self.nest_verify_pin_url, binary_data)
                    request.add_header('Content-Type', 'application/json')

                    try:
                        response = self.merlin.open(request)
                        pin_attempt = response.read()

                        parsed_pin_attempt = json.loads(pin_attempt)
                        if parsed_pin_attempt["status"].lower() == \
                                "id_match_positive":
                            print("2FA verification successful.")

                            utc_date = datetime.utcnow()
                            utc_millis_str = str(
                                int(utc_date.timestamp())*1000)

                            print("Targetting new session with timestamp: ",
                                  utc_millis_str)

                            cookie_data = dict((cookie.name, cookie.value)
                                               for cookie in self.cookie_jar)

                            print(
                                'INFO: [COOKIE] Captured authentication token:'
                            )
                            print(cookie_data["cztoken"])

                            self.nest_access_token = \
                                parsed_pin_attempt['access_token']

                            self.initialize_twof_session(utc_millis_str)
                        else:
                            print("Could not verify. Exiting...")
                            exit()

                    except Exception:
                        traceback.print_exc()

                        print("Failed 2FA checks. Exiting...")
                        exit()

        print('INFO: Session initialization complete!')

    def login(self):
        """Performs user login to get the website_2 cookie."""

        print('INFO: Performing user login...')

        post_data = {'access_token': self.nest_access_token}
        post_data = urllib.parse.urlencode(post_data)
        binary_data = post_data.encode('utf-8')

        print("INFO: Auth post data")
        print(post_data)

        request = urllib.request.Request(
            self.nest_api_login_url, data=binary_data)
        request.add_header('Content-Type', 'application/x-www-form-urlencoded')

        response = self.merlin.open(request)
        session_data = response.read()

        print(session_data)

    def initialize_user(self):
        """Gets the assets belonging to Nest user."""

        print('INFO: Initializing current user...')

        user_url = self.nest_user_url.format(USERID=self.nest_user_id)

        print('INFO: Requesting user data from:')
        print(user_url)

        binary_data = json.dumps(
            self.nest_user_request_payload).encode('utf-8')

        request = urllib.request.Request(user_url, binary_data)

        request.add_header('Content-Type', 'application/json')
        request.add_header('Authorization', 'Basic %s' %
                           self.nest_access_token)

        response = self.merlin.open(request)

        response_data = response.read()

        print(response_data)

        user_object = json.loads(response_data)
        for bucket in user_object['updated_buckets']:
            bucket_id = bucket['object_key']
            if bucket_id.startswith('quartz.'):
                camera_id = bucket_id.replace('quartz.', '')
                print('INFO: Detected camera configuration.')
                print(bucket)
                print('INFO: Camera UUID:')
                print(camera_id)
                self.nest_camera_array.append(camera_id)

    def capture_images(self, config=None):
        """Starts the multi-threaded image capture process."""

        print('INFO: Capturing images...')

        self.capture_rate = config.capture_rate
        self.is_capturing = True

        if not os.path.exists('capture'):
            os.makedirs('capture')

        self.nest_camera_buffer_threshold = config.threshold

        for camera in self.nest_camera_array:
            # Determine whether the entries should be copied to a custom path
            # or not.
            if not config.path:
                self.camera_path = os.path.join(
                    self.local_path, 'capture', camera, 'images')
                self.video_path = os.path.join(
                    self.local_path, 'capture', camera, 'video')
            else:
                self.camera_path = os.path.join(
                    config.path, 'capture', camera, 'images')
                self.video_path = os.path.join(
                    config.path, 'capture', camera, 'video')

            # Provision the necessary folders for images and videos.
            if not os.path.exists(self.camera_path):
                os.makedirs(self.camera_path)

            if not os.path.exists(self.video_path):
                os.makedirs(self.video_path)

            image_thread = threading.Thread(target=self.perform_capture, args=(
                config, camera, self.camera_path, self.video_path))
            image_thread.daemon = True
            image_thread.start()

        while True:
            time.sleep(1)

    def perform_capture(self, 
                        config=None,
                        camera=None,
                        camera_path=None,
                        video_path=None):
        """Captures images and generates the video from them."""

        if camera_path is None:
            camera_path = self.camera_path
        if video_path is None:
            video_path = self.video_path
        camera_buffer = defaultdict(list)
        camera_timestamps_buffer = defaultdict(list)

        while self.is_capturing:
            print("New pic")
            file_id = str(uuid.uuid4().hex)

            utc_date = datetime.utcnow()
            utc_millis_str = str(int(utc_date.timestamp())*1000)

            print('Applied cache buster: ', utc_millis_str)

            image_url = self.nest_image_url.format(CAMERAID=camera,
                                                   CBUSTER=utc_millis_str,
                                                   WIDTH=config.width)

            request = urllib.request.Request(image_url)
            request.add_header(
                'accept', 'image/webp,image/apng,image/*,*/*;q=0.9')
            request.add_header('accept-encoding', 'gzip, deflate, br')
            request.add_header(
                'user-agent',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) ' +
                'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                'Chrome/66.0.3359.181 Safari/537.36')
            request.add_header('referer', 'https://home.nest.com/')
            request.add_header(
                'authority', 'nexusapi-us1.camera.home.nest.com')

            try:
                response = self.merlin.open(request)
                time.sleep(self.capture_rate)

                with open(os.path.join(camera_path, file_id + '.jpg'), 'wb')\
                        as image_file:
                    for chunk in response:
                        image_file.write(chunk)

                # Check if we need to compile a video
                if config.produce_video:
                    camera_buffer_size = len(camera_buffer[camera])
                    print('[ {} ] INFO: Camera buffer size for {} : {}'.format(
                          threading.current_thread().name,
                          camera,
                          camera_buffer_size))

                    if camera_buffer_size < self.nest_camera_buffer_threshold:
                        camera_buffer[camera].append(file_id)
                        timestamp = time.strftime("%Y-%m-%d %H\:%M\:%S",time.localtime())
                        camera_timestamps_buffer[camera].append(timestamp)
                    else:
                        # Build the batch of files that need
                        # to be made into a video.
                        file_declaration = ''
                        ffmpeg_text='-vf "'

                        for buffer_entry in camera_buffer[camera]:
                            # FFMPEG needs absolute paths
                            file_declaration += " file '{}.jpg'\n".format(
                                os.path.abspath(os.path.join(camera_path,
                                                             buffer_entry)))
                        ffmpeg_tmpl = "drawtext=text='{}':x=5:y={}:fontfile={}:fontsize={}:fontcolor={}:borderw=3:bordercolor=black:box=0:enable='between(t,{},{})', "
                        font_file = "/Volumes/Devel/git/matplotlib/lib/matplotlib/mpl-data/fonts/ttf/Vera.ttf"
                        font_color = "white"
                        font_size = 24
                        buf_time = camera_buffer_size * config.capture_rate  # in seconds
                        mov_time = camera_buffer_size / config.frame_rate # in seconds
                        ratio = mov_time / buf_time
                        for i, timestamp in enumerate(camera_timestamps_buffer[camera]):
                            start = i * config.capture_rate * ratio
                            #  Not quite 1 to avoid overlap
                            end = (i + .999) * config.capture_rate * ratio
                            last_time = timestamp.replace("\\:", "-")
                            last_time = last_time.replace(" ", "_")
                            print("ACTUAL :",start, end, last_time)
                            text = ffmpeg_tmpl.format(timestamp, font_size+1, font_file, font_size, font_color, start, end)
                            ffmpeg_text += text

                        ffmpeg_text = ffmpeg_text[:-2]+'"'
                        concat_file_name = os.path.join(
                            camera_path, camera + '.txt')

                        # Make sure that the content is decoded

                        with open(concat_file_name, 'w') as declaration_file:
                            declaration_file.write(file_declaration)

                        # Check if we have ffmpeg locally
                        use_terminal = False
                        ffmpeg_path = ''

                        if shutil.which("ffmpeg"):
                            ffmpeg_path = 'ffmpeg'
                            use_terminal = True
                        else:
                            ffmpeg_path = os.path.abspath(os.path.join(
                                os.path.dirname(__file__), '..', 'tools',
                                'ffmpeg'))

                        if use_terminal or (os.path.isfile(ffmpeg_path)
                                            and
                                            use_terminal is False):
                            print('INFO: Found ffmpeg. Processing video!')
                            target_video_path = os.path.join(
                                video_path, last_time + '.mp4')
                            cmd = "{} -r {} -f concat -safe 0 -i {} " +\
                                "-vcodec libx264 -preset veryslow -pix_fmt yuv420p "
                            cmd = cmd.format(ffmpeg_path,
                                             config.frame_rate,
                                             concat_file_name)
                            cmd += ffmpeg_text + " " + target_video_path
                            print("INFO: FFMPEG command:", cmd)
                            process = Popen(shlex.split(
                                cmd), stdout=PIPE, stderr=PIPE)
                            out, err = process.communicate()
                            # os.remove(concat_file_name)
                            print('INFO: Video processing is complete!')
                            print("INFO: FFMPEG OUT:", out)
                            print("INFO: FFMPEG ERROR:", err)

                            # Upload the video
                            if has_azure:
                                storage_provider = AzureStorageProvider()

                                if bool(config.upload_to_azure):
                                    print('INFO: Upload to Azure Storage...')
                                    file_name = file_id + ".mp4"
                                    target_blob = os.path.join("foggycam",
                                                               camera,
                                                               file_name)
                                    storage_provider.upload_video(
                                        account_name=config.az_account_name,
                                        sas_token=config.az_sas_token,
                                        container='foggycam',
                                        blob=target_blob,
                                        path=target_video_path)
                                    print('INFO: Upload complete.')

                            # If the user specified the need to remove images
                            #  post-processing then clear the image folder
                            #  from images in the buffer.
                            if config.clear_images:
                                for buffer_entry in camera_buffer[camera]:
                                    deletion_target = os.path.join(
                                        camera_path, buffer_entry + '.jpg')
                                    print('INFO: Deleting ' + deletion_target)
                                    os.remove(deletion_target)
                            print("Done with video")
                        else:
                            print(
                                'WARNING: No ffmpeg detected.' +
                                ' Make sure the binary is in /tools.')
                        # Empty buffer,
                        # since we no longer need the file records
                        # that we're planning to compile in a video.
                        camera_buffer[camera] = []
                        camera_timestamps_buffer[camera] = []
            except urllib.request.HTTPError as err:
                print("403")
                if err.code == 403:
                    self.initialize_session()
                    self.login()
                    self.initialize_user()
            except Exception:
                print('ERROR: Could not download image from URL:')
                print(image_url)

                traceback.print_exc()
