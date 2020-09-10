import base64
from Crypto.Cipher import DES

def reverse_bits(data): # using magic
  return bytes([(b * 0x0202020202 & 0x010884422010) % 0x3ff for b in data])

def pad(data):
  # there's no real padding here, we just assume that the message won't contain any null bytes

  if len(data) % 8:
    padlen = 8 - (len(data) % 8)
    data = data + b'\x00' * (padlen-1) + bytes([padlen])

  return data

def unpad(data):
  # since this isn't a real padding, we have to guess it
  # not that it makes any sense, we could simply cut it on first null byte
  padlen = data[-1]

  if 0 < padlen <= 8 and data[-padlen:-1] == b'\x00'*(padlen-1):
    data = data[:-padlen]

  return data

def encrypt(data, key):
  cipher = DES.new(reverse_bits(key), 1)
  return reverse_bits(cipher.encrypt(reverse_bits(pad(data))))

def decrypt(data, key):
  cipher = DES.new(reverse_bits(key), 1)
  return unpad(reverse_bits(cipher.decrypt(reverse_bits(data))))

def encode(data, key):
  return base64.b64encode(encrypt(data, key))

def decode(data, key):
  return decrypt(base64.b64decode(data), key)
