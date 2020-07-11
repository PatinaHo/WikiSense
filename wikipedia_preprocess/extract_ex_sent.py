import os
import json
import re
import time
import glob
import fileinput
from bson import json_util
from collections import defaultdict
from nltk.corpus import wordnet as wn
from nltk.corpus import words
import tqdm


ROOT_PATH = "/home/nlplab/patina/Dataset/wiki_parse"
all_wn_words = set(wn.all_lemma_names())


def get_anchorAlias_pageAlias(redirect_file_PATH):
    """ 
    Get anchor alias & hyperlinkedpage alias. 
    This way when alias appear in Wikipedia contexts, we know which exact hyperlink it is
    Input:
        redirect_file_PATH: "en.link.redirect" file. 
            - File format: 
            - Example: Party (law)	___	113	Counter({'[[party (law)|party]]': 35, '[[Party (law)|party]]': 31, '[[Party (law)|parties]]': 26, '[[party (law)|parties]]': 21})
    Return:
        revAnchorAlias(dict): revAnchorAlias['parties'] = 'party'
        revPageAlias(dict): revPageAlias['party (law)'] = 'Party (law)'
    """

    tStart = time.time()
    print("Start getting alias ...")
    all_wn_words = set(wn.all_lemma_names())
    anchorAlias = defaultdict(lambda: set())
    pageAlias   = defaultdict(lambda: set())
    with open(redirect_file_PATH) as file:
        for line in file:
            lemma, linkpage, ch_title, total_count, counter = line.strip().split('\t')
            if(lemma[0].islower() and int(total_count) > 1 and lemma in all_wn_words):
                for s in re.finditer(r'\[\[[^\[\]]+|[^\[\]]+\]\]', counter):
                    pageAlias[linkpage].add(s.group().split('|')[0][2:])
                    if len(s.group().split('|')) > 1:
                        anchorAlias[lemma].add(s.group().split('|')[1])
                    else:
                        anchorAlias[lemma].add(s.group()[2:])
    
    revAnchorAlias = {}
    revPageAlias   = {}
    for anchor in anchorAlias:
        for alias in anchorAlias[anchor]:
            revAnchorAlias[alias] = anchor
    for page in pageAlias:
        for alias in pageAlias[page]:
            revPageAlias[alias] = page
    
    tEnd = time.time()
    print("Finished getting word alias. Cost %f sec" % (tEnd - tStart))
                    
    return revAnchorAlias, revPageAlias


def extract_sent(anchorAlias, pageAlias, jsonlines):
    """
    Check all redirect qlinks in wiki texts. 
    If it's redirected to any page listed in words_alias, extract the sentence the redirect link located in.

    Return:
        ex_sent(dict): {word0: {sense0: [(sent0, wiki_id, start_idx, end_idx), (sent1, wiki_id, start_idx, end_idx), ...], 
                                sense1: [(sent0, wiki_id, start_idx, end_idx), (sent1, wiki_id, start_idx, end_idx), ...], ... },
                        word1: ...
                        }
    """
    tStart = time.time()
    print("Start extracting sentence...")
    ex_sent = {}
    numOfSent = 0

    # A line is a page
    for line in tqdm.tqdm(jsonlines, position=0, leave=True):
        json_data  = json.loads(line)
        wiki_id    = json_data["id"]
        lines_list = json_data["text"]
        for line_info in lines_list:
            line = line_info["line"]
            validHplk = False
            for start_idx, end_idx, linkpage in line_info["links"]:
                anchor = line[start_idx:end_idx]
                try:
                    normalized_anchor = anchorAlias[anchor]
                    normalized_page   = pageAlias[linkpage]
                    if (normalized_anchor not in ex_sent.keys()):
                        ex_sent[normalized_anchor] = {}
                    if (normalized_page not in ex_sent[normalized_anchor]):
                        ex_sent[normalized_anchor][normalized_page] = []
                    ex_sent[normalized_anchor][normalized_page].append((line, wiki_id, start_idx, end_idx))
                    validHplk = True
                except:
                    pass
            if validHplk == True: numOfSent += 1

    tEnd = time.time()
    print("Finished extracting sentence. Cost %f sec" % (tEnd - tStart))
                            
    return ex_sent, numOfSent


def read_wikifiles(root_dir_PATH):
    tStart = time.time()
    print("Loading wiki data...")

    paths = os.path.join(root_dir_PATH, '*/wiki_*')
    wiki_files = glob.glob(paths)
    lines = [line for line in fileinput.input(wiki_files)]
    
    tEnd = time.time()
    print("Finished loading. Cost %f sec" % (tEnd - tStart))
    print()
    return lines


def main():
    wiki_lines             = read_wikifiles(ROOT_PATH)
    anchorAlias, pageAlias = get_anchorAlias_pageAlias("/home/nlplab/patina/WikiSense/data/en.link.redirect.txt")
    ex_sents, numOfSent = extract_sent(words_alias, wiki_lines)
    print("例句總數：", numOfSent)

    print("Writing full_set_idx.json...")
    result = {}
    with open('/home/nlplab/patina/WikiSense/data/WeCNLP/full_set.json', 'wb') as fp:
        for word in tqdm.tqdm(lemmas):
            if(word in ex_sents.keys()):
                result[word] = ex_sents[word]
        fp.write(json.dumps(result, ensure_ascii=False).encode('utf8'))
    print("Finished writing full_set_idx.json")
    

if __name__ == "__main__":
    main()