from .utils import rel2abs,whoami
from .info import Info
from abc import ABCMeta,abstractmethod
from typing import Any,Dict
from dataclasses import dataclass,field
import os,re,time
import tempfile
from os.path import isdir,isfile

import shlex, subprocess

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

class Builder(metaclass = ABCMeta):
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
        if re.search('\.(tar\.gz|tgz)$',tarball):
            opt_str = 'zxf'
        if re.search('\.(tar\.bz2|tbz)$',tarball):
            opt_str = 'jxf'
        if re.search('\.(tar\.xz)$',tarball):
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

        if self.force != 1:
            sys.exit("FATAL (use --force to override):", msg)
        # use loginfo
        print("WARN:", msg)

    def template_file(self,fm,to,chmod):
        string = self.template_string(fm)
        '''
  open my $f, ">$to";
  print $f $str;
  close $f;
  chmod $chmod, $to if ( defined $chmod );
        '''
    def template_string(self, fm):
        '''
        XXX todo
        '''
        return ''

    def substvars(self, buf):
        '''
        XXX 字符串替换.
        '''
        return ''

    @abstractmethod
    def isMatch(self):
        "状态的属性pkgInfo是否在当前的状态范围内"
        pass

    @abstractmethod
    def makepackage(self):
        pass

    def install_gemspec(self):
        return  True

    def cleanup(self):
        print("Info: Cleaning up..." + self.tmpdir )
        os.system( "rm -rf " + self.tmpdir )

    def _listfile(self):
        return True

    def listdir(self):
        return []

    def runcmd(self, cmd, env = {}, count = 10):
        
        print("RUNNING:", cmd)
        last = []

        args = shlex.split(cmd)
        print("split args:",args)
        p = subprocess.Popen(args, 
                             shell=True, 
                             env = env,
                             universal_newlines=True,
                             bufsize = 1,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)

        while True:
            output = p.stdout.readline()
            if not output:
                break
            if output:
                last.append(output.strip())
                if len(last) > count:
                    last.pop(0)

            if self.verbose:
                print(output.strip().decode("utf-8"))

        if p.wait() != 0:
            print("Build failed", "\n".join(last))
            raise Exception(cmd)

        return last

    def fetch(self):
        return True

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

        os.chdir( info.directory )
        realbuild = self.builddir

        # fetch source from remote
        # XXX
        self.fetch()

        if 'sourcedir' in info.data and isdir(info.data['sourcedir']):
            print("INFO: Building from" . info.data['sourcedir'])
            os.system( "cd "   + 
                        info.data['sourcedir'] + 
                        " && " + 
                        "tar cf - . | tar xf - -C " + 
                        self.builddir )
        elif 'sourcetar' in info.data and isfile(info.data['sourcetar']):
            print("INFO: Building from" + info.data['sourcetar'])
            tar_opt = self.taroption(info.data['sourcetar'])
            os.system( "tar " +
                       tar_opt + " " + 
                       info.data['sourcetar'] + 
                       " -C " + self.builddir )
            with os.scandir( self.builddir ) as d:
                for entry in d:
                    if re.match( '^\.', entry.name):
                        continue
                    if entry.is_dir():
                        realbuild = self.builddir + "/" + entry.name
        else:
            print("ERROR: do not found real build dir.")
            return

        destdir = self.installdir
        prefix  = '/usr'
        if 'buildprefix' in info.data:
            prefix = info.data['buildprefix']

        perl = '/usr/bin/perl'
        if 'perl' in info.data:
            perl = info.data['perl']

        os.chdir( realbuild )
        self._vars['BUILDDIR'] = realbuild

        patchdir = info.directory + '/patches';
        patches  = []

        if isdir(patchdir):
            print("Applying patches")
            with os.scandir( patchdir ) as d:
                for entry in d:
                    if re.match('^\.', entry.name ):
                        continue
                    if entry.is_file():
                        patches.append( entry.name )

            for patch in patches.sort():
                print("Applying:",patch);
                self.runcmd( "patch --ignore-whitespace -p 1 -d . <" + patchdir + "/" + patch )

        env = os.environ.copy()
        env['PERL'] = perl
        env['INSTALLROOT'] = env['DESTDIR'] = destdir
        env['PREFIX'] = prefix
        env['PKGVERID'] = self.pkgverid()
        env['PACKAGEVERSION'] = info.data['version']
        env['PACKAGENAME'] = info.data['name']

        if 'gem' in info.data and 'gembuild' in info.scripts:
            self.runcmd(info.scripts['gembuild'],env)
        else:
            # how to deal with gem?
            try:
                self.runcmd( info.scripts['build'], env )
            except Exception as e:
                msg = "Error running:" + e.args[0]
                print(msg)
                return msg

        os.chdir( self.cwd )

    def verify_data(self,root):
        return True

    def shebangmunge(self,dirname):
        return True

    def transform(self, installdir):
        return True

    def copyroot(self):
        '''copy root to install dir'''
        installdir = self.installdir
        if 'rootdir' in self.info.data and isdir(self.info.data['rootdir']):
            print("INFO: Using " . self.info.data['rootdir'])
            os.system("cd " + self.info.data['rootdir'] + " && " + "tar cf - --exclude \.svn --exclude \.git . | tar xf - -C " + installdir )
        elif 'roottar' in self.info.data and isfile(self.info.data['roottar']):
            print("INFO: Using " . self.info.data['roottar'])
            tar_opt = self.taroption(self.info.data['roottar'])
            os.system("tar " + tar_opt + " " + self.info.data['roottar'] + " -C " + installdir)

        # install daemontools service

        if 'run' in self.info.scripts and 'logrun' in self.info.data:
            print("Next etc....XXX")
        
        return True

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
