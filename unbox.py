#!/usr/bin/python3

import os
import sys
import struct

from lib.box import get_box_entries

def unbox(fn):
  with open(fn, 'rb') as f:
    for name, data in get_box_entries(f):
      print('Unpacking', name)

      """
      initially I wrote this:

      if name.startswith('/'):
        name = name[1:]

      I think Tiandy'd be proud of me :)
      """

      while name.startswith('/'):
        name = name[1:]

      name = name.replace('..', '__')

      fdir = os.path.dirname(name)
      if fdir:
        os.makedirs(fdir, exist_ok=True)

      with open(name, 'wb') as wf:
        wf.write(data)


if __name__ == '__main__':
  if len(sys.argv) < 2:
    print('python3 %s [box_file]' % sys.argv[0], file=sys.stderr)
    print('python3 %s [box_file] [target_dir]' % sys.argv[0], file=sys.stderr)
    exit(1)

  box_file = sys.argv[1]
  target_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(box_file)[0]

  box_file = os.path.abspath(box_file)
  os.makedirs(target_dir, exist_ok=True)
  os.chdir(target_dir)

  print('Extracting to', target_dir)

  unbox(box_file)

    