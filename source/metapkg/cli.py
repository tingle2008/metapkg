from .metapkg import Metapkg
from .utils import whoami
import click

MULTIPKG_VERSION='0.0.1'
init_metadata = {'actionlog':
                   [{'actor': whoami(),
                     'time' : '2022-04-15 16:20:10',
                     'type' : 'build',
                   'actions': 
                        [{'summary':'multipkg initialiation',
                          'text'   :"multipkg version: " + MULTIPKG_VERSION + "\n" + "invoked as : $0 join('',@ARGV)." + "\n",
                                  },],},],}

@click.command()
#@click.option('--count', default=1, help='Number of greetings.')
@click.argument('dirs', nargs= -1, type=click.Path(exists=True))
@click.option('-v', '--verbose', count = True , help='verbose mode. default off')
@click.option('-s', '--set', 'setstr', help='List of variables to set e.g.: a=b,c=d')
@click.option('--keepfiles/--no-keepfiles', default = False , help='Keep files after build')


def mkpkg(dirs,
          verbose,
          keepfiles,
          setstr):

    overrides = {}
    if setstr:
        seta = setstr.split(",")
        for l in seta:
            k,v = l.split('=',1)
            overrides[k] = v

    #TODO: split set_str to overrides
    print(setstr)
    for directory in dirs:
        mp = Metapkg(directory = directory,
                     cleanup   = not keepfiles,
                     force     = True,
                     warn_on_error = 1,
                     verbose  = verbose,
                     platform = 'ubuntu',
                     overrides = overrides,
                     meta = init_metadata )
        mp.build()
