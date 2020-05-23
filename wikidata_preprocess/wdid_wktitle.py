import json
import sys

if __name__ == "__main__":
    for line in open(sys.stdin.fileno(), 'rt'):
        json_line = json.loads(line.strip())
        wdId    = json_line['id']
        wktitle = json_line['sitelinks']['enwiki']
        if json_line and wktitle is not None:
            print(f'{wdId}\t{wktitle}')
