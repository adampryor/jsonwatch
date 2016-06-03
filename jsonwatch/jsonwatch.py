#!/usr/bin/env python2
# jsonwatch
# Copyright (c) 2014 Danyil Bohdan
# This code is released under the MIT license. See the file LICENSE.

from __future__ import print_function

from jsondiff import json_flatten, json_flat_diff, json_diff_str

import six.moves.urllib as urllib
import argparse
import json
import sys
import subprocess
import time
import datetime
import traceback


class JSONRequestURL(object):
    """Abstracts away requests for JSON data from URLs."""
    def __init__(self, url):
        self.url = url
        self.opener = urllib.request.build_opener()
        # User agent needed for some APIs that decide whether to feed
        # you JSON data or a webpage/error 403 based on it.
        self.opener.addheaders = [('User-agent', 'curl')]

    def perform(self):
        return json.loads(self.opener.open(self.url).read().decode("utf-8"))


class JSONRequestCommand(object):
    """Abstracts away requests for JSON data from shell commands."""
    def __init__(self, command):
        self.command = command

    def perform(self):
        return json.loads(subprocess.check_output(self.command, shell=True))


def json_print(jsn):
    print(json.dumps(jsn, indent=4))


def poll_loop(interval, req, date=True, initial_values=True, specify_keys=None):
    """Perform requests for JSON data. Print out changes when they occur."""

    prev_output = None
    output = None
    try:
        output = req.perform()
        if initial_values:
            json_print(output)
        output = json_flatten(output)
    except (subprocess.CalledProcessError,
            urllib.error.HTTPError,
            ValueError) as e:
        print(traceback.format_exc(), file=sys.stderr)
    while True:
        try:
            time.sleep(interval)
            try:
                prev_output, output = output, json_flatten(req.perform())
                diff = json_flat_diff(prev_output, output)
                if diff is not None:
                    msg = json_diff_str(diff, specify_keys)
                    msg.sort()
                    # If msg is multi-line print each difference on a new line
                    # with indentation.
                    prefix = ''
                    if date:
                        prefix += datetime.datetime.now().isoformat()
                    if len(msg) > 1:
                        print(prefix, \
                              "\n   ", "\n    ".join(msg))
                    else:
                        print(prefix, msg[0])
            except (subprocess.CalledProcessError,
                    urllib.HTTPError,
                    ValueError) as e:
                print(traceback.format_exc(), file=sys.stderr)
        except KeyboardInterrupt:
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Track changes in JSON data')
    parser.add_argument('-u', '--url', help='URL',
                        default='', required=False, metavar='url',
                        dest='url')
    parser.add_argument('-c', '--command', help='command to execute',
                        default='', required=False, metavar='command',
                        dest='command')
    parser.add_argument('-n', '--interval', help='interval',
                        default=None, type=int, required=False,
                        metavar='seconds', dest='interval')
    parser.add_argument('--no-date',
                        help='don\'t print date and time for each diff',
                        default=True, required=False,
                        dest='print_date', action='store_false')
    parser.add_argument('--no-initial-values',
                        help='don\'t print the initial JSON values',
                        default=True, required=False,
                        dest='print_init_val', action='store_false')
    parser.add_argument('--specify-keys',
                        help='Only watch specified keys. Separate multiple values with a space. \
                        Keys are supplied in `flattened` form. For content \
                        {"a":{"x":1,"y":2,"z":3}} the argument `--specify-keys .a.x .a.y` would \
                        report the values 1 and 2 but not 3.',
                        default=None, required=False,
                        dest='specify_keys', nargs='*',
                        metavar='flattened.key')
    # Process command line arguments.
    args = parser.parse_args()
    
    # If both or none of 'url' and 'command' given display help and exit.
    if (args.url == '') == (args.command == ''):
        parser.print_help()
        sys.exit(1)

    req = None
    if args.url != '':
        if args.interval is None:
            args.interval = 60
        req = JSONRequestURL(args.url)
    else:
        if args.interval is None:
            args.interval = 5
        req = JSONRequestCommand(args.command)
    poll_loop(args.interval, req, args.print_date, args.print_init_val, specify_keys=args.specify_keys)


if __name__ == "__main__":
    main()
