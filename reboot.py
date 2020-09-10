import sys
import crypt

from lib import decode, Channel

host = sys.argv[1]

uname = b'Admin'
pw = sys.argv[2].encode()

main = Channel(host)
main.connect()

crypt_key = main.login(uname, pw)
if not crypt_key:
  print('Login failed.')
  exit(1)

main.send_msg(['PROXY', 'CMD', 'REBOOT'])

while True:
  try:
    msg = main.recv_msg()
  except ConnectionResetError:
    print('Probably worked')
    break
