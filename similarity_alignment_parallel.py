from collections import defaultdict
from nltk.corpus import wordnet as wn, wordnet_ic
from random import sample
from tqdm import tqdm
import multiprocessing as mp
import numpy as np
import json
import time
import os
import csv
import n_groups.disamb_group as ngroup

SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIRECTORY_ROOT = os.getcwd()
brown_ic = wordnet_ic.ic('ic-brown.dat')

def get_rel_wn_syn(syn):
    """
    Purpose: (Step 1a) Get all related synsets
    Input:   WordNet synset (string)
    Output:  a list of related synsets (including sisterms(往上抓一層的hypernym再往下抓一層hyponym), part holonyms +
             member holonyms + member holonyms) (Data type: list)
    
    [NOTE]:member holonym 的 closure的深度要限制嗎？？（目前是有限制一層）
    """
    #syn = wn.synset(syn)
    hypo = lambda s: s.hyponyms()
    hyper = lambda s: s.hypernyms()
    
    # hypernyms
    hypernyms = list(syn.closure(hyper, depth = 1))# get hypernyms (with the depth of 1 level)
    
    # sister synsets (hyponyms of hypernyms)
    hypo_syn = []
    for h in hypernyms:
        for s in list(h.closure(hypo, depth = 1)):
            hypo_syn.append(s)
    
    part_holonyms = [ z.synset() for y in list(syn.closure(lambda syn: syn.part_holonyms())) for z in y.lemmas() ]
    member_holonyms = [ z.synset() for y in list(syn.closure(lambda syn: syn.member_holonyms(), depth = 1)) for z in y.lemmas() ]
    part_meronyms = [ z.synset() for y in list(syn.closure(lambda syn: syn.part_meronyms(), depth = 1)) for z in y.lemmas() ]
    
    related_terms = hypernyms + hypo_syn + part_holonyms + member_holonyms + part_meronyms
    
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
        max_sim = str(sigmoid(max_sim))
    except AttributeError:
        max_sim = str(sigmoid(max_sim))
        pass
                
    return max_wiki_syn, max_wn_syn, max_sim
    

def sim_match(w):
    # wordResult = defaultdict(lambda: defaultdict(list))
    wordResult = {}
    print(w)
    for synset in wn.synsets(w, pos=wn.NOUN):
        wordResult[synset.name()] = {}
        wn_rel_syn = wn_relatedSyn[synset] # Get related synsets of [synset]
        for cand in wiki_cand[w]:
            # Get Wikipedia sister pages (sister pages of [cand])
            relatedPages = wiki_relatedPage[cand]
            wikiSyns = trans_wikipages(relatedPages)
            wikiSyns = [item[1] for item in wiki_sister_pgs]       # synsets

            max_wiki_syn, max_wn_syn, max_sim = wiki_wn_group_single_link(wiki_sister_pgs, wn_rel_syn)
            
            wordResult[synset.name()][cand] = [max_sim]
    
    return wordResult

##################   Reading required data   ##################

# wiki_cand: {'bass': {'Bass guitar': 15039, 'Double bass': 6540, 'Bass (voice type)': 2791, ...}}
with open(os.path.join(DIRECTORY_ROOT, 'data/en.link.redirect.json')) as json_file:  
    wiki_cand = json.load(json_file)

# wn_relatedSyn: {Synset('party.n.01'): [Synset('organization.n.01'), Synset('adhocracy.n.01'), Synset('affiliate.n.02'), ... ]}
wn_relatedSyn = {}
with open(os.path.join(SERVER_ROOT, "nicalin/wiki-wn_alignment/data/wn_related_synset.csv"), newline='') as csvfile:
    rows = csv.reader(csvfile)
    for row in rows:
        wn_relatedSyn[wn.synset(row[0])] = [wn.synset(item) for item in row[1:]]

# wiki_relatedPage: {}
wiki_relatedPage = {}
with open(os.path.join(SERVER_ROOT, "nicalin/wiki-wn_alignment/data/wiki_sis_pg_in_wn.csv"), newline='') as csvfile:
    rows = csv.reader(csvfile)
    for row in rows:
        if len(row)>1:
            wiki_relatedPage[row[0]] = [item for item in row[1:]]
        else:
            wiki_relatedPage[row[0]] = []


if __name__ == "__main__":
    allLemma = list(wn.all_lemma_names(pos=wn.NOUN))
    polysemousLemma = [lemma for lemma in allLemma if len(wn.synsets(lemma, pos=wn.NOUN))>1]
    wikiCandKeys = set(wiki_cand.keys())
    targetAnchors = [lemma for lemma in polysemousLemma if lemma in wikiCandKeys]

    with mp.Pool(mp.cpu_count()-2) as p:
        wordResultList = list(tqdm(p.imap(sim_match, targetAnchors), total=len(targetAnchors)))

    result = {}
    for num, w in enumerate(targetAnchors):
        result[w] = wordResultList[num]

    with open('sigmoidSim_result.json', 'w') as fp:
        json.dump(result, fp)