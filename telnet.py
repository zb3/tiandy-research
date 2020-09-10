import sys
import crypt

from lib import decode, Channel

host = sys.argv[1]

uname = b'Admin'
pw = sys.argv[2].encode()
mode = 'enable' if len(sys.argv)<=3 or sys.argv[3] == 'enable' else 'disable'

main = Channel(host)
main.connect()

crypt_key = main.login(uname, pw)
if not crypt_key:
  print('Login failed.')
  exit(1)

main.send_msg(['PROXY', 'PARASET', 'COMMONENABLE', '73748', '0', '1' if mode == 'enable' else '0'])

while True:
  msg = main.recv_msg()
  if msg[1:6] == ['PROXY', 'INNER', 'PARASET', 'COMMONENABLE', '73748']:
    print('Telnet %sd' % mode)
    break

