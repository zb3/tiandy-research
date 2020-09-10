#!/usr/bin/python3

import sys
import time
import base64
import hashlib

if len(sys.argv) != 3:
  exit('rtmpauth.py [username] [password]')

username, password = sys.argv[1:3]

hash = hashlib.md5(('%s:%s' % (username, password)).encode()).hexdigest()
authstr = '%s:%s:%d' % (username, hash, int(time.time()))

print(base64.b64encode(authstr.encode()).decode())
