#!/usr/bin/env python

import json
import logging
import os
import paramiko
import pika
import sys
import time

logging.basicConfig(filename='/src/handler.log', level=logging.INFO)


class GerritEventStream(object):
    def __init__(self, *args, **kwargs):
        logging.info('Connecting to gerrit stream using env variables...')
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connected = False
        while not connected:
            try:
                self.ssh.connect(os.environ.get('gerrit_host'),
                                 int(os.environ.get('gerrit_port')),
                                 os.environ.get('ci_account'),
                                 key_filename=os.environ.get('gerrit_ssh_key'))
                connected = True
            except paramiko.SSHException as e:
                logging.error('%s', e)
                logging.warn('Gerrit may be down, will pause and retry...')
                time.sleep(10)

        self.stdin, self.stdout, self.stderr =\
            self.ssh.exec_command("gerrit stream-events")

    def __iter__(self):
        return self

    def next(self):
        return self.stdout.readline()


def _verify_vars():
    for key in ['gerrit_ssh_key', 'gerrit_host', 'gerrit_port', 'project_name',
                'ci_name', 'ci_account', 'recheck_string']:
        if not os.environ.get(key, None):
            logging.error('Missing env variable: %s' % key)
            sys.exit(1)
    return True


def _is_valid_event(event):
    valid = False
    comment_added = event.get('comment', '')
    project = event.get('change', {}).get('project', {})
    branch = event.get('change', {}).get('branch', {})
    author = event.get('author', {}).get('username', {})

    if (comment_added and
            project == os.environ.get('project_name') and
            branch == 'master'):
        if (os.environ.get('recheck_string') in comment_added or
                ('Verified+1' in comment_added and
                 author == 'jenkins')):
            valid = True
    if valid:
        return event
    else:
        return None

reconnect = 6
while reconnect:
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='rabbit'))
        channel = connection.channel()
        channel.queue_declare(queue='task_queue', durable=True)
        reconnect = 0
    except pika.exceptions.ConnectionClosed as ex:
        logging.warning('Connection to RMQ failed, '
                        'remaining attempts: %s' %
                        reconnect)
        reconnect -= 1
        time.sleep(10)
        if reconnect < 1:
            raise(ex)


if not _verify_vars:
    logging.error('Missing required variable, exiting!')
    sys.exit(1)

connected = False
events = []
while not connected:
    try:
        events = GerritEventStream('sfcli')
        logging.info('Connected to gerrit, streaming events.')
        connected = True
    except Exception as ex:
        logging.exception('Error connecting to Gerrit: %s', ex)
        time.sleep(60)
        pass


logging.info('launching event handler/listener loop')
loop_counter = 0
while True:
    for event in events:
        try:
            event = json.loads(event)
        except Exception as ex:
            logging.error('Failed json.loads on event: %s', event)
            logging.exception(ex)
            break
        valid_event = _is_valid_event(event)
        if valid_event:
            logging.info('Identified valid event, sending to queue...')
            channel.basic_publish(
                exchange='',
                routing_key='task_queue',
                body=json.dumps(valid_event),
                properties=pika.BasicProperties(
                    delivery_mode=2,))
