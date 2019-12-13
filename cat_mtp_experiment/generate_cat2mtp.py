""" 
Create Wikipedia category graph, compute MAINTOPIC for each wiki page using shortest_path method.
Generate: wiki.cat_mtp.name.json
{   "Computer science": [
        "Technology"
    ],
    "The Simpsons": [
        "Entertainment",
        "Humanities"
    ],
    "Algorithms": [
        "Mathematics"
    ],
}
"""

import json
import tqdm
import networkx as nx

G = nx.read_adjlist('/home/nlplab/patina/WikiSense/data/wiki.cat.parent.adjlist', create_using = nx.DiGraph(), nodetype = int)

def read_json(PATH):
    with open(PATH) as json_file:
        data = json.load(json_file)
    return data

def read_maintopic(PATH):
    with open(PATH) as f:
        mainTopics = [mt.strip() for mt in f.readlines()]
    return mainTopics

def get_mainTopic(nodeId, mainTopics):
    shortest_path_legths = []
    for i in range(len(mainTopics)):
        try:
            shortest_path_legths.append(nx.shortest_path_length(G, source=nodeId, target=i))
        except:
            shortest_path_legths.append(10000)
    
    if min(shortest_path_legths) == 10000:
        shortest_mtp_id = None
    else:
        shortest_mtp_id = [idx for idx, length in enumerate(shortest_path_legths) if length == min(shortest_path_legths)]
    return shortest_mtp_id


def main():
    # catId = read_json('/home/nlplab/patina/WikiSense/data/catId.json')
    idCat = read_json('/home/nlplab/patina/WikiSense/data/wiki.idCat.json')
    mainTopics = read_maintopic("/home/nlplab/patina/WikiSense/data/wiki.maintopic.txt")

    catMaintopicId = {}
    for node in tqdm.tqdm(range(len(G.nodes)), desc='Generating mtp for cat: '):
        catMaintopicId[int(node)] = get_mainTopic(node, mainTopics)

    with open('/home/nlplab/patina/WikiSense/data/wiki.cat_mtp.id.json', 'w') as fp:
        json.dump(catMaintopicId, fp)

    catMaintopicName = {}
    for node in catMaintopicId:
        if (catMaintopicId[node] is not None):
            catMaintopicName[idCat[str(node)]] = [idCat[str(parendId)] for parendId in catMaintopicId[node]]
        else:
            catMaintopicName[idCat[str(node)]] = None

    with open('/home/nlplab/patina/WikiSense/data/wiki.cat_mtp.name.json', 'w') as fp:
        json.dump(catMaintopicName, fp, indent=4)

if __name__ == "__main__":
    main()



