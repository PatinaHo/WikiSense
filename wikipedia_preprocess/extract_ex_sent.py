import os
import json
import re
import spacy
import time
import glob
import fileinput
from bson import json_util
from math import sqrt, modf
from collections import defaultdict
from nltk.corpus import wordnet as wn
from nltk.corpus import words
import tqdm

import wikipediaapi
from nltk import word_tokenize, sent_tokenize


ROOT_PATH = "/home/nlplab/patina/Dataset/wiki_parse"
# OUTPUT_PATH = "/home/nlplab/patina/Dataset/wiki_parse"
# OUTPUT_PATH = "/home/nlplab/patina/WikiSense"

all_wn_words = set(wn.all_lemma_names())
words_30 = ["argument", "arm", "atmosphere", "bank", "bar", "chair", "channel", "circuit", "degree", "difference", 
            "disc", "dyke", "fatigue", "grip", "image", "material", "mouth", "nature", "paper", "party", 
            "performance", "plan", "post", "restraint", "sense", "shelter", "sort", "source", "spade", "stress"]


# def generate_path(root_path):
#     """ 
#     Get paths of all files under root_path.
#     Return: list of paths.
#     """

#     all_file_paths = []
#     for root, dirs, files in os.walk(root_path):
#         dirs = [d for d in dirs if not d[0] == '.']
#         for d in dirs:
#             dir_path = os.path.join(ROOT_PATH, d)
#             for root, dirs, files in os.walk(dir_path):
#                 files = [f for f in files if not f[0] == '.']
#                 for f in files:
#                     file_path = os.path.join(dir_path, f)
#                     all_file_paths.append(file_path)
    
#     return all_file_paths


# def split_path(full_path, root_path):
#     """ Parse path and return in format [directory, file].
#     """
#     root_len = len(root_path)
#     parsed_list = full_path[root_len+1:].split('/')    
    
#     return parsed_list


def get_lemmas(redirect_file_PATH):
    lemmas = set()
    with open(redirect_file_PATH) as file:
        for line in file:
            lemma, redirect_title, ch_title, total_count, counter = line.strip().split('\t')
            if(lemma[0].islower() and int(total_count) > 1 and lemma in all_wn_words):
                lemmas.add(lemma)
    return lemmas


def get_words_alias(redirect_file_PATH):
    """ 
    Read "en.link.redirect" file; get alias data of target_words. "en.link.redirect" should be renamed as en.anchorlink.txt
    Input:
        redirect_file_PATH: "en.link.redirect" file. 
            - File format: 
            - Example: zygotic    Zygote  16  Counter({'[[zygotic]]': 6, '[[zygote|zygotic]]': 6, '[[Zygote|zygotic]]': 4})
    Return:
        rev_words_alias(dict): {alias: (word, sense)}
        - Example: rev_words_alias['party'] = ('social', 'Party')
    """
    rev_words_alias = {}

    tStart = time.time()
    print("Start getting word alias ...")
    lemma_wikiSense = defaultdict(lambda: defaultdict(lambda: set()))
    with open(redirect_file_PATH) as file:
        for line in file:
            lemma, redirect_title, ch_title, total_count, counter = line.strip().split('\t')
            if(lemma[0].islower() and int(total_count) > 1 and lemma in all_wn_words):
                for s in re.finditer(r'\[\[[^\[\]]+|[^\[\]]+\]\]', counter):
                    lemma_wikiSense[lemma][redirect_title].add(s.group().split('|')[0][2:])

    for lemma in lemma_wikiSense:
        for wikiSense in lemma_wikiSense[lemma]:
            for page in lemma_wikiSense[lemma][wikiSense]:
                rev_words_alias[page] = (lemma, wikiSense)
    tEnd = time.time()
    print("Finished getting word alias. Cost %f sec" % (tEnd - tStart))
                    
    return rev_words_alias


def extract_sent(words_alias, jsonlines):
    """
    Check all redirect links in wiki texts. 
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

    # A line is a page
    for line in jsonlines:
        json_data  = json.loads(line)
        wiki_id    = json_data["id"]
        lines_list = json_data["text"]
        for line_info in lines_list:
            line = line_info["line"]
            for start_idx, end_idx, page in line_info["links"]:
                if page in words_alias:
                    word = words_alias[page][0]
                    wiki_sense = words_alias[page][1]
                    # Make sure "political party" as "party", not as "political party"
                    if line[start_idx:end_idx] == word:
                        if (word not in ex_sent.keys()):
                            ex_sent[word] = {}
                        if (wiki_sense not in ex_sent[words_alias[page][0]]):
                            ex_sent[word][wiki_sense] = []
                        ex_sent[word][wiki_sense].append((line, wiki_id, start_idx, end_idx))

    numOfSent = 0
    for word in ex_sent:
        for wikiSense in ex_sent[word]:
            numOfSent += len(ex_sent[word][wikiSense])

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
    wiki_lines          = read_wikifiles(ROOT_PATH)
    lemmas              = get_lemmas("/home/nlplab/patina/WikiSense/data/en.link.redirect.txt")
    words_alias         = get_words_alias("/home/nlplab/patina/WikiSense/data/en.link.redirect.txt")
    ex_sents, numOfSent = extract_sent(words_alias, wiki_lines)
    print("例句總數：", numOfSent)

    # print("Writing 30_words_set.json...")
    # result = {}
    # with open('30_words_set.json', 'wb') as fp:
    #     for word in tqdm.tqdm(words_30):
    #         if(word in ex_sents.keys()):
    #             result[word] = ex_sents[word]
    #     json.dump(result, fp, indent=4)
    # print("Finisjed writing 30_words_set.json")

    print("Writing full_set_idx.json...")
    result = {}
    with open('full_set_idx.json', 'wb') as fp:
        for word in tqdm.tqdm(lemmas):
            if(word in ex_sents.keys()):
                # fp.write(word.encode('utf8')+b'\t')
                # fp.write(json_util.dumps(ex_sents[word], ensure_ascii=False).encode('utf8')+b'\n')
                result[word] = ex_sents[word]
        fp.write(json.dumps(result, ensure_ascii=False, indent=4).encode('utf8'))
    print("Finished writing full_set_idx.json")
    

if __name__ == "__main__":
    main()