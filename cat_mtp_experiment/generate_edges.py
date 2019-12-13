"""
Generate .adjlist format file for nx package to create Wiki category graph.

Input: wiki.cat.super.txt
<title>Category:Futurama</title>
{{Commons cat|Futurama}}
{{Cat main|Futurama}}
[[Category:Television series by 20th Century Fox Television]]

Generates: wiki.cat.parent.adjlist
40 10185 77722 98458 419280
41 162055 84916 71925
42 710654
43 85 37369 223320 431221 743135 443403 1424837 387112 769553
44 42
"""

import re
import json
import tqdm

def read_maintopic(PATH):
    with open(PATH) as f:
        mainTopics = [mt.strip() for mt in f.readlines()]
    return mainTopics

def generate_catId(PATH, mainTopics):
    """ Given the title of category and give id numbers; dictionary format and save in json file.
    return: None
    generate:
        catId.json : {'Category:Futurama': 0, 'Category:World War II': 1, ... }
        idCat.json : {0: 'Category:Futurama', 1: 'Category:World War II', ... }
    """

    # title 即 category
    print("Generating catId...")
    with open(PATH) as f:
        # titles = [line.strip().strip('<title>Category:').strip('</title>') for line in f.readlines()]
        titles = [line.strip()[16:-8] for line in f.readlines()]

    catId = {}
    i = 0
    for title in mainTopics:
        catId[title] = i
        i += 1
    for title in titles:
        if title not in catId.keys():
            catId[title] = i
            i += 1
    idCat = {y:x for x,y in catId.items()}

    with open('/home/nlplab/patina/WikiSense/data/catId.json', 'w') as fp:
        json.dump(catId, fp)
    with open('/home/nlplab/patina/WikiSense/data/idCat.json', 'w') as fp:
        json.dump(idCat, fp)
    return

def read_catId(PATH):
    with open(PATH) as json_file:
        data = json.load(json_file)
    return data

def get_edges(data, catId):
    """ Generate edges in a dict.
    return:
        edges = {childId: [parentId0, parentId1, ...]}
    """

    error_writer = open("error_log", "w")

    edges = set()
    childId = -1
    edges = {}
    for line in tqdm.tqdm(data, desc="Generate edges:"):
        try:
            if line.startswith('<title>'):
                childCat  = line.strip()[16:-8]
                childId   = catId[childCat]
                edges[childId] = []
            elif line.startswith('[[Category:'):
                parentCat = line.strip()[11:-2].split('|')[0]
                parentId  = catId[parentCat]
                edges[childId].append(parentId)
        except KeyError:
            print("childCat =", childCat, file=error_writer)
            print(line, file=error_writer)
            pass

    error_writer.close()
    return edges

def generate_graph_file(PATH, edges, mainTopics):
    writer = open(PATH, "w")
    for childId in tqdm.tqdm(edges, desc="Write edges file:"):
        if(childId > len(mainTopics)):
            print(childId, end=" ", file=writer)
        for parentId in edges[childId]:
            print(parentId, end=' ', file=writer)
        print('', file=writer)
    writer.close()


def main():
    with open("/home/nlplab/patina/WikiSense/data/wiki.cat.super.txt", "r") as f:
        data = f.readlines()

    mainTopics = read_maintopic("/home/nlplab/patina/WikiSense/data/wiki.maintopic.txt")
    generate_catId("/home/nlplab/patina/WikiSense/data/wiki.cat.txt", mainTopics)

    catId = read_catId('/home/nlplab/patina/WikiSense/data/catId.json')
    edges = get_edges(data, catId)
    generate_graph_file("/home/nlplab/patina/WikiSense/data/wiki.cat.parent.adjlist", edges, mainTopics)
    

if __name__ == "__main__":
    main()
