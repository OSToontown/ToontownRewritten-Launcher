import bsdiff4, hashlib, os, bz2
from urllib.request import urlopen
from urllib.parse import urlencode
import requests

class ManagedFile:

    def __init__(self, name, installBase=None, hash=None, compHash=None, dl=None, progressCallback=None):
        self.name = name
        self.installBase = installBase
        if self.installBase:
            self.loc = os.path.join(installBase, name)
            self.ensureDirectoriesExist()
        self.progressCallback = progressCallback
        self.hash = hash
        self.compHash = compHash
        if not dl:
            self.dl = self.name
        else:
            self.dl = dl

    def ensureDirectoriesExist(self):
        dirs = self.name.split('/')[:-1]
        base = self.installBase
        for dir in dirs:
            base = os.path.join(base, dir)
            if not os.path.isdir(base):
                os.makedirs(base)

    def update(self, urls, patches=None):
        if not self.loc:
            raise Exception('Cannot update a ManagedFile that has no filesystem location')
        if not self.hash:
            raise Exception("Cannot update a ManagedFile that doesn't know its hash")
        for url in urls:
            if url and not url.decode('utf-8').endswith('/'):
                fixedurl = url.decode('utf-8') + '/'
                urls[urls.index(url)] = fixedurl

        if not os.path.exists(self.loc):
            print('File did not exist, downloading fresh...')
            self.obtainFresh(urls)
        else:
            if self.hash == self.currentHash():
                print('File is up to date.')
                return
            patch = self.getPatch(patches)
            if not patch:
                print('No patch found! Downloading fresh...')
                self.obtainFresh(urls)
            else:
                print('Patch located! Patching...')
                try:
                    patchIsGood = self.doPatch(patch, urls)
                    if not patchIsGood:
                        print('Patching failed! Downloading fresh...')
                        self.obtainFresh(urls)
                    else:
                        print('Patched file.')
                except Exception as e:
                    print("An unhandled error occured while patching the file. Do not report this to the TTR devs as this is almost certainly not their fault.")
                    print(e)
                    print("Obtaining fresh file...")
                    self.obtainFresh(urls)
    def obtainFresh(self, urls):
        urlsToTry = [ x for x in urls ]
        for url in urlsToTry:
            try:
                print(url.decode('utf-8') + self.dl)
                self._obtainFresh(url.decode('utf-8') + self.dl)
                return
            except Exception as e:
                print('OF: Mirror %s failed integrity checks, removing... %s' % (url, e))
                urls.remove(url)
    def _obtainFresh(self, url):
        with open(self.loc, 'wb') as f:
            resp = requests.get(url, stream=True)
            tl = resp.headers.get("content-length")
            decomp = bz2.BZ2Decompressor()
            hasher = hashlib.sha1()
            op = 0
            if tl is None:
                f.write(resp.content)
            else:
                tl = int(tl.strip())
                have = 0
                print("GET %s (%d)" % (url, tl))
                for data in resp.iter_content(chunk_size=8192):
                    have += len(data)
                    dcd = decomp.decompress(data)
                    hasher.update(dcd)
                    f.write(dcd)
                    np = round((have / tl) * 100)
                    if self.progressCallback is not None and op != np:
                        self.progressCallback(np)
                        op = np
            h = hasher.hexdigest()
            print("Downloaded Hash: %s\nExpected Hash: %s" % (h, self.hash))
            if h != self.hash:
                raise Exception("Downloaded file has a different hash than we expected.")
        return

    def _getFile(self, flags='rb'):
        try:
            return open(self.loc, flags)
        except:
            print('')
            return

        return

    def getContents(self):
        if not self.loc:
            raise Exception('Cannot read contents of a ManagedFile that has no filesystem location')
        f = self._getFile('rb')
        fc = f.read()
        f.close()
        return fc

    def __hash(self, input):
        return hashlib.sha1(input).hexdigest()

    def currentHash(self):
        return self.__hash(self.getContents())

    def doPatch(self, patch, urls):
        patchContents = self.downloadPatch(patch, urls)
        if not patchContents:
            raise Exception('Error in procuring patch')
        oldContents = self.getContents()
        patchedContents = bsdiff4.patch(oldContents, patchContents)
        del oldContents
        del patchContents
        if self.hash != self.__hash(patchedContents):
            raise Exception('In-memory patch did not have correct hash after patching! Patching failed!')
        fileHandle = self._getFile('wb')
        fileHandle.write(patchedContents)
        fileHandle.close()
        del patchedContents
        return True

    def downloadPatch(self, patch, urls):
        urlsToTry = [ x for x in urls ]
        for url in urlsToTry:
            try:
                return self._downloadPatch(patch, url.decode('utf-8'))
            except Exception as e:
                print('Mirror %s failed integrity checks, removing... %s' % (url, e))
                urls.remove(url)

    def _downloadPatch(self, patch, url):
        if 'filename' not in patch or 'patchHash' not in patch or 'compPatchHash' not in patch:
            raise Exception('Patch descriptor is not fully qualified; it has missing parameters')
        patchfileDlHandle = urlopen(url + patch.get('filename'))
        patchfile = patchfileDlHandle.read()
        patchHash = self.__hash(patchfile)
        if patchHash != patch.get('compPatchHash'):
            raise Exception('Hash of downloaded and compressed patch was invalid!')
        patchfile = bz2.decompress(patchfile)
        if self.__hash(patchfile) != patch.get('patchHash'):
            raise Exception('Hash of downloaded and decompressed patch was invalid!')
        return patchfile

    def getPatch(self, patches):
        hash = self.currentHash()
        if hash in patches:
            return patches.get(hash)
        return

    def diff(self, oldFiles):
        if not os.path.exists(self.loc):
            print("Current version of file %s does not exist, aborting! You should've told me this file isn't managed any more :(" % self.name)
            exit(1)
        currentHash = self.currentHash()
        me = self.getContents()
        me = bz2.compress(me)
        compHash = self.__hash(me)
        compressedSelf = open(self.loc + '.bz2', 'wb')
        compressedSelf.write(me)
        compressedSelf.close()
        if not oldFiles:
            return {'hash': currentHash, 'dl': self.name + '.bz2', 'compHash': compHash, 'patches': {}}
        fileEntry = {'hash': currentHash, 'dl': self.name + '.bz2', 'compHash': compHash, 'patches': {}}
        for oldFile in oldFiles:
            oldFileHandle = oldFile._getFile('rb')
            if oldFileHandle is None:
                continue
            oldFileHandle.close()
            oldHash = oldFile.currentHash()
            if oldHash == currentHash:
                continue
            if oldHash in fileEntry['patches']:
                continue
            patchName = '%s_%s_to_%s.patch.bin' % (os.path.basename(self.name), oldHash[:5], currentHash[:5])
            print('Diffing file %s: %s/%s -> %s' % (self.name, oldFile.installBase, oldHash[:5], currentHash[:5]))
            patchPath = os.path.join(os.path.join(self.installBase, os.path.split(self.name)[0]), patchName)
            patchContents = bsdiff4.diff(oldFile.getContents(), self.getContents())
            patchHash = self.__hash(patchContents)
            patchContents = bz2.compress(patchContents)
            compPatchHash = self.__hash(patchContents)
            patchHandle = open(patchPath, 'wb')
            patchHandle.write(patchContents)
            patchHandle.close()
            fileEntry['patches'][oldHash] = {'filename': os.path.join(os.path.dirname(self.name), patchName), 'patchHash': patchHash, 'compPatchHash': compPatchHash}

        return fileEntry
