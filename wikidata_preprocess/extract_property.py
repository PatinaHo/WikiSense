#!/usr/bin/env python3

""" 
Extract desired properties from Wikidata dump records.
Wikidata dump records need to be converted to JSON stream first (one JSON object per line).

Command:
python extract_property.py -d /home/nlplab/jjc/wiki/wikidata.pages.jsonl.bz2 -e ./data/wikidata.pages.extract.jsonl.bz2
-d: dumpfile as jsonline format
-e: extracted file name

Modified script taken from this link: "https://akbaritabar.netlify.com/how_to_use_a_wikidata_dump
"""

import bz2
import json
import pandas as pd
import pydash
import tqdm


def wikidata(filename):
    """ Load jsonline format wikidata file(latest-all.jsonl.bz2) as a generator of dictionaries.
    """
    with bz2.open(filename, mode='rt', encoding='UTF-8', errors='ignore') as f:
        for line in f:
            try:
                yield json.loads(line.rstrip(',\n'))
            except json.decoder.JSONDecodeError:
                print("JSONDecodeError")
                continue

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


def 


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__
    )
    parser.add_argument(
        '-d',
        '--dumpfile',
        help=(
            'a Wikidata dumpfile from: '
            'https://dumps.wikimedia.org/wikidatawiki/entities/'
            'latest-all.json.bz2'
        )
    )
    parser.add_argument(
        '-e',
        '--extractFileName',
        help=('Name of the file generated.')
    )

    args = parser.parse_args()
    # Should change the way of getting propertyToSave, get from args
    propertyToSave = ['P31', 'P279', 'P2888']

    with bz2.open(args.extractFileName, "wt") as f:
        # How to properly use tqdm?
        for jsl_idx, record in enumerate(wikidata(args.dumpfile)):
            if jsl_idx%5000==0:
                print('{jsl_idx} / 62372998, {progress:.4f}%'.format(jsl_idx=jsl_idx, progress=float(jsl_idx/62372998)), end='\r')
            jsonl = {}
            jsonl['id']   = pydash.get(record, 'id')
            jsonl['type'] = pydash.get(record, 'type')
            jsonl['labels']        = {key:pydash.get(record, 'labels.'+key+'.value') for key in ['en', 'zh-hant', 'zh-hans']}
            jsonl['descriptions']  = {key:pydash.get(record, 'descriptions.'+key+'.value') for key in ['en', 'zh-hant', 'zh-hans']}
            jsonl['sitelinks']     = {key:pydash.get(record, 'sitelinks.'+'.title') for key in ['enwiki', 'zhwiki']}
            jsonl['claims']        = {}
            for ppty in propertyToSave:
                if check_property(record, ppty) != None:
                    jsonl['claims'][ppty] = check_property(record, ppty)
            if (jsonl['claims'] != {}):
                f.write(json.dumps(jsonl))
                f.write('\n')
