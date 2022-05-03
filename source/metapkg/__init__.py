__version__ = '0.0.1'

def test_build_package():

    MULTIPKG_VERSION='0.0.1'
    init_metadata = {'actionlog':
                        [{'actor': 'yuting', #whoami()
                          'time' : '2022-04-15 16:20:10',
                          'type' : 'build',
                          'actions': 
                                [{'summary':'multipkg initialiation',
                                  'text'   :"multipkg version: " + MULTIPKG_VERSION + "\n" + "invoked as : $0 join('',@ARGV)." + "\n",
                                  },],},],}

    #mp = Metapkg(directory = '/home/yuting/metapkg/test_pkg',
    mp = Metapkg(directory = 'test_pkg',
                 cleanup   = True,
                 force     = True,
                 warn_on_error = 1,
                 verbose  = 0,
                 platform = 'ubuntu',
                 overrides = {},
                 meta = init_metadata
                 )
    mp.makepackage()
