import os
import logging
import logging.handlers

# Where this app should place work files.
APP_HOME = ''

#WORK_DIR            = APP_HOME
WORK_TODO_DIR       = '' #WORK_DIR + os.sep + 'todo'
WORK_PROCESSING_DIR = '' #WORK_DIR + os.sep + 'inprogress'
WORK_DONE_DIR       = '' #WORK_DIR + os.sep + 'done'

WORK_DONE_MARKER = 'done.txt'

# AWS Setup
AWS_ACCESS_KEY_ID       = None
AWS_SECRET_ACCESS_KEY   = None
AWS_BUCKET              = None
AWS_LOG_BUCKET          = None

API_BASE         = 'http://localhost:8888/api'
API_ACK_ENDPOINT = '/ack/'
API_USER         = ''
API_PASSWORD     = ''

LOG_FILENAME = APP_HOME + os.sep + 'logs' + os.sep + 'app.log'
LOG_LEVEL = logging.DEBUG


