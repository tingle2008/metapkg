from .utils import rel2abs,whoami
from abc import ABCMeta,abstractmethod
from dataclasses import dataclass,field

import os,re,time
from os.path import exists,isdir

import pprint
pp = pprint.PrettyPrinter(indent=4)

MULTIPKG_VERSION='0.0.1'

# *state pattern*为了维护一个状态机器构建一个Info类存状态信息。
import yaml

@dataclass
class Info():
    directory: str 
    confdir:   str = None
    scripts:   str = None
    platform:  str = None
    overrides: dict = field(default_factory = dict)
    data:      dict = field(default_factory = dict)
    meta:      dict = field(default_factory = dict)

    def __post_init__(self):

        data = {}
        table = {}

        for yaml_conf in [ self.confdir + "/default.yaml", self.directory + "/index.yaml" ]:
            if not exists(yaml_conf):
                continue

            try:
                with open(yaml_conf,"r") as conf_stream:
                    table = yaml.safe_load ( conf_stream )
            except yaml.YAMLError as exc :
                print("Error in configuration file:", exc)

            #XXX log info:
            print("LOADING", yaml_conf)

            for t1_key in table.keys():
                if t1_key in data:
                    data[t1_key] = data[t1_key]
                else:
                    data[t1_key] = {}

                for t2_key in table[t1_key].keys():
                    data[t1_key][t2_key] = table[t1_key][t2_key]

        dirname = self.directory.split(os.sep)[-1]

        if dirname != '.' and dirname != '':
            if 'name' in data['default']:
                data['default']['name'] = data['default']['name']
            else:
                data['default']['name'] = dirname

        platforms = self.platforms()

        for base in platforms:  #1197

            basedir = self.directory + "/" + base
            if base == 'default':
                basedir = self.directory 
            basedir = rel2abs( basedir )
            
            try:
                with os.scandir(basedir) as dir_:
                    # other platform name
                    #assert 'name' not in data[base]
                    name = data[base]['name']
                    for entry in dir_:
                        if entry.name.startswith('.'):
                            continue
                        if entry.is_file():
                            e = re.compile("^{}-([\d\.]+)\.tar\.(gz|bz2)".format(name)).match(entry.name)
                            if e:
                                if 'sourcetar' not in data[base]:
                                    data[base]['sourcetar'] = '{b}/{d}'.format(b = basedir,d = entry.name)
                                if 'version' not in data[base]:
                                    data[base]['version'] = '{}'.format(e.group(1))
                                
                        if entry.is_dir():
                            e = re.compile('^{}-([\d\.]+)$'.format(name)).match(entry.name)
                            if e:
                                if 'sourcedir' not in data[base]:
                                    data[base]['sourcedir'] = '{b}/{d}'.format(b = basedir,d = entry.name)
                                if version not in data[base]:
                                    data[base]['version'] = '{}'.format(e.group(1))

                    if 'sourcedir' not in data[base]:
                        data[base]['sourcedir'] = '{b}/source'.format(b = basedir)
                    if 'rootdir'  not in data[base]:
                        data[base]['rootdir'] = '{b}/root'.format(b = basedir)

                    #1229
                    suffix = ['.tar.gz','.tgz','.tar.bz2','.tbz','.tar.xz']
                    sourcetar = ['{b}/source{s}'.format(b = basedir,s = x) for x in suffix if exists('{b}/source{s}'.format(b = basedir,s = x))]
                    roottar = ['{b}/root{s}'.format(b = basedir,s = x) for x in suffix if exists('{b}/root{s}'.format(b = basedir,s = x))]
                    
                    if sourcetar and 'sourcetar' not in data[base]:
                        data[base]['sourcetar'] = sourcetar.pop(0)

                    if roottar and 'roottar' not in data[base]:
                        data[base]['roottar'] = roottar.pop(0)
                    
                    # what's up? no 
                    for srdt in ['sourcedir','rootdir','sourcetar','roottar']:
                        if not (base in data and srdt in data[base]):
                            continue
                        if re.match('/', data[base][srdt]):
                            continue
                        srdt_fullname = "{b}/{d}".format(b = basedir,d = data[base][srdt])
                        if (exists(srdt_name)):
                            data[base][srdt] = srdt_fullname
                    
            except FileNotFoundError as err:
                pass

        finaldata = {}

        for plat in platforms:
            if plat in data:
                for platdata in data[plat]:
                    finaldata[platdata] = data[plat][platdata]

        if 'packagetype' not in finaldata:
            finaldata['packagetype']='tarball'
            for plat in platforms[::-1]:
                if plat == 'gem':
                    finaldata['packagetype'] = 'gem'
                if plat == 'rpm':
                    finaldata['packagetype'] = 'rpm'
                if plat == 'deb':
                    finaldata['packagetype'] = 'deb'

        # get scripts
        scriptdirs = [ '{directory}/{f}/scripts'.format(directory = self.directory,f=x) for x in platforms if x != 'default' ]
        scriptdirs.insert(0, '{directory}/scripts'.format(directory = self.directory))
        scriptdirs.insert(0, '{directory}/scripts'.format(directory = self.confdir))

        scripts = {}

        for dir_ in scriptdirs:
            dir_ = rel2abs(dir_)
            try:
                with os.scandir(dir_) as d:
                    for entry in d:
                        if re.compile('^\.').match(entry.name):
                            continue
                        if not exists('{}/{}'.format(dir_,entry.name)):
                            continue
                        scripts[entry.name] = '{}/{}'.format(dir_,entry.name)

            except FileNotFoundError as err:
                pass

        if 'conflicts' not in finaldata:
            finaldata['conflicts'] = []
        if 'provides'  not in finaldata:
            finaldata['provides'] = []
        if 'requires'  not in finaldata:
            finaldata['requires'] = []
        if 'obsoletes'  not in finaldata:
            finaldata['obsoletes'] = []

        # if scripts have run.. then we need  daemontools required
        if 'run' in scripts:
            finaldata['requires'].append('daemontools');
            if 'post.sh' not in scripts:
                scripts['post.sh'] = scripts['supervisepost.sh']
            if 'preun.sh' not in scripts:
                scripts['preun.sh'] = scripts['supervisepreun.sh']

        #new = dict.fromkeys(finaldata['conflicts'],1)
        #1304 - 1320 ignore ,don't know why

        finaldata['conflictlist'] = ', '.join(finaldata['conflicts'])
        finaldata['providelist']  = ', '.join(finaldata['provides'])
        finaldata['requirelist']  = ', '.join(finaldata['requires'])
        finaldata['obsoletelist'] = ', '.join(finaldata['obsoletes'])

        for k in self.overrides:
            finaldata[k] = self.overrides[k]

        if 'author' not in finaldata:
            finaldata['author'] = 'nobody@null'

        if 'url' not in finaldata and 'srcurl' in finaldata:
            finaldata['url'] = finaldata['srcurl']

        if 'url' not in finaldata:
            finaldata['url'] = ''

        finaldata['whoami'] =  whoami()

        print("--------final data info-----------")
        pp.pprint(finaldata)

        self.data = finaldata
        self.scripts = scripts

        init_meta = self.meta
        self.meta = {}

        mdir = self.directory + '/meta'
        if isdir(mdir):
            try:
                with os.scandir(mdir) as d:
                    for entry in d:
                        if entry.is_file():
                            self.mergemeta('{}/{}'.format(mdir,entry.name))
                    
            except FileNotFoundError as err:
                pass
        if init_meta:
            self.mergemeta(init_meta)

        metapkg_init_metadata = {'actionlog':
                                    [{'actor' : finaldata['whoami'],
                                       'time' : time.asctime(time.localtime(time.time())),
                                       'type' : 'build',
                                        'actions': 
                                        [{'summary':':Metapkg Info initialization',
                                            'text'   :"metapkg version: " + MULTIPKG_VERSION + "\n",
                                            },],},],}

        self.mergemeta(metapkg_init_metadata)

        print("--------meta info-----------")
        pp.pprint(self.meta)

    def mergemeta(self,merge):
        d = {}
        if isinstance(merge,str):
            try:
                with open(merge, "r") as meta_stream:
                    d = yaml.safe_load ( meta_stream )
            except yaml.YAMLError as exc :
                print("Error in configuration file:", exc)
        else:
            d = merge
        self._merge_tree(self.meta,d)
    
    @staticmethod
    def _merge_tree(into_,from_):
        for key in from_:
            if isinstance(from_[key],dict):
                if key not in into_:
                    into_[key] = {}
                if not isinstance(into_[key],dict):
                    sys.exit("can not merge hash into non hash")
                _merge_tree(into_,from_)
            elif isinstance(from_[key],list): 
                if key not in into_:
                    into_[key] = []
                if not isinstance(into_[key],list):
                    sys.exit("can not merge hash into non hash")
                into_[key].extend(from_[key])
            else:
                into_[key] = from_[key]

    def platforms(self):
        #TODO: more detection by scripts.

        platforms=[]
        # `uname`
        platforms.append('Linux')
        # `uname -m`
        platforms.append('x86_64')
        # -f /etc/issue
        platforms.append('ubuntu')
        platforms.append('deb')
        platforms.append('override')
        if self.platform:
            platforms.append(self.platform)
        
        #like perl unshift. #1452
        platforms.insert(0,'default')

        return(platforms)

    # dumb data merger: recurses into hash trees
    # array types are concatenated, scalars overwrite each other


