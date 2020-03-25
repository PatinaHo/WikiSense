#!/usr/bin/env python 
# -*- coding: utf8 -*-

import sys
from nltk.corpus import wordnet as wn

"""
catMembers = {catSynset1: (catNumber, descendents), catSynset2: (catNumber, descendents), ...}
cat        = {synset: catNumber}
"""
catMembers = {}
cat = {}

LOWER = 50 # 25
UPPER = 100 #100
catNumber = 0
fileout = open('wn.500.categories.txt', 'w')

def unregistered_descendents(syn):
    """
    Return syn itself and its recurring unregistered descendents, if syn is unregistered (isn't initially in cat).
    Return:
        res: [descendent_synset1, descendent_synset2, ...]
    """
    if syn in cat:
        return []

    res = [syn]
    for hypo in syn.hyponyms():
        res += unregistered_descendents(hypo)
    return res

def mark(syn, descendents, catNumber):
    """
    Changes catMembers and cat.
    Returns nothing.
    """
    catMembers[syn] = (catNumber, descendents)
    for d in descendents:
        cat[d] = catNumber
    return

def add_categories(n):
    """
    Classify synsets with descendents number in range(LOWER, UPPER) as a category.
    Changes catMembers and cat.
    Returns nothing.
    """
    global catNumber
    if n in catMembers: return

    descendents = unregistered_descendents(n)
    total = len(descendents)
    if total in range(LOWER, UPPER):
        catNumber += 1
        mark(n, descendents, catNumber)
    elif total > UPPER:
        for hypo in n.hyponyms():
            descendents = unregistered_descendents(hypo)
            total = len(descendents)
            if total in range(LOWER, UPPER):
                catNumber += 1
                mark(hypo, descendents, catNumber)
            elif total > UPPER:
                add_categories(hypo)

        descendents = unregistered_descendents(n)
        total = len(descendents)
        if total > LOWER:
            descendents = unregistered_descendents(n)
            catNumber += 1
            mark(n, descendents, catNumber)


def 

nouns = [ s for s in wn.all_synsets() if s.pos == 'n']
for n in nouns:
  add_categories(n)

"""
cats = [(catNumber, catsynset, [descendentSyn1, descendentSyn2, ...])]
"""
cats = [ (catMembers[syn][0], syn, catMembers[syn][1]) for syn in catMembers.keys()]
cats.sort(key = lambda x: x[0])

for no, syn, members in cats:
    print(fileout, no, syn.name)

    y = [ ', '.join([ x for x in m.lemma_names if '_' not in x and '-' not in x] ) for m in members ]
    print(fileout, '; '.join( [ z for z in y if z != '' ] ))
    print(fileout)
fileout.close()
