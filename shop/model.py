# -*- coding: utf-8 -*-
"""
Defines the domain model for a shop with categories and products.

Each product in a category is of a type defined by the category. Therefore
the Category type in the domain model is the metaclass of the Product type.
Each category is an instance of the Category class. Each category object is
also the class of the products that are contained in that category.
The Product class is the base class for all product classes (the Category
objects). While metaprogramming can easily get tricky, this is a perfect
example of where it is actually useful, this allows us to store the metadata
of the domain in the database with the actual data. The metadata here being
the definitions of the categories, with the attribute constraints the
categories carry, and the data being the actual products in the categories.
"""

from __future__ import with_statement

import threading
import neo4j

__all__ = 'Product', 'Category', 'SubCategories', 'Attribute', #'AttributeType',


class Product(object): # instance of Category

    def __init__(self, graphdb, node):
        self.__node = node
        #self.__graphdb = graphdb
    #graphdb = property(lambda self: self.__graphdb)

    def __new__(Product, graphdb, node):
        """Create a Product representation from a Node"""
        # 1. Lookup the category 
        # 2. Create the product as an instance of the category
        return Category(graphdb, node.PRODUCT.single.start)(graphdb, node)

    def __str__(self):
        return " ".join(attr(self) for attr in self.all_attributes()) or \
            ("an unspecified %s" % (self.__class__,))
    @classmethod
    def all_attributes(cls):
        return cls.get_all_attributes()

    def __repr__(self):
        return '<%s %s>' % (self.__class__, self)

    global product_node # define here to get the name mangling right
    def product_node(self):
        return self.__node


class Category(type): # type of Product
    __categories = {}
    __create_lock = threading.RLock() # reentrant lock

    graphdb = property(lambda self: self.__graphdb)

    def __init__(self, *args): pass # do nothing

    def __new__(Category, graphdb, node):
        """Lookup or create a Category representation for a Node."""
        # If the Category instance already exists
        self = Category.__categories.get(node.id)
        if self is None: # Otherwise create it
            with Category.__create_lock: # Unless it was created concurrently
                self = Category.__categories.get(node.id)
                if self is not None: return self

                with graphdb.transaction:

                    # Get the name of the category
                    name = node['Name']
                    if isinstance(name, unicode):
                        name = name.encode('ascii')

                    # Get the attributes for products in the category
                    attributes = dict(__new__=object.__new__)
                    for attr in node.ATTRIBUTE:
                        # Get the Attribute type (instance of AttributeType)
                        Attribute = AttributeType( graphdb, attr.end )
                        # Instantiate the attribute
                        attribute = Attribute( graphdb, attr['Name'],
                                               attr.get('DefaultValue'),
                                               attr.get('Required') )
                        # Add the attribute to the category instance dict
                        attributes[ attr['Name'] ] = attribute

                    # Get the parent category (the superclass of this category)
                    parent = node.SUBCATEGORY.incoming.single
                    if parent is None:
                        parent = Product # The base Category type
                    else:
                        parent = Category(graphdb, parent.start)
                    
                    # Create a new type instance representing the Category
                    self = type.__new__(Category, name, (parent,), attributes)
                    self.__graphdb = graphdb
                    self.__node = node
                    Category.__categories[node.id] = self

        return self

    global category_node # define here to get the name mangling right
    def category_node(self):
        return self.__node

    def get_all_attributes(self):
        for name in dir(self):
            value = getattr(self, name)
            if isinstance(value, Attribute):
                yield value

    def __str__(self):
        return self.name

    @neo4j.transactional(graphdb)
    @property
    def name(self):
        return self.__node['Name']

    @property
    def parent(self):
        try:
            return Category(self.graphdb,
                            self.__node.SUBCATEGORY.incoming.single.start)
        except:
            return self

    def __getitem__(self, name):
        for rel in self.__node.SUBCATEGORY.outgoing:
            node = rel.end
            if node['Name'] == name:
                break
        else:
            raise KeyError(name)
        return Category(self.graphdb, node)

    def new_subcategory(self, name, **attributes):
        """Create a new sub category"""
        with self.__create_lock:
            with self.graphdb.transaction:
                node = self.graphdb.node(Name=name)
                self.__node.SUBCATEGORY(node)
                for key, factory in attributes.items():
                    factory(node, key)
                return Category(self.graphdb, node)

    def new_product(self, **values):
        """Create a new product in this category"""
        with self.graphdb.transaction:
            node = self.graphdb.node()
            self.__node.PRODUCT(node)
            product = self(self.graphdb, node)
            for key, value in values.items():
                getattr(self, key).__set__(product, value)
            for attr in self.get_all_attributes():
                attr.verify(product)
            return product

    def __iter__(self):
        """Iterating over a category yields all its products.
        This includes products in subcategories of this category."""
        for prod in SubCategoryProducts(self.__node):
            yield Product(self.graphdb, prod)

    @property
    def categories(self):
        for rel in self.__node.SUBCATEGORY.outgoing:
            yield Category(self.graphdb, rel.end)


class SubCategoryProducts(neo4j.Traversal):
    "Traverser that yields all products in a category and its sub categories."
    types = [neo4j.Outgoing.SUBCATEGORY, neo4j.Outgoing.PRODUCT]
    def isReturnable(self, pos):
        if pos.is_start: return False
        return pos.last_relationship.type == 'PRODUCT'


class SubCategories(neo4j.Traversal):
    "Traverser that yields all subcategories of a category."
    types = [neo4j.Outgoing.SUBCATEGORY]
    


class AttributeType(type): # type of Attribute
    __attribute_types = {}
    __create_lock = threading.RLock() # reentrant lock

    def __new__(AttributeType, graphdb, node):
        """Lookup or create a AttributeType representation for a Node."""
        # If the AttributeType instance already exists
        self = AttributeType.__attribute_types.get(node.id)
        if self is None: # Otherwise create it
            with AttributeType.__create_lock: # Unless created concurrently
                self = AttributeType.__attribute_types.get(node.id)
                if self is not None: return self

                with graphdb.transaction:

                    body = dict(__new__=object.__new__)
                    self = type.__new__(AttributeType, node['Name'],
                                        (Attribute,), body)

                    self.__node = node

        return self

    @classmethod
    def create(AttributeType, graphdb, root, name, **attributes):
        unit = attributes.pop('Unit', "")
        if attributes: raise TypeError(
            "Unsupported keyword arguments: "+", ".join(
                "'%s'" % (key,) for key in attributes))

        with graphdb.transaction:
            node = graphdb.node(Name=name, Unit=unit)
            root.ATTRIBUTE_TYPE(node)
            
            for rel in root.ATTRIBUTE_TYPE:
                if rel.end == node: continue
                if rel.end['Name'] == name:
                    raise KeyError("AttributeType %r already exists" % (name,))

            return AttributeType(graphdb, node)

    @property
    def unit(self):
        return self.__node.get('Unit', '')

    @property
    def name(self):
        return self.__node['Name']

    global type_node
    def type_node(self):
        return self.__node

    def to_primitive_neo_value(self, value):
        return value

    def from_primitive_neo_value(self, value):
        return value

    def verify_constraints(self, value):
        pass


class Attribute(object): # instance of AttributeType

    def __new__(self, type, **kwargs):
        required = kwargs.pop('required', 'default' not in kwargs)
        default = kwargs.pop('default', None)
        if kwargs: raise TypeError("Unsupported keyword arguments: "+", ".join(
                "'%s'" % (key,) for key in kwargs))
        def AttributeFactory(node, name):
            attr=node.ATTRIBUTE( type_node(type), Name=name, Required=required)
            if default is not None:
                attr['DefaultValue'] = type.to_primitive_neo_value(default)
        return AttributeFactory

    def __init__(self, graphdb, key, default, required):
        self.key = key
        self.default = default
        self.required = required

    def verify(self, obj):
        if self.required:
            self.verify_value(product_node(obj)[self.key])

    def __str__(self):
        return '<Attribute type=%s Name=%r DefaultValue=%r Required=%s>' % (
            self.__class__.__name__, self.key, self.default, self.required)

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        else:
            return self.from_neo(product_node(obj).get(self.key, self.default))

    def __set__(self, obj, value):
        product_node(obj)[self.key] = self.to_neo(value)

    def __delete__(self, obj):
        del product_node(obj)[self.key]

    def __call__(self, obj):
        return "%s: %s%s" % (self.key, self.__get__(obj), self.get_unit())

    @classmethod
    def verify_value(Attribute, value):
        value = Attribute.from_primitive_neo_value(value)
        Attribute.verify_constraints(value)

    @classmethod
    def to_neo(Attribute, value): # Delegate to the AttributeType
        return Attribute.to_primitive_neo_value(value)

    @classmethod
    def from_neo(Attribute, value): # Delegate to the AttributeType
        return Attribute.from_primitive_neo_value(value)

    @classmethod
    def get_unit(Attribute):
        return Attribute.unit

