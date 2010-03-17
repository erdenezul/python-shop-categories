# -*- coding: utf-8 -*-

from __future__ import with_statement

if __name__ == '__main__':
    import os, sys
    with open(os.path.join(os.path.dirname(__file__),'__main__.py')) as module:
        exec(module)
    sys.exit()

import neo4j

from shop import model

class Store(object):

    def __init__(self, storedir):
        self.__graphdb = graphdb = neo4j.GraphDatabase(storedir)
        with graphdb.transaction:
            root = self.graphdb.reference_node
            root['name'] = "Product"
            self.__root = model.Category(graphdb, root)

    graphdb = property(lambda self: self.__graphdb)
    root = property(lambda self: self.__root)
