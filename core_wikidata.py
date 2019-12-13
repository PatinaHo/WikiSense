import networkx as nx
import bz2
import requests
import json
import pydash
from collections import defaultdict
from tqdm import tqdm

class Wikidata:
    def create_graph(self, graph, filePATH, line_count):
        """ Graph node: item page (not sure if property page is also there);
                  edge: property relation.
        Input:
            filePath - Wikidata jsonline file.
        """
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

        with tqdm(total=line_count, desc='Building graph ...') as pbar:
            for record_idx, record in enumerate(wikidata(filePATH)):
                from_page = record['id']

                if from_page not in graph:
                    graph.add_node(from_page)

                for p_num in record['claims']:
                    for to_page in pydash.get(record, 'claims.'+p_num):
                        if to_page not in graph:
                            graph.add_node(to_page)
                        graph.add_edge(from_page, to_page, property=p_num)
                pbar.update(1)


    def read_page_index(self, filePATH):
        with open(filePATH, 'r') as f:
            data = f.readlines()
        index_data = dict()
        for line in tqdm(data, desc='Reading index ...'):
            index_data[line.strip().split('\t')[0]] = line.strip().split('\t')[1]
            
        return index_data


    def __init__(self, wikidata_filePATH, wikidataIndex_filePath, line_count):
        """ WD: wikidata / WP:wikipedia
        Graph under construction, nodes: Q..., edges: P...
        Arguments:
            - wikidata_filePATH: bz2 jsonl file, after extracted.
        """
        self.graph     = nx.DiGraph()
        self.pageIndex = self.read_page_index(wikidataIndex_filePath)
        self.pageTitleIndex = {v: k for k, v in self.pageIndex.items()}
        self.create_graph(self.graph, wikidata_filePATH, line_count=line_count)


    def api_query(self, wikidataID):
        """ THIS IS A PRIVATE FUNCTION.
        Give parameters and return the WD api pack of namespace.
        This function should be called by other function to input parameter.
        """
        S = requests.Session()
        PARAMS = "Special:EntityData/" + wikidataID
        URL = "https://www.wikidata.org/wiki/" + PARAMS
        R = S.get(url=URL)
        
        return R.json()


    def sparql_query(self, query):
        S = requests.Session()
        URL = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"
        R = S.get(url=URL, params={'query': query, 'format': 'json'})
        
        return R.json()


    def apiGet_ID(self, wikidataTitle):
        """
        Give WD_page_title and return WD_page_id using API.
        Note that WD_page_title may not be the same with WP_page_title.
        """
        PARAMS = {
            "action":"query",
            "prop":"pageprops",
            "ppprop":"wikibase_item",
            "format":"json",
            "titles":wikidataTitle,
        }
        
        wikipediaID = str(get_wikipediaID(wikidataTitle))
        DATA = api_query(PARAMS)
        return DATA["query"]["pages"][wikipediaID]["pageprops"]["wikibase_item"]


    def apiGet_enLabel(self, wikidataID): 
        DATA = wikidata_query(wikidataID)
        return DATA['entities'][wikidataID]['labels']['en']['value']

    def apiGet_superclass(self, wikidata_pageID):
        """ Given Wikidata pageID and get en_label of its superclass.
        """
        query = """SELECT ?descendant ?descendantLabel\nWHERE\n{{
        wd:{wikidataID} wdt:P279 ?descendant.
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE]". }}\n}}"""
        DATA = sparql_query(query.format(wikidataID=wikidataID))
        superclass_IDs = [DATA['results']['bindings'][i]['descendantLabel']['value'] for i in range(len(DATA['results']['bindings']))]

        return [apiGet_enLabel(super_id) for super_id in superclass_IDs]


    # Wikidata path to root:"Q35120/entity" page
    def get_nearest_paths(self, page):
        """
        """
        try:
            l_idx = nx.all_shortest_paths(self.graph, source=page, target="Q35120")
        except nx.NodeNotFound:
            raise NodeNotFoundError("Page not found in graph.")
        except nx.NetworkXNoPath:
            raise NetworkXNoPathError("No path from Page:{} to Entity page".format(page))
        l_name = []
        for path in list(l_idx):
            l_name.append([self.pageIndex[idx] for idx in path])

        return l_idx, l_name

