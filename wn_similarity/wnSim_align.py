from collections import defaultdict
from nltk.corpus import wordnet as wn, wordnet_ic
from random import sample
import numpy as np
import os
from wn_similarity import disamb_group as ngroup

SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIRECTORY_ROOT = os.getcwd()
brown_ic = wordnet_ic.ic('ic-brown.dat')

def get_rel_wn_syn(syn, hyperDepth=1, hypoDepth=1, sisterDepth=1):
    """
    Purpose: Get all related synsets
    Input: WordNet synset (string)
    Output: a list of related synsets (including sisterms(往上抓一層的hypernym再往下抓一層hyponym), part holonyms +
            member holonyms + member holonyms) (Data type: list)
    """
    #syn = wn.synset(syn)
    hypo = lambda s: s.hyponyms()
    hyper = lambda s: s.hypernyms()
    
    # hypernyms
    hypernyms = list(syn.closure(hyper, depth=hyperDepth))# get hypernyms (with the depth of 1 level)
    
    # hyponyms
    hyponyms = list(syn.closure(hypo, depth=hypoDepth))# get hypernyms (with the depth of 1 level)
    
    # sister synsets (hyponyms of hypernyms)
    sisters = []
    for h in hypernyms:
        for s in list(h.closure(hypo, depth=sisterDepth)):
            sisters.append(s)
    
    part_holonyms = [ z.synset() for y in list(syn.closure(lambda syn: syn.part_holonyms())) for z in y.lemmas() ]
    member_holonyms = [ z.synset() for y in list(syn.closure(lambda syn: syn.member_holonyms(), depth=1)) for z in y.lemmas() ]
    part_meronyms = [ z.synset() for y in list(syn.closure(lambda syn: syn.part_meronyms(), depth=1)) for z in y.lemmas() ]
    
    related_terms = hypernyms + hyponyms + sisters + part_holonyms + member_holonyms + part_meronyms
    
    return related_terms



def trans_wikipages(wikipages, UPBOUND_disambGroup=50):
    
    wikipageGroup = wikipages if len(wikipages) < UPBOUND_disambGroup else sample(wikipages, UPBOUND_disambGroup)
    tmpSenses_ = [ wn.synsets(wikipageGroup[i], pos=wn.NOUN) for i in range(len(wikipageGroup)) ]
    wikiSyns = ngroup.disambGroup(wikipageGroup, tmpSenses_, pos=wn.NOUN)

    # 如果 disambiguate 失敗 (wikiSyns為空)，而還有尚未 disambigate 的 wikipages 可用 (len(wikipages)!=0)，就繼續 sample 下一組 wikipage
    while len(wikiSyns) == 0 and len(wikipages) != 0:
        # 把 disambiguate 失敗的 wikipage 從 wikipages 刪掉，再sample 其他 wikipage 出來
        wikipages = list(set(wikipages) - set(wikipageGroup))
        wikipageGroup = wikipages if len(wikipages) < UPBOUND_disambGroup else sample(wikipages, UPBOUND_disambGroup)
        tmpSenses_ =  [ wn.synsets(wikipageGroup[i], pos=wn.NOUN) for i in range(len(wikipageGroup)) ]
        wikiSyns = ngroup.disambGroup(wikipageGroup, tmpSenses_, pos=wn.NOUN)
    
    return wikiSyns



def wiki_wn_group_single_link(wiki_pgs, wn_terms):
    """
    Purpose: Calculate and determine the max similarity between WordNet related words and Wiki sister pages
    Input: [wiki_pgs]: wiki sister pages (list of synsets); [wn_terms]: WordNet related terms (list of synsets)
    Output: max similarity (float)
    """
    max_sim = -1
    max_wiki_syn = 'None'
    max_wn_syn = 'None'
    
    def sigmoid(x):
        return 1/(1 + np.exp(-x))
    
    for wn_term in wn_terms:
        for wiki_pg in wiki_pgs:
            pair_sim = wn_term.res_similarity(wiki_pg, brown_ic)
            if pair_sim > max_sim:
                max_sim = pair_sim
                max_wiki_syn = wiki_pg
                max_wn_syn = wn_term
    
    try:
        max_wiki_syn = max_wiki_syn.name()
        max_wn_syn = max_wn_syn.name()
        max_sim = str(max_sim)
    except AttributeError:
        max_sim = str(max_sim)
        pass
                
    return max_wiki_syn, max_wn_syn, max_sim
    
