from .utils import rel2abs,whoami
from .info import Info
from abc import ABCMeta,abstractmethod
from typing import Any,Dict
from dataclasses import dataclass,field
import os,re,time
import tempfile
from os.path import exists,isdir

import pprint

pp = pprint.PrettyPrinter(indent=4)

MULTIPKG_VERSION='0.0.1'

class BuildContext(metaclass = ABCMeta):
  
    def __init__( self ):
        self.__pkgBuilders = []
        self.__curPkgBuilder = None
        self.__pkgInfo = None

    def error(self,msg):
        print("error msg is:", msg)
        return(1)

    def addPkgBuilder(self, pkgBuilder ):
        if( pkgBuilder not in self.__pkgBuilders ):
            self.__pkgBuilders.append( pkgBuilder )

    def _getPkgInfo(self):
        return(self.__pkgInfo)

    def changePkgBuilder(self,pkgBuilder):
        if (pkgBuilder is None):
            return False
        if (self.__curPkgBuilder is None):
            print("初始化为",pkgBuilder.getName())
        else:
            print(self.__curPkgBuilder.getName(),"->", pkgBuilder.getName())

        self.__curPkgBuilder = pkgBuilder
        self.addPkgBuilder(pkgBuilder)
        return True

    def getPkgBuilder(self):
        return self.__curPkgBuilder

    def setPkgBuilderInfo(self, pkgInfo):
        self.__pkgInfo = pkgInfo
        for pkgbuilder in self.__pkgBuilders:
            if (pkgbuilder.isMatch(pkgInfo)):
                self.changePkgBuilder(pkgbuilder)
                pkgbuilder.setPkgInfo(pkgInfo)

def singleton(cls, *args, **kwargs):
    "构造一个单例的装饰器"
    instance = {}

    def __singleton(*args, **kwargs):
        if cls not in instance:
            instance[cls] = cls(*args, **kwargs)
        return instance[cls]
    return __singleton

class Builder:
    """包状态的基类"""
    def __init__(self, 
                 verbose    = 0, 
                 tmpdir     = None, 
                 force      = 0, 
                 builddir   = None, 
                 cwd        = None,
                 installdir = None ):
        self.verbose  = verbose
        self.tmpdir   = tmpdir
        self.force    = force
        self.builddir = builddir
        self.cwd      = cwd
        self.installdir = installdir


        self.info    = {}
        self._vars={}
        self._rules = {}

    def getName( self ):
        return self.__class__.__name__

    def getInfo( self ):
        return self.info

    def setPkgInfo( self, pkgInfo ):
        self.info = pkgInfo
        self.setrelease()
        self._rules = self.get_file_rules()

    def taroption(self,tarball):
        opt_str = ''
        if re.match('\.(tar\.gz|tgz)$',tarball):
            opt_str = 'zxf'
        if re.match('\.(tar\.bz2|tbz)$',tarball):
            opt_str = 'jxf'
        if re.match('\.(tar\.xz)$',tarball):
            opt_str = 'Jxf'
        return opt_str

    def setrelease(self):

        if 'release' not in self.info.data:
            self.info.data['release'] =  '{:.2f}'.format(time.time())
        elif re.match('p4v',self.info.data['release']):
            print("launch p4 \n")
            self.info.data['release'] =  'todoP4' 
        elif re.match('gitv',self.info.data['release']):
            print("launch git \n")
            self.info.data['release'] =  'todoGit' 

        if os in self.info.data:
            self.info.data['release'] = self.info.data['release'] + '.' + self.info.data['os']

    def pkgverid(self):

        return '-'.join((
                self.info.data['name'],
                self.info.data['version'],
                self.info.data['release']))

    def forceok(self,msg):
        return False
        #if not 


    def isMatch(self):
        "状态的属性pkgInfo是否在当前的状态范围内"
        return False

    def cleanup( self ):
        print("Info: Cleaning up..." + self.tmpdir )
        os.system( "rm -rf " + self.tmpdir )

    def build(self):

        info = self.getInfo()

        self.tmpdir   = tempfile.mkdtemp(prefix='metapkg-')
        self.builddir   = self.tmpdir + "/build"
        self.installdir = self.tmpdir + "/install"

        try:
            os.mkdir(self.builddir)
            os.mkdir(self.installdir, mode = 0o755)
        except OSError as error:
            sys.exit("Unable to mkdir", error)

        self.setrelease()
        os.chdir( info.directory )
        realbuild = self.builddir

        # fetch source from remote
        # XXX
        self.fetch()

    def get_file_rules(self):
        ''' not done yet '''
        ''' 通过设计文件内容 '''
        return ['f1','f2']

    def fetch(self):

        info = self.getInfo()
        target = None

        if ( 'cpan-module' in info.data ):
            target = info.data['cpan-module']
            print("INFO:cpan command required", target)
            pass
        elif('http' in info.data):
            target = info.data['http']
            try:
                from .http_method import Http
            except ImportError as e:
                print("INFO:import failed:", e)

            agent = Http( xfercmd    = self.info.data[xfercmd] ,
                          depositdir = self.tmpdir + "/source" ,
                          tmpdir      = self.tmpdir )
            try:
                res_hash = agent.pull(target)
            except HttpFetchError as e:
                print("INFO:import failed:", e)
        else:
            pass

    def copyroot(self):
        installdir = self.installdir
        print("in copyroot... ", installdir)

    def transform(self):
        print("in transform... ")

    def verify_data(self):
        print("in verify_data... ")
        return True

    @abstractmethod
    def makepackage(self, pkgInfo):
        pass

@singleton
class Rpm(Builder):
    def __init__(self,  verbose    = 0, 
                        tmpdir     = None, 
                        force      = 0, 
                        builddir   = None, 
                        cwd        = None,
                        installdir = None ):
        super().__init__(verbose, tmpdir, force, builddir, cwd, installdir)

    def isMatch(self,pkgInfo):
        return pkgInfo.data['packagetype'] == 'rpm'

    def makepackage( self ):
        print("making package..")

@singleton
class Deb(Builder):
    def __init__(self,  verbose    = 0, 
                        tmpdir     = None, 
                        force      = 0, 
                        builddir   = None, 
                        cwd        = None,
                        installdir = None ):
        super().__init__(verbose, tmpdir, force, builddir, cwd, installdir)

    def isMatch(self,pkgInfo):
        return pkgInfo.data['packagetype'] == 'deb'

    def makepackage( self ):
        print("making debian package..")

@singleton
class Tarball(Builder):
    def __init__(self,  verbose    = 0, 
                        tmpdir     = None, 
                        force      = 0, 
                        builddir   = None, 
                        cwd        = None,
                        installdir = None ):
        super().__init__(verbose, tmpdir, force, builddir, cwd, installdir)

    def isMatch(self,pkgInfo):
        return pkgInfo.data['packagetype'] == 'tarball'

    def makepackage( self ):
        print("makeing package..")

class Metapkg( BuildContext ):
    def __init__(
            self,
            startdir = None,
            directory = None,
            confdir = '/usr/share/multipkg',
            info = None,
            cleanup = False,
            cwd = None,
            overrides = {},
            meta = None,
            force = 0,
            platform = None,
            warn_on_error = 0,
            verbose = 0
            ):
        super().__init__()

        self.cwd = os.getcwd()
        self.overrides = overrides
        self.platform  = platform
        self.directory = rel2abs( re.sub('/$','',directory ) )
        self.startdir  = startdir
        self.verbose   = verbose
        self.confdir   = confdir 
        self.meta      = meta
        self.cleanup   = cleanup
        self.force     = force

        self.info = Info (
                        overrides = self.overrides,
                        platform  = self.platform,
                        directory = self.directory,
                        confdir   = self.confdir,
                        meta      = self.meta )

        # 动物园加入各种动物一样. 开闭原则上看. 如果添加新的bulder 只要新增builder 就好了
        # self.addPkgBuilder 之后直接调用build 就好。
        self.addPkgBuilder(Deb( verbose = self.verbose,
                                force   = self.force,
                                cwd     = self.cwd ))
        self.addPkgBuilder(Rpm( verbose = self.verbose,
                                force   = self.force,
                                cwd     = self.cwd ))
        self.addPkgBuilder(Tarball( verbose = self.verbose,
                                    force   = self.force,
                                    cwd     = self.cwd ))
        self.setPkgBuilderInfo( self.info )

    def build(self):

        builder = self.getPkgBuilder()
        builder.build()
        builder.copyroot()
        builder.transform()

        if builder.verify_data() or builder.forceok("Finished package contains no files"):
            pass

        metapkg_init_meta = {'actionlog':
                             [{'actor' : self.info.data['whoami'],
                               'time' : time.asctime(time.localtime(time.time())),
                               'type' : 'build',
                                        'actions': 
                                         [{'summary':':Metapkg build complete',
                                           'text'   :"metapkg version: ",
                                          },],},],}

        self.info.mergemeta(metapkg_init_meta)

        pkg = builder.makepackage()

        if self.cleanup:
            builder.cleanup()
        else:
            print("Not cleaning up:" + builder.tmpdir + "\n")

        return( pkg )
