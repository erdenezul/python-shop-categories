# -*- coding: utf-8 -*-

def create_empty_category(store):
    cat = store.categories('Empty')
    assert cat is not None
    assert cat == store.categories['Empty']

def create_category_with_attributes(store):
    cat = store.categories('Stuff', Name=store.attribute(
            store.attribute.type.get_or_create('name')))
    assert cat is not None
    assert 'Name' in dir(cat)
    print cat.Name
