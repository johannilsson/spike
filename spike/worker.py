import sys
import os
import threading
import time
from datetime import datetime, timedelta
import settings
import shutil

import os
import boto
import boto.s3
import mimetypes

from boto.s3.bucket import Bucket
from boto.s3.key import Key

import requests

import logging
import logging.handlers


#import errno
#import fnmatch
#import codecs
#import re
#import hashlib
#import socket
#import filecmp
#from unicodedata import normalize
#from functools import partial

logger = logging.getLogger('spike')
logger.setLevel(settings.LOG_LEVEL)

class Config(object):
    storage_conn = None

config = Config()

try:
    _stdout, _stderr = sys.stdout.write, sys.stderr.write
except IOError:
    _stdout = lambda x: sys.stdout.write(x)
    _stderr = lambda x: sys.stderr.write(x)


def mkdir_p(path):
    """ Create intermediate directories as required.
    """
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise

class ResourceMonitor(threading.Thread):
    """ Monitor resources for changes.

    Example usage.

    >>> def onchange(paths):
    ...   print 'changed', paths
    ... 
    >>> ResourceMonitor(['.'], onchange).start()
    """
    def __init__(self, paths, onchange):
        threading.Thread.__init__(self)
        self.daemon = True
        self.paths = paths
        self.onchange = onchange
        self.modified_paths =  {}

    def remove_paths(self, paths):
        to_remove = [p for p in self.modified_paths if p in paths]
        for p in to_remove:
            try:
                del self.modified_paths[p]
            except KeyError, e:
                _stderr('\n ** Could not remove "{0}" from monitored files\n'.format(watched_path))

    def diff(self, path):
        """ Check for modifications returns a dict of paths and times of change.
        """
        modified_paths = {}
        for root, dirs, files in os.walk(path, topdown=True):
            for f in files:
                path = os.path.join(root, f)
                try:
                    modified = os.stat(path).st_mtime
                except Exception, e:
                    continue
                if path not in self.modified_paths or self.modified_paths[path] != modified:
                    modified_paths[path] = modified
        return modified_paths

    def _diffall(self):
        """ Run diff through all paths.
        """
        modified_paths = {}
        for p in self.paths:
            modified_paths.update(self.diff(p))
        return modified_paths

    def run(self):
        """ Starts monitoring, onchange is called if an resource is modified.
        """
        self.modified_paths = self._diffall()
        while True:
            modified_paths = self._diffall()
            if modified_paths:
                self.modified_paths.update(modified_paths)
                self.onchange(self, modified_paths)
            time.sleep(0.5)


def _move_to_processing(key):
    logger.debug('Move {0} from TODO to IN PROGRESS'.format(key))
    status = False
    try:
        shutil.move(
            settings.WORK_TODO_DIR + os.sep + key,
            settings.WORK_PROCESSING_DIR + os.sep + key
        )
        status = True
    except Exception, e:
        logger.info('Could move directory {0} from TODO to IN PROGRESS, {1}'.format(key, e))
        _stderr('E')
    return status


def _handle_process(key):
    logger.debug('Handle upload of "{0}"'.format(key))

    upload_failed = False
    try:
        _upload_directory_to_storage(config.storage_conn, settings.WORK_PROCESSING_DIR + os.sep + key, settings.AWS_BUCKET)
    except Exception, e:
        logger.warning('Upload of "{0}" failed: {1}'.format(key, e))
        _stderr('E')
        upload_failed = True
    else:
        # Only ack if manged to upload all files.
        r = requests.get(settings.API_ACK_ENDPOINT + '?key=' + key, auth=(settings.API_USER, settings.API_PASSWORD))

    #_stderr('Response from API {0}'.format(r.status_code))
    logger.info('API Response status code for key "{0}": "{1}"'.format(key, r.status_code))

    move_to = settings.WORK_DONE_DIR
    if upload_failed:
        # If we failed to upload, move files back to the todo directory.
        move_to = settings.WORK_TODO_DIR

    # Move to done.
    if os.path.exists(move_to + os.sep + key):
        for root, dirs, files in os.walk(settings.WORK_PROCESSING_DIR + os.sep + key, topdown=True):
            for f in files:
                path = os.path.join(root, f)
                try:
                    shutil.copy(path, move_to+ os.sep + key + os.sep + f)
                except shutil.Error, e:
                    _stderr('E')
                    logger.warning('Failed to copy "{0}" from IN PROGRESS to DONE {0}: {1}'.format(f, e))
        try:
            shutil.rmtree(settings.WORK_PROCESSING_DIR + os.sep + key)
        except Exception, e:
            logger.warning('Could not remove "{0}" from IN PROGRESS {0}: {1}'.format(key, e))
            _stderr('E')
    else:
        try:
            shutil.move(
                settings.WORK_PROCESSING_DIR + os.sep + key,
                move_to + os.sep # TODO: maybe + key here.
            )
        except Exception, e:
            logger.warning('Could not move "{0}" from IN PROGRESS to DONE {0}: {1}'.format(key, e))
            _stderr('E')

    # return status so we dont get stuck in a loop with on change eventd.

def _upload_to_storage(conn, filename, bucket_name, is_logs=False):

    logger.debug('Init upload to storage for {0}'.format(filename))

    b = Bucket(conn, bucket_name)
    k = Key(b)
    key = filename.replace(settings.WORK_PROCESSING_DIR, '')
    # Hack for uploading logs, maybe they should be moved to processing and done dir too.
    if is_logs:
        key = filename.replace(os.path.dirname(settings.LOG_FILENAME), '')
    # TODO: Check if theres any sanitizer.
    key = key.replace('\\', '/')

    k.key = key
    type, encoding = mimetypes.guess_type(filename)

    if type is None:
        type = 'text/plain'

    expires = datetime.utcnow() + timedelta(days=(25 * 365))
    expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
    k.set_metadata('Expires', expires)
    k.set_metadata("Content-Type", type)

    k.set_contents_from_filename(filename)
    k.set_acl("public-read")

    logger.debug('Upload done {0}'.format(key))
    _stderr('U')


def _upload_directory_to_storage(conn, foldername, bucket_name, is_logs=False):
    for filename in os.listdir(foldername):
        root, ext = os.path.splitext(filename)
        if ext in ['.jpg', '.JPG', '.png', '.gif', '.json'] or "logs" in bucket_name:
            _upload_to_storage(conn, foldername + os.sep + filename, bucket_name, is_logs)
        elif filename != settings.WORK_DONE_MARKER and not filename.startswith('.'):
            logger.info('Unknown extension ignoring upload "{0}"'.format(filename))
            _stderr('E')

def upload_logs():
    _stderr('L')
    upload_failed = False
    bucket_name = settings.AWS_LOG_BUCKET
    try:
        _upload_directory_to_storage(config.storage_conn, os.path.dirname(settings.LOG_FILENAME), bucket_name, is_logs=True)
    except Exception, e:
        logger.warning('Upload of "logs" failed: {0}'.format(e))
        _stderr('E')
        upload_failed = True
    else:
        _stderr('S')


def recover():
    ''' Try to recover from a bad state.

    Check if we have anything in todo with a marker.
    Check if we have anything stuck in progress.

    Process from each state and aim to get everything to done.
    '''
    _stderr('R')

    # Check done.
    for root, dirs, files in os.walk(settings.WORK_TODO_DIR, topdown=True):
        for f in files:
            path = os.path.join(root, f)
            file_name = os.path.basename(path)
            if file_name == settings.WORK_DONE_MARKER:
                key = os.path.basename(os.path.dirname(path))
                upload(key)
                # We're not removing files from the monitor here, but it has not started yet. so no worries.

    # Check in progress
    # For all dirs we find here, force them into process state.
    for root, dirs, files in os.walk(settings.WORK_PROCESSING_DIR, topdown=True):
        for d in dirs:
            _handle_process(d)

def upload(key):
    ''' Process upload on the supplied key.
    '''
    logger.debug('Init upload of {0}'.format(key))
    if _move_to_processing(key):
        _handle_process(key)
        logger.info('Upload finished {0}'.format(key))
    else:
        logger.warning('Failed to upload {0}'.format(key))
        _stderr('E')


def watch():
    ''' Start monitor.
    '''
    recover()

    logger.info('Starting monitoring of {0}'.format(settings.WORK_TODO_DIR))
    _stderr('W')

    paths = [settings.WORK_TODO_DIR]

    monitor = ResourceMonitor(paths, onchange)
    monitor.start()

    try:
        while True:
            _stderr('.')
            time.sleep(2)
    except KeyboardInterrupt, e:
        _stderr(" ** Bye **")


def init():
    _stderr('I')

    config.storage_conn = boto.connect_s3(
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY
    )

    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler = logging.handlers.RotatingFileHandler(
                  settings.LOG_FILENAME, maxBytes=10485760, backupCount=5)
    log_handler.setFormatter(log_formatter)
    log_handler.setLevel(settings.LOG_LEVEL)
    logger.addHandler(log_handler)

    can_run = True
    if not os.path.exists(settings.WORK_TODO_DIR):
        logger.warning('TODO directory "{0}" does not exists.'.format(settings.WORK_TODO_DIR))
        _stderr('E')
        can_run = False
    if not os.path.exists(settings.WORK_PROCESSING_DIR):
        logger.warning('PROCESSING directory "{0}" does not exists.'.format(settings.WORK_PROCESSING_DIR))
        _stderr('E')
        can_run = False
    if not os.path.exists(settings.WORK_DONE_DIR):
        logger.warning('DONE directory "{0}" does not exists.'.format(settings.WORK_DONE_DIR))
        _stderr('E')
        can_run = False

    if not can_run:
        logger.warning('Failed to initialize, spike.')
        _stderr(' !! Stopped with errors, check logs !!')
        sys.exit(1)

    _stderr(" ** I'll dance with you, pet, on the Slayer's grave. ** ")

def setup():
    _stderr('S')
    try:
        mkdir_p(settings.WORK_TODO_DIR)
        mkdir_p(settings.WORK_PROCESSING_DIR)
        mkdir_p(settings.WORK_DONE_DIR)
        mkdir_p(os.path.dirname(settings.LOG_FILENAME))
    except Exception, e:
        logger.warning('Could not complete setup: {0}'.format(e))
        _stderr('E')


def onchange(monitor, files):
    logger.debug('On change')
    for f in files:
        file_name = os.path.basename(f)
        logger.debug('change {0}'.format(file_name))
        # Check for marker, if found trigger upload.
        if file_name == settings.WORK_DONE_MARKER:
            key = os.path.basename(os.path.dirname(f))
            upload(key)
            # Remove from monitoring
            try:
                exclude_files = [
                    settings.WORK_TODO_DIR + os.sep + key + os.sep + p for p in os.listdir(
                        settings.WORK_DONE_DIR + os.sep + key)
                ]
            except Exception, e:
                logger.warning('DONE directory for "{0}" is missing'.format(key))
                _stderr('E')
            else:
                monitor.remove_paths(exclude_files)


