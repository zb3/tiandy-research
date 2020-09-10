import socket
import struct
import base64
import hashlib


def recvall(s, l):
  buf = b''
  while len(buf) < l:
    nbuf = s.recv(l - len(buf))
    if not nbuf:
      break

    buf += nbuf

  return buf

class Channel:
  def __init__(self, ip, port=3001):
    self.ip = ip
    self.ip_bytes = socket.inet_aton(ip)[::-1]
    self.port = port
    self.msg_seq = 0
    self.data_seq = 0
    self.msg_queue = []

  def fileno(self):
    return self.socket.fileno()

  def connect(self):
    self.socket = socket.socket()
    self.socket.connect((self.ip, self.port))

  def reconnect(self):
    self.socket.close()
    self.connect()

  def send_cmd(self, data):
    self.socket.sendall(b'\xf1\xf5\xea\xf5' + struct.pack('<HH8xI', self.msg_seq, len(data) + 20, len(data)) + data)
    self.msg_seq += 1

  def send_data(self, stream_type, data):
    # must support streamtype, length
    # probably also ip to bytes

    self.socket.sendall(struct.pack('<4sI4sHHI', b'\xf1\xf5\xea\xf9', self.data_seq, self.ip_bytes, 0, len(data) + 20, stream_type) + data)
    self.data_seq += 1


  def recv(self):
    hdr = recvall(self.socket, 20)
    if hdr[:4] == b'\xf1\xf5\xea\xf9':
      lsize, stream_type = struct.unpack('<14xHI', hdr)
      data = recvall(self.socket, lsize - 20)

      # we want to know when this is not the case
      if data[:4] != b'NVS\x00':
        print(data[:4], b'NVS\x00')
        raise Exception('invalid data header')

      return None, [stream_type, data[8:]]


    elif hdr[:4] == b'\xf1\xf5\xea\xf5':
      lsize, dsize = struct.unpack('<6xH10xH', hdr)

      if lsize != dsize + 20:
        raise Exception('size mismatch')

      msgs = []

      for msg in recvall(self.socket, dsize).decode().strip().split('\n\n\n'):
        msg = msg.split('\t')
        if '.' not in msg[0]:
          msg = [self.ip] + msg

        msgs.append(msg)

      return msgs, None

    else:
      raise Exception('invalid packet magic: ' + hdr[:4].hex())

  def recv_msg(self):
    if len(self.msg_queue):
      ret = self.msg_queue[0]
      self.msg_queue = self.msg_queue[1:]

      return ret

    msgs, _ = self.recv()

    if len(msgs) > 1:
      self.msg_queue.extend(msgs[1:])

    return msgs[0]

  def send_msg(self, msg):
    self.send_cmd((self.ip+'\t'+'\t'.join(msg)+'\n\n\n').encode())

  def get_crypt_key(self, mode=1, uname=b'Admin', pw=b'Admin'):
    self.send_msg(['IP', 'USER', 'LOGON', base64.b64encode(uname).decode(), base64.b64encode(pw).decode(), '', str(mode), 'UTF-8', '805306367', '1'])

    resp = self.recv_msg()

    if resp[4:6] != ['LOGONFAILED', '3']:
      print(resp)
      raise Exception('unrecognized login response')

    crypt_key = base64.b64decode(resp[8])
    return crypt_key

  def login_with_key(self, uname, pw, crypt_key):
    self.reconnect()

    hashed_uname = base64.b64encode(hashlib.md5(uname.lower()+crypt_key).digest())
    hashed_pw = base64.b64encode(hashlib.md5(pw+crypt_key).digest())

    self.send_msg(['IP', 'USER', 'LOGON', hashed_uname.decode(), hashed_pw.decode(), '', '1', 'UTF-8', '1', '1'])
    resp = self.recv_msg()

    if resp[4] == 'LOGONFAILED':
      return False

    self.msg_queue = [resp] + self.msg_queue

    return True

  def login(self, uname, pw):
    crypt_key = self.get_crypt_key(1, uname, pw)

    if not self.login_with_key(uname, pw, crypt_key):
      return False

    return crypt_key



