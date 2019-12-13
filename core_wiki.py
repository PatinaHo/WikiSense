import networkx as nx
# import pickle
import json
import math
import requests
# import wikipediaapi
from collections import Counter

# from nltk.corpus import wordnet as wn

class Wiki:
    def create_graph(self, graph, categ_filePATH):
        """ Graph node: page or category page; 
                  edge: page belongs to category relation. (only 1 type)
        """
        with open(categ_filePATH,'rb') as file:
            link_dict = pickle.load(file)

        pages = set()

        for from_page in link_dict:
            if from_page not in graph:
                graph.add_node(from_page)
            if len(from_page) <= 9 or from_page[:9] != 'Category:':
                pages.add(from_page)
            for to_page in link_dict[from_page]:
                if to_page not in graph:
                    graph.add_node(to_page)
                graph.add_edge(from_page, to_page)
                

    def wiki_query(self, PARAMS):
        S = requests.Session()
        URL = "https://en.wikipedia.org/w/api.php"
        R = S.get(url=URL, params=PARAMS)

        return R.json()
    
    
    def get_subcat(self, wikicat, limit):
        PARAMS = {
            "action":"query",
            "format":"json",
            "list":"categorymembers",
            "cmtitle":wikicat,
            "cmlimit":limit,
            "cmtype":"subcat",
        }
        DATA = self.wiki_query(PARAMS)
        return [cat['title'] for cat in DATA['query']['categorymembers']]

    
    def get_wikidataID(self, title):
        """ Return None when title doesn't exist. """
        PARAMS = {
            "action":"query",
            "format":"json",
            "prop":"pageprops",
            "ppprop":"wikibase_item",
            "redirects":1,
            "titles":title
        }
        DATA = self.wiki_query(PARAMS)
        if len(DATA['query']['pages'].keys())==1:
            wikipediaID = list(DATA['query']['pages'].keys())[0]
        else:
            raise ValueError('More than 1 Wikipedia ID in this Title.')

        if wikipediaID == '-1':
            return None
        return DATA['query']['pages'][wikipediaID]['pageprops']['wikibase_item']


    def get_unambig_words(self, redirectLink_filePATH):
        """Get words that only redirect to one page.
        Returns:
            unambig_words(dict) - key: column1 in en.link.redirect.txt / value: column2 in en.link.redirect.txt
            {'assignee':'Assignment (law)', 'American_Party':'American_party', 'John_Doe':'John_doe' ...} 
        """
        with open(redirectLink_filePATH, 'r', encoding="utf-8") as f:
            data = f.readlines()
        titles    = [line.split('\t')[0] for line in data]
        redirects = [line.split('\t')[1] for line in data]
        unambig_lemma = {title for title, numOfLinks in Counter(titles).items() if numOfLinks == 1}
        unambig_words = {}
        for idx, title in enumerate(titles):
            if title in unambig_lemma:
                unambig_words[title] = redirects[idx]

        return unambig_words
    

    def read_redirect_file(PATH):
        """Return redirect information in dictionary, key: from_page / value: to_page.
        """
        with open(PATH, 'r', encoding='utf-8') as f:
            data = f.readlines()
        from_pages = [line.strip().split('\t')[1].strip("'") for line in data]
        to_pages   = [line.strip().split('\t')[2].strip("'") for line in data]
        redirects  = {}
        for idx, from_page in enumerate(from_pages):
            redirects[from_page] = to_pages[idx]

        return redirects
    
    
    def __init__(self, categ_filePATH, redirectLink_filePATH, redirect_filePATH):
        """
        self.cats(list) = ['Category:Main topic articles', 'Category:Academic disciplines', 'Category:Business', ...]
        self.unambig_words(dict): from column1 en.link.redirect.txt
        """
        self.cat_graph     = nx.DiGraph()
        self.create_graph(self.cat_graph, categ_filePATH)
        self.cats          = self.get_subcat('Category:Main_topic_classifications', limit=40)
        self.unambig_words = self.get_unambig_words(redirectLink_filePATH)
        self.__redirects__ = self.read_redirect_file(redirect_filePATH)


    # Wiki get multiple maintopics
    def get_nearest_mtp(self, page, cats):
        def shortest(page, cat):
            try:
                l = nx.shortest_path_length(self.cat_graph, page, cat)
            except:
                return math.inf
            else:
                return l
        try:
            l = [shortest(page, cat) for cat in cats]
            nearest_idx = [idx for idx, steps in enumerate(l) if steps==min(l)]
            nearest_mtp = [cats[i] for i in nearest_idx]
        except nx.NodeNotFound:
            nearest_mtp = "Page not found"
        except nx.NetworkXNoPath:
            nearest_mtp = "No path from Page:{} to maintopic".format(page)
        
        return nearest_mtp