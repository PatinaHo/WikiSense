#!/usr/bin/env python 
# -*- coding: utf8 -*-

import sys
from nltk.corpus import wordnet as wn

catMembers = {}
cat = {}

LOWER = 100 # 25
UPPER = 1000 #100
catNumber = 0
#fileout = file('wn.500.categories.txt', 'w')

def unregistered_descendents(syn):
  if syn in cat:
    return []
  
  res = [syn]
  for hypo in syn.hyponyms():
    res += unregistered_descendents(hypo)
  return res

def mark(syn, descendents, catNumber):
  catMembers[syn] = (catNumber, descendents)
  for d in descendents:
    cat[d] = catNumber
  return

def addCategories(n):
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
        addCategories(hypo)

    descendents = unregistered_descendents(n)
    total = len(descendents)
    if total > LOWER:
      descendents = unregistered_descendents(n)
      catNumber += 1
      mark(n, descendents, catNumber)

#nouns = [ wn.synsets('plant', 'n')[1] ]
nouns = [ s for s in wn.all_synsets() if s.pos() == 'n']
print('classifying', len(nouns), 'noun synsets')

for n in nouns:
  addCategories(n)
  
cats = [ (catMembers[syn][0], syn, catMembers[syn][1]) for syn in catMembers.keys()]
cats.sort(key = lambda x: x[0])

for no, syn, members in cats:
  y = [ ', '.join([ x for x in m.lemma_names() if '_' not in x and '-' not in x] ) for m in members ]
  print(no, syn.name,'; '.join( [ z for z in y if z != '' ] ))
  #print >> fileout
#fileout.close()
