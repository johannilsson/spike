import sys
from optparse import OptionParser
import ConfigParser
from spike import worker
from spike import settings

__author__ = 'Expanded Activities'
__version__ = '0.1.dev'
__license__ = 'MIT'

# Workaround for the "print is a keyword/function" Python 2/3 dilemma
# and a fallback for mod_wsgi (resticts stdout/err attribute access)
# From Bottle.
try:
    _stdout, _stderr = sys.stdout.write, sys.stderr.write
except IOError:
    _stdout = lambda x: sys.stdout.write(x)
    _stderr = lambda x: sys.stderr.write(x)

def main():
    # TODO: Add so we can only process one key.
    _cmd_parser = OptionParser(usage="usage: %prog [options]", version="%prog {0}".format(__version__))
    _opt = _cmd_parser.add_option
    _opt("-c", "--config", action="store", help="path to configuration [default: %default].", default="spike.cfg")
    _opt("-w", "--watch", action="store_true", help="watch work directory.")
    _opt("-u", "--upload", action="store", help='upload directory, if UPLOAD is logs log files is upload.', dest='upload')
    _opt("-r", "--recover", action="store_true", help='recover', dest='recover')
    _opt("-s", "--setup", action="store_true", help='setup', dest='setup')
    _cmd_options, _cmd_args = _cmd_parser.parse_args()

    opt, args, parser = _cmd_options, _cmd_args, _cmd_parser

    sys.path.insert(0, '.')
    sys.modules.setdefault('spike', sys.modules['__main__'])

    config = ConfigParser.ConfigParser()
    config.readfp(open(opt.config))

    settings.APP_HOME               = config.get('app', 'home')
    settings.WORK_TODO_DIR          = config.get('app', 'todo_dir')
    settings.WORK_PROCESSING_DIR    = config.get('app', 'processing_dir')
    settings.WORK_DONE_DIR          = config.get('app', 'done_dir')
    settings.WORK_DONE_MARKER       = config.get('app', 'done_marker')
    settings.LOG_FILENAME           = config.get('app', 'log_filename')
    settings.AWS_ACCESS_KEY_ID      = config.get('aws', 'access_key_id')
    settings.AWS_SECRET_ACCESS_KEY  = config.get('aws', 'secret_access_key')
    settings.AWS_BUCKET             = config.get('aws', 'bucket')
    settings.AWS_LOG_BUCKET         = config.get('aws', 'log_bucket')
    settings.API_ACK_ENDPOINT       = config.get('api', 'ack')
    settings.API_USER               = config.get('api', 'user')
    settings.API_PASSWORD           = config.get('api', 'password')

    if opt.watch:
        worker.init()
        worker.watch()
    elif opt.upload:
        worker.init()
        key = opt.upload
        if key == 'logs':
            worker.upload_logs()
        else:
            worker.upload(key)
    elif opt.recover:
        worker.init()
        worker.recover()
    elif opt.setup:
        worker.setup()
    else:
        parser.print_help()
        _stderr('\nError: No options specified.\n')
        sys.exit(1)


if __name__ == '__main__':
    main()



