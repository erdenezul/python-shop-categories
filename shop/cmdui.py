# -*- coding: utf-8 -*-
"""
This module defines a command line interface for working with this shop model.
"""

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

    def help_help(self):
        print("""With no arguments help lists all available commands,
If a command is given as an argument the help for that command is displayed.""")

    def do_EOF(self, line):
        "Exit the application on end of file."
        print("  ") # Cover up the ^D char
        self.do_exit()

    def do_exit(self, line=None):
        "Exit the application."
        print("bye.")
        sys.exit()

    def emptyline(self):
        pass

    def default(self, line):
        command, args, line = self.parseline(line)
        print("unknown command: %s" % command)

    def do_list(self, line):
        "list all available products in the current category"
        with self.store.graphdb.transaction:
            for product in self.category:
                print(product)

    def do_cat(self, line=None):
        """Change the current category and list all subcategories.
        The parameter to this command is the name of the subcategory
        to change to, .. changes to the parent category.
        If no parameter is given cat only lists the subcategories.
        """
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

    def do_sample(self, line):
        """Create an example set of data."""
        weight = self.store.attribute.type("Weight", Unit="Kg")
        count = self.store.attribute.type("Count", Unit="pcs.")
        length = self.store.attribute.type("Length", Unit='"')
        frequency = self.store.attribute.type("Frequency", Unit="MHz")
        name = self.store.attribute.type("Name", Unit="")
        currency = self.store.attribute.type("Currency", Unit="USD")

        electronics = self.store.root.new_subcategory(
            "Electronics", Name=Attribute(name), Price=Attribute(currency),
            Weight=Attribute(weight))

        cameras = electronics.new_subcategory("Cameras")

        computers = electronics.new_subcategory("Computers", **{
                'Shipping weight':Attribute(weight),
                'CPU frequency':Attribute(frequency)})

        desktops = computers.new_subcategory("Desktops", **{
                'Expansion slots':Attribute(count, default=4)})

        laptops = computers.new_subcategory("Laptops", **{
                'Display size':Attribute(length, default=15.0)})

        desktops.new_product(Name="Dell Desktop",
                             Weight=17.1,
                             Price=890.0,
                             **{'Shipping weight': 22.3,
                                'CPU frequency': 3000.0})

        laptops.new_product(Name="HP Laptop",
                             Weight=3.5,
                             Price=1200.0,
                             **{'Shipping weight': 6.3,
                                'CPU frequency': 2000.0})

    _make_usage = "USAGE: make %s [<key>:<value> ...]"
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
            print(self._make_usage % ("|".join(self._makers),))

    def help_make(self):
        print(self._make_usage % ("|".join(self._makers),))
        print("")
        for maker in self._makers:
            print("make %s:" % (maker,))
            print("    " + getattr(self, 'make_'+maker).__doc__)

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
        """Creates a new category.
        A 'Name' parameter must be specified for the category.
        The rest of the parameters are names and types of the attributes of
        the products in the category.
        """
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
        """Creates a new product.
        The supplied key value pairs are the attribute values for the product.
        """
        try:
            self.category.new_product(**attributes)
        except:
            import traceback; traceback.print_exc()

    def make_type(self, attributes):
        """Creates a new attribute type.
        A 'Name' parameter must be specified for the attribute type.
        """
        try:
            name = self._make_required(attributes, 'name', 'Name')
        except KeyError:
            print("ERROR: missing required attribute 'name'")
        try:
            self.store.attribute.type(name, **attributes)
        except TypeError:
            _,val,_ = sys.exc_info()
            print(val)

    _makers = tuple(name[5:] for name in dir() if name.startswith('make_'))

    def do_types(self, line):
        "List all available attribute types."
        pass

def start(*args, **params):
    ui = CommandLineUi( Store(params['store']) )
    ui.cmdloop()
    
