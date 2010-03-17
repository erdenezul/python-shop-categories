# -*- coding: utf-8 -*-

from __future__ import with_statement

import threading
import neo4j


class Product(object): # instance of Category

    def __init__(self, graphdb, node):
        self.__graphdb = graphdb
        self.__node = node

    graphdb = property(lambda self: self.__graphdb)

    def __new__(Product, graphdb, node):
        return Category(node.CATEGORY.single.end)(graphdb, node)

    global node # define here to get the name mangling right
    def node(self):
        return self.__node


class Category(type): # type of Product
    __categories = {}
    __create_lock = threading.RLock() # reentrant lock

    graphdb = property(lambda self: self.__graphdb)

    def __new__(Category, graphdb, node):
        self = Category.__categories.get(node.id)
        if self is None:
            with Category.__create_lock:
                self = Category.__categories.get(node.id)
                if self is not None: return self

                with graphdb.transaction:

                    name = node['name']
                    if isinstance(name, unicode):
                        name = name.encode('ascii')

                    attributes = dict(__new__=object.__new__)
                    for attr in node.ATTRIBUTE:
                        Attribute = AttributeType( attr.end )
                        attribute = Attribute( attr['name'],
                                               attr.get('default') )
                        attributes[ attr['name'] ] = attribute
                    
                    parent = node.SUBCATEGORY.single
                    if parent is None:
                        parent = Product
                    else:
                        parent = Category(graphdb, parent.start)
                    
                    self = type.__new__(Category, name, (parent,), attributes)
                    self.__graphdb = graphdb
                    self.__node = node
                    Category.__categories[node.id] = self

        return self

    def new_subcategory(self, name, **attributes):
        with self.__create_lock:
            with self.graphdb.transaction:
                node = self.graphdb.node(name=name)
                self.__node.SUBCATEGORY(node)
                return Category(self.graphdb, node)

    def new_product(self, name, **values):
        with self.graphdb.transaction:
            node = self.graphdb.node(name=name)
            node.CATEGORY(self.__node)
            product = self(graphdb, node)
            for key, value in values.items():
                setattr(product, key, value)
            return product

    def __iter__(self):
        """Iterating over a category yeilds all its products."""
        for prod in SubCategoryProducts(self.__node):
            yield Product(self.graphdb, prod)


class SubCategoryProducts(neo4j.Traversal):
    types = [neo4j.Outgoing.SUBCATEGORY, neo4j.Incoming.CATEGORY]
    def isReturnable(self, pos):
        return pos.last_relationship.type == 'CATEGORY'


class AttributeType(type): # type of Attribute

    def to_primitive_neo_value(self, value):
        return value

    def from_primitive_neo_value(self, value):
        return value


class Attribute(object): # instance of AttributeType

    def __init__(self, key, default):
        self.key = key
        self.default = default

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        else:
            return self.from_neo( node(obj).get(self.key, self.default) )

    def __set__(self, obj, value):
        node(obj)[self.key] = self.to_neo(value)

    def __delete__(self, obj):
        del node(obj)[self.key]

    @classmethod
    def to_neo(Attribute, value):
        return Attribute.to_primitive_neo_value(value)

    @classmethod
    def from_neo(Attribute, value):
        return Attribugte.from_primitive_neo_value(value)
