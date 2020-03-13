import pandas as pd
import numpy as np
import nltk
import operator
import re
import json

from collections import Counter, defaultdict
from nltk.corpus import wordnet as wn
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer


def read_categories():
    """ Reader.
    Returns:
        - pageCat:
          ex. {'Party': ['Category:Parties', 'Category:Party stores'], 'Party (law)': ['Category:Legal terminology']}
        - parentCatsID: 
          ex. {'40': ['10185', '77722', '98458', '419280'], '41': ['162055', '84916', '71925'], ...}
        - id2cat:
          ex. {'40': 'Programming languages', '41': 'Professional wrestling', ...}
        - cat2id:
          ex. {Programming languages': '40', 'Professional wrestling': '41', ...}
    """
    
    with open('/home/nlplab/patina/WikiSense/data/categ.json') as json_file:
        pageCat = json.load(json_file)
        print("pageCat read.")
    with open('/home/nlplab/patina/WikiSense/data/wiki.idCat.json') as json_file:
        id2cat = json.load(json_file)
        print("id2cat read.")
    with open('/home/nlplab/patina/WikiSense/data/wiki.catId.json') as json_file:
        cat2id = json.load(json_file)
        print("cat2id read.")
    
    parentCatsID = {}
    with open('/home/nlplab/patina/WikiSense/data/wiki.cat.parent.adjlist', 'r') as f:
        for line in f:
            line = line.strip().split(' ')
            parentCatsID[line[0]] = line[1:] if len(line) > 1 else []
        
    return pageCat, parentCatsID, id2cat, cat2id


def get_parentCategories(title, pageCat, parentCatsID, id2cat, cat2id):
    """ Pass WikiTitle and return its categories and the parent categories of its categories.
    Arg: title(string)
    Return:
        - parentsName(list); if the page only has 'Disambiguation pages' as category, then returns [].
          ex. ['Social events', 'Retailers by type of merchandise sold', 'Parties',
               'Organized events', 'Parties', 'Party stores']
    """

    pageCats   = pageCat[title] if title in pageCat else []
    pageCatsID = [cat2id[cat[9:]] for cat in pageCats if cat[9:] in cat2id]
    parents = {p for pageCatID in pageCatsID for p in parentCatsID[str(pageCatID)]}
    
    parentsName = [id2cat[pid] for pid in parents]
    for pageCat in pageCats:
        parentsName.append(pageCat[9:])
    
    return parentsName


def gen_features(FILE_PATH, parentCatsID, id2cat, cat2id):
    """
    Generate features of Wikipages. 'features' represents PE & categories.
    Arg: 
        - title2GT(dict): {page_title: (GTsynset_name, WNaligned_synset)}
          ex: {'Aardvark': ('mammal.n.01', 'aardvark.n.01'), 'Ceiba': ('genus.n.02', 'ceiba.n.01')}
    Return:
        - featuresText(list): [({'PE': ..., 'categories': [...]}, GT, alignWN)]
          ex: [({'PE': 'number', 'categories': ['Ring theory', 'Elementary number theory', 'Numbers',]}, 'number.n.02', 'forty.n.01'),
                ...]
    """
    featuresText = []
    
    with open(FILE_PATH, 'r') as f:
        for line in f:
            title, WNsynset, refinedGT, origGT, wikiDef, WNDef = line.strip().split('\t')
            parentsName = get_parentCategories(title, pageCat, parentCatsID, id2cat, cat2id)
            PE   = re.search(r'\(.+\)', title).group()[1:-1] if re.search(r'\(.+\)', title) != None else None
            page_info = {'title': title, 'PE': PE, 'categories': parentsName, 'GT': refinedGT, 'alignSynset': WNsynset}
            featuresText.append(page_info)
            
    return featuresText


def main():
    pageCat, parentCatsID, id2cat, cat2id = read_categories()
    featuresText = gen_features('/home/nlplab/patina/WikiSense/data/hypernym_definition_gt.txt', parentCatsID, id2cat, cat2id)
    

if __name__ == "__main__":
    main()