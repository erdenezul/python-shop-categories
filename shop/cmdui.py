# -*- coding: utf-8 -*-

from __future__ import with_statement

import cmd
import sys
import re

from shop import Store
from shop.model import Attribute

class CommandLineUi(cmd.Cmd):
    def __init__(self, store):
        cmd.Cmd.__init__(self)
        self.store = store
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
        with self.store.graphdb.transaction:
            for product in self.category:
                print(product)

    def do_cat(self, line=None):
        if line:
            if line == '..':
                self.category = self.category.parent
            else:
                try:
                    self.category = self.category[line]
                except:
                    print("No such category %r" % (line,))
        else:
            print("Current category: %s" % (self.category,))
            self.columnize(map(str, self.category.categories))

    _make_usage = "USAGE: make %s [<key>:<attr type> ...]"
    def do_make(self, line):
        command, args, line = self.parseline(line)
        if command:
            cmd = getattr(self, 'make_' + command, None)
            if cmd is None:
                print("Cannot make %s" % (command,))
            else:
                try:
                    cmd(self._make_attributes(args))
                except ValueError:
                    print(self._make_usage % (command,))
        else:
            print(self._make_usage % ("category|product|type",))

    _make_pattern = re.compile(r'^\s*(\w+):((?:"(?:[^"]*(?:\\")?)*")|(?:\w+))')
    def _make_attributes(self, line):
        attributes = {}

        while line:
            # There is a bug in Jython's re module that prevents the use of '"'
            match = self._make_pattern.match(line)
            if match is None: raise ValueError

            key, value = match.groups()
            if value.startswith('"'): value = value[1:-1]
            attributes[key] = value

            line = line[len(match.group()):].strip()

        return attributes

    def _make_required(self, attributes, *keys):
        for key in keys:
            value = attributes.pop(key, None)
            if value is not None: break
        else:
            raise KeyError
        return value

    def make_category(self, attributes):
        try:
            name = self._make_required(attributes, 'name', 'Name')
        except KeyError:
            print("ERROR: missing required attribute 'name'")
        try:
            attributes = dict([(key,Attribute(self.store.attribute.type[value]))
                               for key, value in attributes.items()])
        except KeyError:
            print("ERROR: the attribute type %r is not defined.\n"
                  "       Use 'make type' to define it." % (key,))
        self.category = self.category.new_subcategory(name, **attributes)
        self.do_cat()

    def make_product(self, attributes):
        try:
            self.category.new_product(**attributes)
        except:
            import traceback; traceback.print_exc()

    def make_type(self, attributes):
        try:
            name = self._make_required(attributes, 'name', 'Name')
        except KeyError:
            print("ERROR: missing required attribute 'name'")
        try:
            self.store.attribute.type(name, **attributes)
        except TypeError:
            _,val,_ = sys.exc_info()
            print(val)

    def do_types(self, line):
        pass

def start(*args, **params):
    ui = CommandLineUi( Store(params['store']) )
    ui.cmdloop()
    
