# -*- coding: utf-8 -*-

import sys
import os
import traceback

from shop import Store


def start(*args, **params):
    storedir = os.path.join(params['store'],'test')

    paths = []
    for path, dirs, files in os.walk(storedir):
        paths.append(path)
        for f in files:
            os.remove(os.path.join(path,f))
    paths.reverse()
    for path in paths:
        os.rmdir(path)

    store = Store(storedir)

    if args:
        for arg in args:
            try:
                run(store, arg)
            except:
                print('no such test case: "%s"' % (arg,))
    else:
        for filename in os.listdir(os.path.dirname(__file__)):
            if filename.endswith('.py') and not filename.startswith('_'):
                run(store, filename[:-3])


def run(store, test):
    environ = {}
    exec("from shop.test.%s import *" % (test,), environ)
    for name, case in environ.items():
        if not name.startswith('_'):
            runtest(store, '%s.%s' % (test, name), case)


def runtest(store, name, case):
    try:
        case(store)
    except AssertionError:
        _,val,tb = sys.exc_info()
        message = val.message
        print('%s: FAILED   %s' % (name, message))
    except:
        print('%s: ERROR!' % (name,))
        traceback.print_exc()
    else:
        print('%s: PASSED' % (name,))
