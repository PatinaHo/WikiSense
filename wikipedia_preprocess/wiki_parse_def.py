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
import time
import urllib.parse
from bson import json_util
from math import sqrt, modf
from joblib import Parallel, delayed
import logging

from pathlib import Path
from joblib import Parallel, delayed
from functools import partial
import thinc.extra.datasets
import plac
from spacy.util import minibatch


ROOT_PATH = "/home/nlplab/patina/Dataset/wiki_parse_new"
OUTPUT_PATH = "/home/nlplab/patina/WikiSense/data/wiki_def"


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
        if not os.path.exists(os.path.join(OUTPUT_PATH, d)):
            os.makedirs(os.path.join(OUTPUT_PATH, d))
        parsed_files = get_parsed_files(output_path, d)
        if f not in parsed_files:
            with open(file_path) as json_file:
                OUTPUT_FILE_PATH = os.path.join(OUTPUT_PATH, d, f)
                with open(OUTPUT_FILE_PATH, 'w') as writer:
                    for num, line in enumerate(json_file):
                        json_data = json.loads(line)
                        title = json_data['title']
                        if json_data['text']:
                            definition = json_data['text'][0]['line']
                            writer.write(f'{title}\t{definition}\n')
                        else:
                            writer.write(f'{title}\tNone.\n')

def main(output_dir, n_jobs=20, batch_size=1000, limit=10000):
    
    all_file_paths = generate_path(ROOT_PATH)
    partitions = minibatch(all_file_paths, size=batch_size)
    executor = Parallel(n_jobs=n_jobs, backend="multiprocessing", prefer="processes")
    do = delayed(partial(parse, ROOT_PATH, OUTPUT_PATH))
    tasks = (do(batch) for batch in partitions)
    executor(tasks)


main(OUTPUT_PATH)
