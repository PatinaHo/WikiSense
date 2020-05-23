#!/usr/bin/env python3

""" 
Extract desired properties from Wikidata dump records.
Wikidata dump records need to be converted to JSON stream first (one JSON object per line).

Command:
cat /home/nlplab/jjc/wiki/wikidata.pages.jsonl | tqdm --total=62372998 | parallel --pipe --block 2G-1 --lb "python ~/WikiSense/wikidata_preprocess/extract_property_parallel.py" | bzip2 >wikidata.pages.extract.sitelinks.jsonl.bz2

Modified script taken from this link: "https://akbaritabar.netlify.com/how_to_use_a_wikidata_dump
"""

import bz2
import json
import pandas as pd
import pydash
import tqdm
import fileinput


def check_property(item_data, p_num):
    """ Check if p_num property is in item_data. Return list of id if True; None otherwise.
    Parameter:
        item_data(dict): json data of an item in wikidata.
        p_num(string): property number, example: "P31".
    Return:
        Example: ['Q3624078', 'Q43702', 'Q6256', 'Q20181813'].
    """
    if pydash.has(item_data, 'claims.'+p_num):
        return [pydash.get(item_data['claims'][p_num][idx], 'mainsnak.datavalue.value.id') for idx, item in enumerate(item_data['claims'][p_num])]
    return None


if __name__ == '__main__':

    # Should change the way of getting propertyToSave, get from args
    propertyToSave = ['P31', 'P279', 'P2888']

    # How to properly use tqdm?
    for jsl_idx, record in enumerate(fileinput.input()):
        record = json.loads(record)
        jsonl = {}
        jsonl['id']   = pydash.get(record, 'id')
        jsonl['type'] = pydash.get(record, 'type')
        jsonl['labels']        = {key:pydash.get(record, 'labels.'+key+'.value') for key in ['en', 'zh-hant', 'zh-hans']}
        jsonl['descriptions']  = {key:pydash.get(record, 'descriptions.'+key+'.value') for key in ['en', 'zh-hant', 'zh-hans']}
        jsonl['sitelinks']     = {key:pydash.get(record, 'sitelinks.'+key+'.title') for key in ['enwiki', 'zhwiki']}
        jsonl['claims']        = {}
        for ppty in propertyToSave:
            if check_property(record, ppty) != None:
                jsonl['claims'][ppty] = check_property(record, ppty)
        print(json.dumps(jsonl))
