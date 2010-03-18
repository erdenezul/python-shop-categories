# -*- coding: utf-8 -*-

from __future__ import with_statement

if __name__ == '__main__':
    import os, sys
    with open(os.path.join(os.path.dirname(__file__),'__main__.py')) as module:
        exec(module)
    sys.exit()

import neo4j

from neo4j.util import Subreference

from shop import model


class _descriptor(type):
    def __get__(categories, store, cls=None):
        if store is None:
            return None
        return categories(store)
    def __set__(categories, store, value):
        raise TypeError("cannot assign to categories")


class Store(object):

    def __init__(self, storedir, storename="Products"):
        self.__graphdb = neo4j.GraphDatabase(storedir)
        self.__name = storename

    name = property(lambda self: self.__name)
    graphdb = property(lambda self: self.__graphdb)

    __root = None
    @property
    def root(self):
        root = self.__root

        if root is None:

            with self.graphdb.transaction:
                root = model.Category(
                    self.graphdb,
                    Subreference.Node.CATEGORY_ROOT(self.graphdb,
                                                    Name=self.__name))

            self.__root = root

        return root

    class categories(object):
        __metaclass__ = _descriptor
        def __init__(self, store):
            self.store = store

        @property
        def __categories(self):
            try:
                categories = self.store.__categories
            except:
                categories = None
            if categories is None:
                self.store.__categories = categories = {}
            return categories

        def __iter__(self):
            for node in model.SubCategories(self.__root):
                category = model.Category(self.store.graphdb, node)
                self.__categories[category.name] = category
                yield category

        @property
        def __root(self):
            return Subreference.Node.CATEGORY_ROOT(self.store.graphdb,
                                                   Name=self.store.name)

        def __getitem__(self, key):
            category = self.__categories.get(key)
            if category is None:
                with self.store.graphdb.transaction:
                    for category in self:
                        if category.name == key: break
                    else:
                        raise KeyError("No such category '%s'." % (key,))
            return category

        def __call__(self, *args, **kwargs):
            return self.store.root.new_subcategory(*args, **kwargs)

    class attribute(object):
        __metaclass__ = _descriptor
        def __init__(self, store):
            self.store = store

        class type(object):
            __metaclass__ = _descriptor
            def __init__(self, attr):
                self.attr = attr
            store = property(lambda self: self.attr.store)

            def __getitem__(self, key):
                type = self.__types.get(key)
                if type is None:
                    for type in self.__all:
                        if type.name == key: break
                    else:
                        raise KeyError("No such attribute type: %r" % (key,))
                return type

            def __call__(self, *args, **kwargs):
                return model.AttributeType.create(self.store.graphdb,
                                                  self.__node,
                                                  *args, **kwargs)

            @property
            def __node(self):
                return Subreference.Node.ATTRIBUTE_ROOT(self.store.graphdb)

            def get_or_create(self, name, *args, **kwargs):
                try:
                    return self[name]
                except KeyError:
                    try:
                        return self(name, *args, **kwargs)
                    except KeyError: # crated concurrently
                        return self[name]

            @property
            def __types(self):
                try:
                    types = self.store.__types
                except:
                    types = None
                if types is None:
                    self.store.__types = types = {}
                return types

            @property
            def __all(self):
                graphdb = self.store.graphdb
                for rel in self.__node.ATTRIBUTE_TYPE:
                    type = model.AttributeType(graphdb, rel.end)
                    self.__types[type.name] = type
                    yield type

        def __call__(self, *args, **kwargs):
            return model.Attribute(*args, **kwargs)

    @property
    def root_node(categories):
        self = categories.store
        return model.category_node(self.__root)
    categories.root = root_node
    attribute.root = root_node
    del root_node
