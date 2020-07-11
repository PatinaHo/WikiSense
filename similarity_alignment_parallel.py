from collections import defaultdict
from nltk.corpus import wordnet as wn, wordnet_ic
from tqdm import tqdm
import multiprocessing as mp
import numpy as np
import json
import time
import os
import csv
import argparse
from wn_similarity import wnSim_align
from wn_similarity import disamb_group as ngroup

SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIRECTORY_ROOT = os.getcwd()


def sim_match(w):
    # wordResult = defaultdict(lambda: defaultdict(list))
    wordResult = {}
    print(w)
    candWikipages = list(cand for cand in wiki_cand[w] if wiki_cand[w][cand]>=3)
    for synset in wn.synsets(w, pos=wn.NOUN):
        wordResult[synset.name()] = {}
        wnRelatedSyn = wn_relatedSyn[synset] # Get related synsets of [synset]
        for cand in candWikipages:
            # Get Wikipedia sister pages (sister pages of [cand])
            relatedPages = wiki_relatedPage[cand]
            wikiSyns = wnSim_align.trans_wikipages(relatedPages)
            wikiSyns = [item[1] for item in wikiSyns]       # synsets

            max_wiki_syn, max_wn_syn, max_sim = wnSim_align.wiki_wn_group_single_link(wikiSyns, wnRelatedSyn)
            
            wordResult[synset.name()][cand] = [max_sim]
    
    return wordResult



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__
    )

    parser.add_argument(
        '-n',
        '--wnRelatedSynFile',
        help=(
            'give the file name of input WordNet related synsets, should be csv format'
        )
    )

    parser.add_argument(
        '-s',
        '--similarityScore',
        help=(
            'give the file name of middle output file, similarity score, should be json format'
        )
    )

    parser.add_argument(
        '-k',
        '--wkRelatedPageFile',
        default='wiki_sis_pg_in_wn.csv',
        help=(
            'give the file name of middle output file, similarity score, should be json format'
        )
    )

    args = parser.parse_args()

    ##################   Reading required data   ##################

    print("Reading required data...")
    # wiki_cand: {'bass': {'Bass guitar': 15039, 'Double bass': 6540, 'Bass (voice type)': 2791, ...}}
    with open(os.path.join(DIRECTORY_ROOT, 'data/en.link.redirect.json')) as json_file:  
        wiki_cand = json.load(json_file)

    # wn_relatedSyn: {Synset('party.n.01'): [Synset('organization.n.01'), Synset('adhocracy.n.01'), Synset('affiliate.n.02'), ... ]}
    wn_relatedSyn = {}
    with open(os.path.join(SERVER_ROOT, f"patina/WikiSense/jupyter_nb/experimentSetting/{args.wnRelatedSynFile}"), newline='') as csvfile:
        rows = csv.reader(csvfile)
        for row in rows:
            wn_relatedSyn[wn.synset(row[0])] = [wn.synset(item) for item in row[1:]]

    # wiki_relatedPage: {}
    wiki_relatedPage = {}
    with open(os.path.join(SERVER_ROOT, f"patina/WikiSense/jupyter_nb/experimentSetting/{args.wkRelatedPageFile}"), newline='') as csvfile:
        rows = csv.reader(csvfile)
        for row in rows:
            if len(row)>1:
                wiki_relatedPage[row[0]] = [item for item in row[1:]]
            else:
                wiki_relatedPage[row[0]] = []

    ##############################################################

    allLemma = list(wn.all_lemma_names(pos=wn.NOUN))
    polysemousLemma = [lemma for lemma in allLemma if len(wn.synsets(lemma, pos=wn.NOUN))>1]
    wikiCandKeys = set(wiki_cand.keys())
    # targetAnchors = [lemma for lemma in polysemousLemma if lemma in wikiCandKeys]

    EVAL_WORDS = ['star', 'mole', 'galley', 'cone', 'bass', 'bow', 'taste', 'interest', 'issue', 'duty', 'sentence', 'slug', 'argument', 'arm', 'atmosphere', 'bank', 'bar']

    print("Start calculating similarity score...")
    with mp.Pool(mp.cpu_count()-2) as p:
        wordResultList = list(tqdm(p.imap(sim_match, EVAL_WORDS), total=len(EVAL_WORDS)))

    result = {}
    for num, w in enumerate(EVAL_WORDS):
        result[w] = wordResultList[num]

    print("Writing similarity score into file...")
    with open(os.path.join(SERVER_ROOT, f'patina/WikiSense/jupyter_nb/experimentSetting/{args.similarityScore}'), 'w') as fp:
        json.dump(result, fp)