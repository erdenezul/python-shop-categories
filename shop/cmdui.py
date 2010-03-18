# -*- coding: utf-8 -*-

import cmd
import sys

from shop import Store

class CommandLineUi(cmd.Cmd):
    def __init__(self, store):
        cmd.Cmd.__init__(self)
        self.__store = store
        self.prompt = "%s> " % (store.name,)
        self.category = store.root

    def do_EOF(self, line):
        print("  ") # Cover up the ^D char
        self.do_exit()

    def do_exit(self, line=None):
        print("bye.")
        sys.exit()

    def emptyline(self):
        pass

    def default(self, line):
        command, args, line = self.parseline(line)
        print("unknown command: %s" % command)

    def do_list(self, line):
        "list all available products"
        for product in self.category:
            print(product)

    def do_cat(self, line):
        if line:
            try:
                pass
            except:
                pass
        else:
            for category in self.category.categories:
                print(category)

    def do_make(self, line):
        command, args, line = self.parseline(line)
        if command:
            cmd = getattr(self, 'make_' + command, None)
            if cmd is None:
                print("Cannot make %s" % (command,))
            else:
                cmd(args)

    def make_category(self, line):
        pass

    def make_product(self, line):
        pass

def start(*args, **params):
    ui = CommandLineUi( Store(params['store']) )
    ui.cmdloop()
    
