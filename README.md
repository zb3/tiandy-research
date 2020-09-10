# tiandy-research
This repository contains the results of my August 2020 research of Tiandy's IPC/NVR firmware (these devices are also sold as OMNY). This "research" was not exhaustive, but I did find multiple methods to recover the administrator password remotely, enable telnet and change the root password.

It's hard to say exactly which versions are affected, since we can only download the recent ones. All these downloadable versions are affected:
```
DVRS_V9.12.7.20200422
DVRS_V11.7.4.20200721
NVSS_V13.6.1.20200723
NVSS_V22.1.0.20200722
```
Not only are there different branches for different devices, but some components are versioned and upgraded separately, like the web API, where I found an authentication bypass that only works for versions released since mid 2019 regardless of the firmware version number. If you happen to know more about versions affected, I'd appreciate your help.

I'm doing full disclosure here, but it's reasonable. A vendor patch (unlikely since they are unresponsive) 'd not make the problem vanish, especially when no devices online have the latest firmware (not even close). The actual vulnerability is that those devices are exposed to the internet. And this is something that *end users* need to fix, not Tiandy.

As a bonus, I'm also including the firmware unpacker and some info about how to access the streams via RTSP/RTMP (good luck finding that in the manual).


## What's here
Firstly I present the scripts:
- [Password recovery](#password-recovery)
- [Getting root](#getting-root)

Then I try to briefly explain what these scripts do and why. I don't repeat the code though, but I try to explain enough context so you can understand the code:
- [Overview](#overview)
- [The vulnerabilities](#the-vulnerabilities)
- [Beyond password recovery](#beyond-password-recovery)

Finally, this get relatively technical:
- [Unpacking the firmware](#unpacking-firmware)
- [Finding Tiandy devices on the internet](#finding-tiandy)
- [Bonus: RTSP and RTMP urls](#rtsp-rtmp-urls)

## <a name="password-recovery">Password recovery</a>
You'll need Python 3 with PyCrypto.

First, try `recover.py`. This requires port `3001` to be accessible:
```
python3 recover.py [HOST]
```
if everything goes well, the administrator credentials should be printed.

If that port is not accessible, the web one might work. This requires the url:
```
python3 cgi_recover.py http://123.45.67.89
python3 cgi_recover.py https://123.45.67.89
```

If none of the above work, check if telnet is enabled. If it is, you can root the device directly, just crack this hash:
```
support:$1$$AErA9BQgLjrxTJB1748k71:501:501:Linux User,,,:/home/support:/bin/sh
```
(make sure to open a PR in case you actually crack it :D)


## <a name="getting-root">Getting root</a>

### Old firmware
In older `V7` NVR firmware, you can run commands directly:
```
python3 ftpupdate.py [host] [adminpass] '[cmd]'
```
but it gives no output. To make this easier, I've included this shorthand:
```
python3 ftpupdate.py [host] [adminpass] adduser [username] [password]
```
This will add another user with uid 0.


### Newer firmware
First, enable telnet using:
```
python3 telnet.py [host] [adminpw]
```
or for recent devices:
```
python3 cgi_recover.py [host] telnet
```

Then you can overwrite `/etc/passwd` (I assume you know how this works). Try `filetransport.py` first (for NVRs):
```
python3 filetransport.py [host] [adminpass] put /etc/passwd <[source_file]
```
this gives no feedback, you need to test it by trying to login...

For IPC models where `filetransport.py` doesn't work, try `upgrade_rw.py`:
```
python3 upgrade_rw.py [url] [adminpass] /etc/passwd <[source_file]
```
(this gives no feedback either)

Finally, for even newer devices, this can also be done through the web API:
```
python3 cgi_recover.py [url] write /etc/passwd <[source_file]
```

If none of the above worked (check whether you can login), retry all those methods but overwrite `/config/etc/passwd` instead. In some firmware versions, `/etc/passwd` is a symlink to that. Finally, you can also try overwriting `/tdfs/etc/passwd`, but after that, a device reboot might be needed, so to reboot, use:
```
python3 reboot.py [host] [adminpass]
```


## <a name="overview">Overview</a>

The old `V7` (IPC and NVR) firmware doesn't appear to be affected, but if you have the administrator password, for NVRs there's an authenticated RCE (`ftpupdate.py`), and for IPCs, the `upgrade-rw.py` script might be used to overwrite `/etc/passwd`.

Later versions of the NVR firmware (`V9` and `V11`) feature a default account, which combined with "passive" privilege escalation makes it possible to recover the administrator password. We can then overwrite `/etc/passwd` using `filetransport.py`.

While the default account isn't present in the IPC firmware, another recovery method appears - the PSW method. This is a password recovery mechanism with no security at all. It's present in all downloadable firmware versions since `V9`. While `filetransport.py` only works on NVRs, `upgrade_rw.py` achieves the same purpose on IPCs by using the upgrade mechanism so we can still gain the root access.

2019 firmware introduces another attack vector - an authentication bypass using the web API. By exporting the configuration file without authentication, we can recover the password and prepare an upgrade package to overwrite arbitrary files.

Speaking of vulnerabilities, there are 4 of them:
* Hardcoded telnet credentials (old NVR firmware)
* Authenticated privilege escalation (any user can read the administrator password)
* Insecure password recovery (symmetric encryption key embedded in the binary)
* Web API authenttication bypass (appending certain strings to the URL path disables authentication)

Note that I didn't investigate the "cloud" features i.e. whether it's possible to enumerate devices and therefore connect to devices not exposed to the internet (as it is with Xiongmai devices).

## <a name="the-vulnerabilities">The vulnerabilities</a>

### Hardcoded telnet credentials for old firmware

In old versions, telnet is enabled by default and this is what we can find in the `/etc/passwd` file:
```
support:$1$$AErA9BQgLjrxTJB1748k71:501:501:Linux User,,,:/home/support:/bin/sh
```
(root password is updated dynamically, also I didn't crack this hash, so pull requests more than welcome :D)

The `support` user (actually present in all firmware versions) might seem unprivileged, but of course, this user has enough privileges to read the `Admin` password and overwrite world-writable init scripts in `/etc/init.d` or even create new ones :)


### The default account + authenticated privilege escalation

Conceptually, the method is really simple. We just send a login packet and read the response. That's all, because the "login successful" response contains credentials of all users, regardless of our privileges. While it was like this in `V7` too, practically this method became useful only when the default account was introduced in the NVR firmware. The irremovable "Default" has no remote privileges, so you can't do anything with it. Well, maybe except reading the administrator password...

While this sounds trivial, it wasn't that trivial to implement. A custom protocol is used for communication, and passwords are encryptred using DES but with bits reversed (the hardest part was figuring that out), with a key transmitted by the server. Since there's no key derivation, an eavesdropper could easily decrypt everything. Nevertheless, one still needs to figure out that the bits are reversed, or reimplement the whole thing from scratch...

See the `recover_with_default` function in the `recover.py` file for the implementation.


### Insecure password recovery - the PSW method

When analysing the binary, it's hard not to notice this mechanism. Its whole purpose is to... make password recovery possible, and it actually does this thing well. Too well I'd say...

What's going on here? I think this meant to be a password recovery mechanism, presumably created so that vendors could provide a way to for device owners to recover *their* passwords.

I can hypothesize the flow was supposed to be like this:
1. You enter your email or phone when configuring the device
2. You ask Tiandy to recover your password
3. Tiandy sends a "magic packet" to your device and obtains an email/phone and an encrypted data to derive the security code.
4. Tiandy decrypts and derives the security code and sends it via that communication channel.
5. You enter this security code in your client program which sends a second packet.
6. Voila. The client decrypts the response and shows you the credentials.

That's all good, except there's one thing missing... where's the security?
Nowhere, it turns out. There's nothing stopping us from sending this packet, deriving the security code and recovering the password of any accessible device.

I find this astonishing, because it's not that there's some flaw in the mechanism which defeats the security. It's simply not there at all. There's nothing to fix, but this also doesn't look like an obvious backdoor to me. This leaves traces in the logs and has 3 different derivation schemes, each more sophisticated than the previous one. This actually took time to implement...

Going back to the method, in order for this to work, the device needs to have a phone/email associated. Looking at the older version, I saw that only the administrator can do this, but then I found a bypass. Surprisingly, in the newer firmware, that bypass is no longer needed, since it's explicitly possible to change the device email without authentication. Now, _this_ is where I think the backdoor was supposed to be :)

On the technical side, this mechanism is actually quite complicated and was the hardest one to reverse and reimplement. There are 3 versions of this mechanism, each one uses a different algorithm for deriving the security code. Besides DES with bits reversed, a custom substitution cipher with a hardcoded key is involved. But this is all for nothing, because Tiandy can't make symmetric encryption with a hardcoded key secure, no matter how hard they try. 

One thing I observed is that since the security code changes every minute, there's a possibility that the original process could fail just because the code changed between the packet in step 3 and the one in step 5, regardless of how little time has passed between sending those. I took this into account so my script retries the process if the code turns out to be invalid.

The whole process, including setting the email (which we don't need to own) is implemented in the `recover.py` file.

 
### The web API authentication bypass
This one works with newer firmware versions (2019 and later) that have the "modern" web interface (that one with the "map". I like that map even though Australia seems a bit distorted).

This bypass is simple. While most API endpoints are authenticated, there are some exceptions. However, a check for whether to skip the authentication and a match for which endpoint to activate are implemented in different places. In most cases, the authentication is skipped when the URL path is equal to a given string, which is secure. 

But recent versions introduce another exception, which is activated when the strings `Record/DownLoad` and `ID=` simply exist somewhere in the URL path.

Now, for endpoints where the full path is matched, this is still secure. Since `Security/users` is one of those endpoints, we can't recover the password directly. Luckily for us, the config export endpoint gets selected by checking whether the URL path *starts* with a given string (using `strncmp`), so we can just append those strings to the path and export the configuration file.

Recovering the password using this flaw is implemented in `cgi_recover.py`.


## <a name="beyond-password-recovery">Beyond password recovery</a>

Theoretically, the administrator can upgrade the firmware, and the firmware is neither signed nor encrypted. But do we really need to prepare a custom firmware package? Sometimes not. Sometimes we do, and I was crazy enough to actually implement it...


### For old NVR firmware
If you have the password, there's a command injection vulnerability you can use, the `ftpupdate.py` script. What happens there is that we tell the device to fetch an upgrade over ftp and `ftpget` is used perform that task. Unsurprisingly, our parameters flow directly into the `system()` function.


### Newer firmware
In the NVR firmware, the binary protocol has the `FILETRANSPORT` command which does exactly what it says. Actually there's nothing more to say, because you could as well download the SDK and use the same command. Of course I wanted to reimplement it, so to see how this works, look at `filetransport.py`.

IPC models don't have this command though, yet like I said before, we can always upgrade the firmware. While preparing the whole flash is impractical, Tiandy's upgrade packages allow us to replace individual files, which is exactly what we need (see unpacking the firmware).

Except, it's not that simple. The "box" file format has some metadata, then an array of files. The first file has to be named `ProductModule`, and must contain matching device parameters, otherwise the upgrade won't proceed. We need not only values of those parameters, but also those parameters themselves. Additionally, the metadata part (including box file version) is also verified.

Manually assembling those seems impractical, but fortunately there's another way. The configuration file exports use the same "box" file format, with all the matching metadata and the `ProductModule` file included, sans the upgrade type field.

I was able to find out how to fill this field, and therefore implement this process. While the mechanism is also present in the NVR firmware, it doesn't work the same way, yet there's no point in further analysis since NVRs have the `FILETRANSPORT` command that was previously described.

The `upgrade_rw.py` script makes use of the upgrade process. The name suggests something more though... That's because when exporting the configuration file, we specify which files to export by name, and unsurprisingly, any file works, so we can download the box and then read that file using the same code used to extract the firmware.

Both the export and upgrade can be done via the web API as well. In this case it's not possible to read arbitrary files. I still wanted to implement this because the API seems more stable, see `cgi_recover.py`.

### What I didn't look at
In models that support FTP, it *might* be possible to inject shell commands in the user password (when a command is executed which adds this user so they can log in via FTP).


## <a name="finding-tiandy">Finding Tiandy devices on the internet</a>
Tiandy devices have the port 3001 open. This is the port needed for the non-web methods to run. 
Newer models have RTSP on port 9100 in addition to port 554, and they also have RTMP on port 1935. IPC models use port 8082 for ONVIF. HTTP and HTTPS run on their standard ports.

Devices with the older web interface (using our beloved ActiveX technology) contain one of the following in their HTTP response:
```
<title>Net Video Browser</title>
```
```
tdvideo.css
```

Devices with the newer web interface (this time using... Flash) contain this in the response:
```
res/app-0.1.0.css
```
(the `Last-Modified` header is happy to reveal the exact release date to us)

We can also identify those devices by the certificate, albeit HTTPS is not always enabled. There are only two certificates used for all devices and they can be found in the downloaded firmware, which makes pinning them useless.

The older one:
```
C=CN, ST=Tianjin, O=Tiandy Tech, CN=dvr_ui
```

The newer one:
```
C=CN, ST=Tianjin, L=Tianjin, O=Tiandy Tech Ltd, CN=NetDevice
```

BTW... HTTPS support is implemented via a separate `stunnel` process. This works, but unsurprisingly the IP address is lost in process, so the logs always say `127.0.0.1`.

## <a name="rtsp-rtmp-urls">Tiandy RTSP and RTMP urls</a>

Tiandy claims their devices support RTSP and RTMP. That's cool, but what we can't find in the manual is how to actually use these protocols, because we can't find necessary RTSP and RTMP urls.
Fortunately I have this information as a byproduct of the analysis, so I can share it.

### RTSP urls

**For NVR:**  
To view the live stream for channel `C` (starting with 1) with stream type `S` (1, 2, 3):
```
rtsp://username:password@host/C/S
```

**For IPC:**   
To view the live stream with stream type `S`:
```
rtsp://username:password@host/S
```

### RTMP urls
RTMP urls are not so simple because they require a custom hash so that the request can be authenticated. However, RTMP also allows us to play back the recorded content.

The url for the live stream is:
```
rtmp://host/live/C/S/authstring
```
where `C` is the channel, `S` is the stream type.

The url for playback is:
```
rtmp://host/vod/START-STOP/C/S/authstring
```
where both `START` and `STOP` are unix timestamps.

`authstring` is computed as follows:
```
base64("username:"+md5("username:password")+":unix_timestamp")
```
The `rtmpauth.py` tool can generate it:
```
python3 rtmpauth.py username password
```

Since this timestamp is checked and the difference can be no more than 2 days, there are limitations:
- the camera needs to have correct time set up
- a RTMP URL will stop working after 2 days


## <a name="unpacking-firmware">Unpacking the firmware</a>

Firmware upgrades are packed in a proprietary "box" file format that is neither signed nor encrypted. This format is actually very simple from the unpacker's perspective. There's a header which we skip, and an array of files to unpack, where each file has a fixed-size header containing file name and size (twice), then the data follows.

The `unbox.py` tool unpacks the file into a directory named like the box file or the specified directory:
```
python3 unbox.py [box_file]
python3 unbox.py [box_file] [target_dir]
```

This tool should be safe to use (I wrote this line, then checked the tool again and found a vulnerability... oops) because absolute paths are turned into relative ones, `..` is replaced with `__` and there are no symlinks.

Sometimes you'll need to run this tool twice as you'll notice that the file inside a `.box` is another `.box`.




