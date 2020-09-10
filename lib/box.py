import os
import io
import sys
import struct
import tarfile

from .des import decode


def get_box_entries(f):
  if f.read(8) != b'Tiandy\x00\x00':
    raise Exception('invalid file magic')

  # skip the rest of this 40 byte header
  f.seek(0x20, 1)

  while True:
    # print('reading name @ 0x%x' % f.tell())

    name_buf = f.read(128)
    if not name_buf:
      break

    name = name_buf[:name_buf.index(b'\x00')].decode()

    len1, len2 = struct.unpack('<II', f.read(8))
    if len1 != len2:
      raise Exception("unsupported case where lengths don't match @ 0x%x" % (f.tell() - 8))

    # seems like lengths are aligned so we need padding
    len_pad = (8 - (len1 % 8)) % 8

    yield name, f.read(len1)

    f.seek(len_pad, 1)


def read_admin_credentials(config_box_data):
  config_box = io.BytesIO(config_box_data)

  key = uname = pw = None

  config_data = None
  for name, data in get_box_entries(config_box):
    if name == 'config_server.ini':
      config_data = data
      break

    if name.endswith('export_config.tar.gz'):
      tf = tarfile.open(fileobj=io.BytesIO(data))

      for cfgfile in tf:
        if cfgfile.name.endswith('config_server.ini'):
          cfgfile = tf.extractfile(cfgfile)
          config_data = cfgfile.read()
          break

  if config_data:
    for line in config_data.split(b'\n'):
      if b' = ' not in line:
        continue

      line = line.split(b';', 1)[0]
      k, v = line.split(b' = ')

      if k == b'yekresu': # ytiruces hcum os
        key = v

      elif k == b'username0':
        uname = v

      elif k == b'password0':
        pw = v

        break

  if not key or not uname or not pw:
    raise Exception('invalid config file: ' + config_box_data.hex())

  return decode(uname, key).decode(), decode(pw, key).decode()


def assemble_box(config_box_data, entries, box_type=2):
  if config_box_data[:6] != b'Tiandy':
    raise Exception("not a box")

  if config_box_data[12] > 0:
    type_bytes = bytes([box_type, 0, 0, 0])
  elif config_box_data[14] > 0:
    type_bytes = bytes([0, 0, box_type, 0])
  else:
    raise Exception("invalid box type")

  # ProductModule must match, so we extract it from the config box

  if config_box_data[40:53] == b'ProductModule':
    pm_length = struct.unpack('<I', config_box_data[0xac:0xb0])[0]
    pm_data = config_box_data[0xb0:0xb0+pm_length]

    entries = [
      # mandatory
      ('ProductModule', pm_data)
    ] + entries

  new_box = b''
  for name, data in entries:
    entry = struct.pack('<128sII', name.encode(), len(data), len(data)) + data

    if len(entry) % 8:
      entry += b'\x00' * (8 - (len(entry) % 8))

    new_box += entry

  new_box = struct.pack('<8sI4s8s8xII', b'Tiandy', len(new_box)+40, type_bytes, config_box_data[0x10:0x16], len(new_box), len(new_box)) + new_box

  return new_box
