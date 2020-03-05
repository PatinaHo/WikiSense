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


def get_title2GT(FILE_PATH):
    title2GT = {}
    
    with open(FILE_PATH, 'r') as f:
        for line in f:
            title, WNsynset, refinedGT, origGT, wikiDef, WNDef = line.strip().split('\t')
            title2GT[title] = refinedGT
    return title2GT


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


def gen_features(title2GT, parentCatsID, id2cat, cat2id):
    """
    Generate features of Wikipages. 'features' represents PE & categories.
    Arg: 
        - title2GT(dict): {page_title: GTsynset_name}
          ex: {'AX': 'tool.n.01', 'Aardvark': 'mammal.n.01'}
    Return:
        - titles(list):
        - featuresText(list): [({'PE': ..., 'categories': [...]}, GT)]
          ex: [({'PE': None}, 'material.n.01'),
               ({'PE': 'fabric',
                 'categories': ['Textiles', 'Weaving', 'Woven fabrics']}, 'fabric.n.01'),
                ...]
        - featuresVec(list): 
        - labelVec(list): 
    """
    
    titles = [title for title in title2GT]
    featuresText = []

    for title in title2GT:
        parentsName = get_parentCategories(title, pageCat, parentCatsID, id2cat, cat2id)
        PE   = re.search(r'\(.+\)', title).group()[1:-1] if re.search(r'\(.+\)', title) != None else None
        feature = {'PE': PE, 'categories': parentsName}
        featuresText.append((feature, title2GT[title]))
    
    peSet  = {pageInfo[0]['PE'] for pageInfo in featuresText if pageInfo[0]['PE']!= None}
    catSet = {cat for pageInfo in featuresText for cat in pageInfo[0]['categories']}
    peIdx  = {pe: i for i, pe in enumerate(list(peSet))}
    catIdx = {cat: i+len(peIdx) for i, cat in enumerate(list(catSet))}
    
    featuresVec = np.zeros((len(titles), len(peSet)+len(catSet)))
    for i in range(len(titles)):
        if featuresText[i][0]['PE']!=None:
            pe = featuresText[i][0]['PE']
            featuresVec[i][peIdx[pe]] = 1
        if featuresText[i][0]['categories']!=[]:
            for cat in featuresText[i][0]['categories']:
                featuresVec[i][catIdx[cat]] = 1
    
    gtSet = {gt for title, gt in title2GT.items()}
    gtIdx = {gt: i for i, gt in enumerate(list(gtSet))}
    
    labelVec = np.array([gtIdx[pageInfo[1]] for pageInfo in featuresText])
        
    return titles, featuresText, featuresVec, labelVec


def main():
    title2GT = get_title2GT('/home/nlplab/patina/WikiSense/data/hypernym_definition_gt.txt')
    pageCat, parentCatsID, id2cat, cat2id = read_categories()
    titles, featuresText, featuresVec, labelVec = gen_features(title2GT, parentCatsID, id2cat, cat2id)
    

if __name__ == "__main__":
    main()