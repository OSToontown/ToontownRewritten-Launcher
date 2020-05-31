import json, sys, os
from urllib.request import urlopen
from urllib.parse import urlencode
import requests

#Some nice constants
MIRRORLIST = "https://www.toontownrewritten.com/api/mirrors"
MANIFEST_URL = "https://cdn.toontownrewritten.com/content/patchmanifest.txt"

from patcher.ManagedFile import ManagedFile
PATCHER_BASE = os.environ.get('PATCHER_BASE', './')

print('Obtaining available mirrors...')

MIRRORS = []
try:
    remoteMirrors = requests.get(MIRRORLIST)

    if remoteMirrors.status_code != 200:
        raise Exception("Received non-OK response when fetching the mirror list!")

    MIRRORS = remoteMirrors.json()
    print('Obtained %s mirrors from remote server.' % len(MIRRORS))
except:
    pass

#if not MIRRORS:
#    try:
#        remoteMirrors = urlopen('https://s3.amazonaws.com/nope/mirrors.txt', timeout=10)
#        MIRRORS = json.loads((remoteMirrors.read().decode('utf-8')))
#        print('Obtained %s mirrors from backup remote server.' % len(MIRRORS))
#    except:
#        pass

if not MIRRORS:
    MIRRORS = ['http://download.toontownrewritten.com/patches/']
    print("Couldn't get the mirrorlist from the website! Falling back to download.toontownrewritten.com")
MIRRORS = [ mirror.encode('ascii') for mirror in MIRRORS ]


MF = requests.get(MANIFEST_URL)

if MF.status_code != 200:
    raise Exception("Received a non-OK response from the CDN when getting the update manifest.")
MANIFEST = MF.json()
files = []

def Patch(progressCallback=None, fileCallback=None):
    global count
    count = 0
    for filename in MANIFEST:
        print("begin patch %s" % filename)
        count += 1
        entry = MANIFEST.get(filename)
        print('Updating file %s of %s, %s...' % (count, len(MANIFEST), filename))
        if sys.platform not in entry.get('only', ['linux2', 'win32', 'darwin']):
            print('Skipped updating, file is not required on this platform.')
            continue
        if fileCallback is not None:
            fileCallback('Updating file %s of %s\n(%s)' % (count, len(MANIFEST), filename))
        managedFile = ManagedFile(filename, installBase=PATCHER_BASE, hash=entry.get('hash'), dl=entry.get('dl'), compHash=entry.get('compHash'), progressCallback=progressCallback)
        managedFile.update(MIRRORS, patches=entry.get('patches'))
        files.append(managedFile)

    return
