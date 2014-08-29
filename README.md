# Spike

Sits in a London alley, performs punkish background jobs like watching
directories for changes and uploading files to Amazon S3 and calls a
ack API for each upload.

## Installation

Preferred way is to use virtualenv.

### Install notes.

*  Install python

    <http://www.python.org/download/releases/2.7.3/>

*  Install pip

        easy_install pip

*  Download Spike

*  Install dependencies

    Go to spike directory and open a shell, then run.

        pip install -r requirements.txt

*  Copy spike.cfg.example to spike.cfg

   Edit spike.cfg.

   Add full path to "home" directory, this is where work files will
   live. On Windows, use forward slashes.

   Add keys for AWS. 

*  Verify spike by running the following command, should give a list of
   options. Needs to be run from the command line where spike was
   installed.

        python spike.py

*  Run the following command to create all work directories.

        python spike.py --config=spike.cfg --setup

*  Start monitoring with

        python spike.py --config=spike.cfg --watch 

## Flow

Before watcher is started.

1. Check all TODO directories
2. Check all PROCESSING direcotories

1. Watch TODO directory for file changes.
2. When change is detected, move directoru PROCESSING direcotry.
3. Upload to S3, call ack api, write ack file
4. Move to DONE directory.


