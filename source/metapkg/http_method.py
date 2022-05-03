from os.path import exists,isdir

class Http():
    def __init__(self, directory  = None,
                       xfercmd    = None,
                       depositdir = None,
                       tmpdir     = None):
        self.directory  = directory
        self.xfercmd    = xfercmd
        self.depositdir = depositdir 
        self.tmpdir     = tmpdir


    def pull(self,url):
        return ['tarball': '/package.tgz']
