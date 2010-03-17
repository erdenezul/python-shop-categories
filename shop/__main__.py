# -*- coding: utf-8 -*-

if __name__ != '__main__': raise ImportError

import sys, os, copy
from optparse import OptionParser, Option

this_dir = os.path.dirname(os.path.abspath(__file__))
path_dir = os.path.dirname(this_dir)
for path in sys.path:
    if os.path.abspath(path) == path_dir: break
else:
    for i, path in enumerate(sys.path):
        if os.path.abspath(path) == this_dir:
            sys.path[i] = path_dir
            break
    else:
        sys.path.append(os.path.dirname(this_dir))

class ShopOption(Option):
    these_actions = ('import','dir')
    ACTIONS = Option.ACTIONS + these_actions + ('runtest',)
    STORE_ACTIONS = Option.STORE_ACTIONS + these_actions
    TYPED_ACTIONS = Option.TYPED_ACTIONS + these_actions
    ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + these_actions
    del these_actions

    def take_action(self, action, dest, opt, value, values, parser):
        ui = 'ui'
        if action == 'runtest':
            action = 'import'
            value = 'test'
            dest = 'ui'
            ui = ''
        if action == 'import':
            environ = {}
            exec("from shop import %s%s as module" % (value,ui), environ)
            setattr(values, dest, environ['module'])
        elif action == 'dir':
            setattr(values, dest, os.path.abspath(value))
        else:
            Option.take_action(self, action, dest, opt, value, values, parser)

class DummyUI(object):
    def __init__(self, module):
        self.module = module
    def start(self, *args, **params):
        environ = {}
        exec("from shop.%sui import start" % (self.module,), environ)
        return environ['start'](*args, **params)

parser = OptionParser(option_class=ShopOption)
parser.add_option('--ui', dest="ui", action="import", default=DummyUI("cmd"),
                  help="the UI to launch", metavar="NAME")
parser.add_option('--store', dest="store", action="dir",
                  default=os.path.abspath('storedb'), metavar="DIR",
                  help="the store directory")
parser.add_option('--test', action="runtest", help="run tests")

options, args = parser.parse_args()

params = copy.copy(options.__dict__)
del params['ui']

options.ui.start(*args, **params)
