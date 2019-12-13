""" 
Get Wikidata index list records from extracted Wikidata.

Command:
python gen_wikidata_index.py
"""

import bz2
import json
import pydash
from collections import defaultdict
from tqdm import tqdm_notebook, tqdm


writer = open("/home/nlplab/patina/WikiSense/data/wikidata.pages.id.enTitle.index", "w")

def wikidata(filename):
    """ Process Wikidata jsonline bz2 file, yield each line as a dict.
    """
    with bz2.open(filename, mode='rt') as f:
        for line in f:
            try:
                yield json.loads(line.rstrip(',\n'))
            except json.decoder.JSONDecodeError:
                print("json.decoder.JSONDecodeError")
                continue

with tqdm(total=59189275) as pbar:
    for record_idx, record in enumerate(wikidata("/home/nlplab/patina/WikiSense/data/wikidata.pages.extract.jsonl.bz2")):
        pageID  = record["id"]
        if pydash.has(record, 'labels.en.value'):
            enTitle = record["labels"]["en"]["value"]
        print(pageID, enTitle, sep='\t', file=writer)
        pbar.update(1)