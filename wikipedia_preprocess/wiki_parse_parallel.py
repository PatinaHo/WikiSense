"""
Parse wikipedia dump.
Extract hyperlinks from raw sentences, save as [start_pos, end_pos, hyperlinked_title].

Example:
"text": [{
    "line": "Anarchism is an anti-authoritarian political philosophy that advocates self-managed, self-governed societies based on voluntary, cooperative institutions and the rejection of hierarchies those societies view as unjust.", 
    "links": [[16, 34, "Anti-authoritarianism"], [35, 55, "political philosophy"], [71, 83, "Workers' self-management"], [85, 98, "Self-governance"], [129, 140, "cooperative"], [175, 186, "Hierarchy"]]
    }, ...]
"""

import os
import json
import re
import spacy
import time
import urllib.parse
from bson import json_util
from math import sqrt, modf
from joblib import Parallel, delayed
import logging

# from __future__ import print_function, unicode_literals
from pathlib import Path
from joblib import Parallel, delayed
from functools import partial
import thinc.extra.datasets
import plac
import spacy
from spacy.util import minibatch


# error_file = open("error_wikiparse.log", "w")
# logging.basicConfig(level=logging.INFO)

spacy.prefer_gpu()
nlp = spacy.load("en_core_web_sm", disable=["ner"])

def link_extractor(text):
    """
    Input:
        text - Wiki texts, including tags.
    Output:
        result - {'line': ..., 'links': [(46, 59, 'Academy Awards'), ... ]}
        Value of 'line' is Wiki texts without tags; values of 'links' are (start_idx, end_idx, Wiki_title) of Wiki article.
    """
    href_matches = []
    for match in re.finditer(r'<a href="([^"]*)">([^<]*)</a>', text):
        href_matches.append(match)
        
    result = {"line": "", "links": []}
    start = 0
    for match in href_matches:
        
        href_start, href_end = match.span()
        href_text = match.group(2)
        href_link = urllib.parse.unquote(match.group(1))
        
        result["line"] += text[start:href_start] + href_text
        
        link_start = len(result["line"]) - len(href_text)
        link_end = len(result["line"])
        link_title = href_link
        
        result["links"].append((link_start, link_end, link_title))
        start = href_end
    
    result["line"] += text[start:]
    return result


def sentence_extractor(text):
    """
    Input:
        text - Wiki texts, including tags.
    Output:
        Generator. Need to list(output) and became:
        [{'line': ..., 'links': [(4, 17, 'Academy Awards'), ...]},
         {'line': ..., 'links': [(105, 124, '85th Academy Awards'), ...]},
         ...
         ]
    """
    
    for line in text.split("\n"):
        link_data = link_extractor(line)
        if not link_data['links']:
            continue
        
        doc = nlp(link_data["line"])
        
        link_count_start = 0
        for sent in doc.sents:
            sent_start, sent_end = sent.start_char, sent.end_char
            
            links = []
            links_count = 0
            
            for link_idx in range(link_count_start, len(link_data["links"])):
                link_start, link_end, link_title = link_data["links"][link_idx]
                if sent_start<=link_start and link_end<=sent_end:
                    links_count += 1
                    links.append((link_start-sent_start, link_end-sent_start, link_title))
            
            result = {"line": sent.text, "links": links}
            if links:
                yield result
                    
            link_count_start += links_count    
            
            if len(link_data['links']) == link_count_start:
                break


ROOT_PATH = "/home/nlplab/patina/Dataset/wiki_data"
OUTPUT_PATH = "/home/nlplab/patina/Dataset/wiki_parse_new"
# OUTPUT_PATH = "/home/nlplab/patina/WikiSense"


def generate_path(root_path):
    
    all_file_paths = []
    for root, dirs, files in os.walk(root_path):
        dirs = [d for d in dirs if not d[0] == '.']
        for d in dirs:
            dir_path = os.path.join(ROOT_PATH, d)
            for root, dirs, files in os.walk(dir_path):
                files = [f for f in files if not f[0] == '.']
                for f in files:
                    file_path = os.path.join(dir_path, f)
                    all_file_paths.append(file_path)
    
    return all_file_paths


def split_path(full_path, root_path):
    """ Parse path and return in format [directory, file].
    """
    root_len = len(root_path)
    parsed_list = full_path[root_len+1:].split('/')    
    
    return parsed_list


def get_parsed_files(output_path, directory):
    """ Get the list of files that already exists in output directory to avoid duplicate parsing and save time.
    """
    parsed_files = set(os.listdir(os.path.join(output_path, directory)))
    
    return parsed_files


def parse(root_path, output_path, batch_file_paths):
    """ Identify if the input file is already parsed, parse the new file and save in output directory.
    """
    for file_path in batch_file_paths:
        d, f = split_path(file_path, root_path)
        print(time.ctime(), "d =", d, "; f =", f)
#         print(time.ctime(), "d =", d, "; f =", f, file=error_file)
        if not os.path.exists(os.path.join(OUTPUT_PATH, d)):
            os.makedirs(os.path.join(OUTPUT_PATH, d))
        parsed_files = get_parsed_files(output_path, d)
        if f not in parsed_files:
            with open(file_path) as json_file:
                OUTPUT_FILE_PATH = os.path.join(OUTPUT_PATH, d, f)
                with open(OUTPUT_FILE_PATH, 'wb') as writer:
                    for num, line in enumerate(json_file):
                        json_data = json.loads(line)
                        parsed_data = list(sentence_extractor(json_data['text']))
                        json_data['text'] = parsed_data
                        writer.write(json_util.dumps(json_data, ensure_ascii=False).encode('utf8')+b'\n')
#                 print(time.ctime(), "File:", file_path, "processed.")

def main(output_dir, model="en_core_web_sm", n_jobs=20, batch_size=1000, limit=10000):
    
#     nlp = spacy.load(model)  # load spaCy model
#     print("Loaded model '%s'" % model)
    all_file_paths = generate_path(ROOT_PATH)
    partitions = minibatch(all_file_paths, size=batch_size)
    executor = Parallel(n_jobs=n_jobs, backend="multiprocessing", prefer="processes")
    do = delayed(partial(parse, ROOT_PATH, OUTPUT_PATH))
    tasks = (do(batch) for batch in partitions)
    executor(tasks)


main(OUTPUT_PATH)

# Start time: 7/21 18:40
