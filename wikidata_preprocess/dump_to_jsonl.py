"""
Convert Wikidata dump records to JSON stream (one JSON object per line).

Parallel command:
cat /home/nlplab/patina/WikiSense/data/latest-all.json | tqdm --total=62372998 | parallel --pipe --block 2G-1 --lb "python dump_to_jsonl.py">wikidata.pages.jsonl

Command:
cat /home/nlplab/patina/WikiSense/data/latest-all.json | tqdm --total=62372998 | python dump_to_jsonl.py |bzip2 > wikidata.pages.jsonl.bz2
"""

import fileinput


if __name__ == "__main__":
    for line in fileinput.input():
        json_line = line[:-2]
        if json_line:
            print(json_line)