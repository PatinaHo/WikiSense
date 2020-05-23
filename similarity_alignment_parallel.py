from collections import defaultdict
from nltk.corpus import wordnet as wn, wordnet_ic
from random import sample
from tqdm import tqdm
import multiprocessing as mp
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



def limit_wiki_sis_pg(sis_pages):
    """
    Purpose: Limit the amount of wiki sister pages (for better performance of [disambWikiGroup])
    Input: [sis_pages]: Wiki sister pages (list of string)
    Output: [final_sis_pages]: reduced (if applicable) Wiki sister pages (list of string)
    """
    
    if len(sis_pages) < 50:
        lim_sis_pages = sis_pages
    else:
        lim_sis_pages = sample(sis_pages, 50)
    
    return lim_sis_pages


def get_new_lim_wiki_sis(all_wiki_sis, remove_sis):
    """
    Purpose: 把找不到wiki_synset的wiki_page從[all_wiki_sis]刪掉，再抽50個wiki_page出來
    Input: [all_wiki_sis]: all wiki pages (a list of string); 
           [remove_sis]: 找不到synset的wiki_page (a list of string)
    Output: [all_wiki_sis]: 刪掉找不到synset的wiki page之後的所有wiki sister page
            [lim_wiki_sis]: 重新抽的50個wiki page
    """
    
    all_wiki_sis = list(set(all_wiki_sis) - set(remove_sis))
    if len(all_wiki_sis) < 50:
        lim_wiki_sis = all_wiki_sis
    else:
        lim_wiki_sis = sample(all_wiki_sis, 50)
    
    return all_wiki_sis, lim_wiki_sis


def wiki_wn_group_single_link(wiki_pgs, wn_terms):
    """
    Purpose: Calculate and determine the max similarity between WordNet related words and Wiki sister pages
    Input: [wiki_pgs]: wiki sister pages (list of synsets); [wn_terms]: WordNet related terms (list of synsets)
    Output: max similarity (float)
    """
    max_sim = -1
    max_wiki_syn = 'None'
    max_wn_syn = 'None'
    
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
    

def sim_match(w):
    # wordResult = defaultdict(lambda: defaultdict(list))
    wordResult = {}
    print(w)
    for synset in wn.synsets(w, pos=wn.NOUN):
        wordResult[synset.name()] = {}
        wn_rel_syn = wn_relatedSyn[synset] # Get related synsets of [synset]
        for cand in wiki_cand[w]:
            # Get Wikipedia sister pages (sister pages of [cand])
            sister_pgs = [sis for sis in wiki_relatedPage[cand] if wn.synsets(sis, pos=wn.NOUN)]
            lim_sister_pgs = limit_wiki_sis_pg(sister_pgs)

            senses =  [ wn.synsets(lim_sister_pgs[i], pos='n') for i in range(len(lim_sister_pgs)) ]
            wiki_sister_pgs = ngroup.disambGroup(lim_sister_pgs, senses, pos='n')

            # 如果[wiki_sister_pgs]是空的，然後len(sister_pgs) != 0，就繼續找新的Wiki page
            while len(wiki_sister_pgs) == 0 and len(sister_pgs) != 0:
                sister_pgs, lim_sister_pgs = get_new_lim_wiki_sis(sister_pgs, wiki_sister_pgs)   
                senses =  [ wn.synsets(lim_sister_pgs[i], pos='n') for i in range(len(lim_sister_pgs)) ]
                wiki_sister_pgs = ngroup.disambGroup(lim_sister_pgs, senses, pos='n')

            wiki_sister_pgs_name = [item[0] for item in wiki_sister_pgs]  ######################TO BE DEL        
            wiki_sister_pgs = [item[1] for item in wiki_sister_pgs]       # synsets

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
    allLemma = list(wn.all_lemma_names(pos='n'))
    polysemousLemma = [lemma for lemma in allLemma if len(wn.synsets(lemma, pos=wn.NOUN))>1]
    wikiCandKeys = set(wiki_cand.keys())
    targetAnchors = [lemma for lemma in polysemousLemma if lemma in wikiCandKeys]

    with mp.Pool(mp.cpu_count()-2) as p:
        wordResultList = list(tqdm(p.imap(sim_match, targetAnchors), total=len(targetAnchors)))

    result = {}
    for num, w in enumerate(targetAnchors):
        result[w] = wordResultList[num]

    with open('sim_result.json', 'w') as fp:
        json.dump(result, fp)