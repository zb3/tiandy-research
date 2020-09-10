import sys
import crypt
import base64

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

while True:
  msg = main.recv_msg()

  print(msg)

  if msg[1:5] == ['IP', 'INNER', 'SUPER', 'GETUSERINFO']:
    print('user', decode(msg[6].encode(), crypt_key).decode(), decode(msg[7].encode(), crypt_key).decode())


