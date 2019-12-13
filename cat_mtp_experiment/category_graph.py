"""
Seems to have the same function as generate_cat2mtp.py,
and is not adopted to do anything?
"""

import re
import tqdm

def read_maintopic(PATH):
    with open(PATH) as f:
        mainTopic = [mt.strip() for mt in f.readlines()]
    return mainTopic

def get_catId(data, mainTopic):
    """ Given the title of category and give id numbers; store in a dictionary.
    return:
        catId(dict): {0: 'Category:Futurama', 1: 'Category:World War II', ... }
    """

    # title 即 category
    titles = [line.strip().strip('<title>Category:').strip('</title>') for line in data if line.startswith('<title>')]

    catId = {}
    i = 0
    for title in mainTopic:
        catId[title] = i
        i += 1
    for title in titles:
        if title not in catId.keys():
            catId[title] = i
            i += 1

    return catId

def get_edges(data, catId):
    """ Generate edges in a dict.
    return:
        edges = {childId: [parentId0, parentId1, ...]}
    """
    error_writer = open("error_log", "w")

    edges = set()
    childId = -1
    edges = {}
    for line in tqdm.tqdm(data):
        try:
            if line.startswith('<title>'):
                childCat  = line.strip().strip('<title>Category:').strip('</title>')
                childId   = catId[childCat]
                edges[childId] = []
            elif line.startswith('[[Category:'):
                parentCat = line.strip('[[Category:').strip(']]\n')
                parentId  = catId[parentCat]
                edges[childId].append(parentId)
        except KeyError:
            print("childCat =", childCat, file=error_writer)
            print(line, file=error_writer)
            pass

    error_writer.close()
    return edges

# def get_edges(data, catId):
#     """ Generate edges in a set.
#     return:
#         edges(set): {(parentId, childId), ...}
#     """
#     error_writer = open("error_log", "w")

#     edges = set()
#     childId = -1
#     for line in tqdm.tqdm(data):
#         try:
#             if line.startswith('<title>'):
#                 childCat = line.strip().strip('<title>Category:').strip('</title>')
#                 childId += 1
#             elif line.startswith('[[Category:'):
#                 parentCat = line.strip('[[Category:').strip(']]\n')
#                 parentId  = catId[parentCat]
#                 edges.add((parentId, childId))
#         except KeyError:
#             print("childCat =", childCat, file=error_writer)
#             print(line, file=error_writer)

#     error_writer.close()
#     return edges

def get_graph_file(PATH, edges, mainTopic):
    writer = open(PATH, "w")
    for childId in tqdm.tqdm(edges):
        if(childId > len(mainTopic)):
            print(childId, end=" ", file=writer)
        for parentId in edges[childId]:
            print(parentId, end=' ', file=writer)
        print('', file=writer)
    writer.close()


def main():
    with open("/home/nlplab/patina/WikiSense/data/wiki.cat.super.txt", "r") as f:
        data = f.readlines()

    mainTopic = read_maintopic("/home/nlplab/patina/WikiSense/data/wiki.maintopic.txt")
    catId = get_catId(data, mainTopic)
    edges = get_edges(data, catId)
    get_graph_file("/home/nlplab/patina/WikiSense/data/wiki.cat.maintopic.txt", edges, mainTopic)
    

if __name__ == "__main__":
    main()
