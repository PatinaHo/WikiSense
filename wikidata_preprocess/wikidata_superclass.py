import requests
import json
from collections import defaultdict

WORDS_30 = ["argument", "arm", "atmosphere", "bank", "bar", "chair", "channel", "circuit", "degree", "difference", 
            "disc", "dyke", "fatigue", "grip", "image", "material", "mouth", "nature", "paper", "party", 
            "performance", "plan", "post", "restraint", "sense", "shelter", "sort", "source", "spade", "stress"]

def wikipedia_query(PARAMS):
    S = requests.Session()
    URL = "https://en.wikipedia.org/w/api.php"
    R = S.get(url=URL, params=PARAMS)
    
    return R.json()


def get_wikipediaID(wikiTitle):
    PARAMS = {
        "action":"query",
        "prop":"pageprops",
        "ppprop":"wikibase_item",
        "format":"json",
        "titles":wikiTitle,
        "formatversion":2,
    }
    DATA = wikipedia_query(PARAMS)
    return DATA["query"]["pages"][0]["pageid"]


def get_wikidataID(wikiTitle):
    PARAMS = {
        "action":"query",
        "prop":"pageprops",
        "ppprop":"wikibase_item",
        "format":"json",
        "titles":wikiTitle,
    }
    
    wikipediaID = str(get_wikipediaID(wikiTitle))
    DATA = wikipedia_query(PARAMS)
    return DATA["query"]["pages"][wikipediaID]["pageprops"]["wikibase_item"]


def wikidata_query(query):
    S = requests.Session()
    URL = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"
    R = S.get(url=URL, params={'query': query, 'format': 'json'})
    
    return R.json()


def get_enLabel(wikidata_pageID):
    PARAMS = "Special:EntityData/" + wikidata_pageID
    
    S = requests.Session()
    URL = "https://www.wikidata.org/wiki/" + PARAMS
    R = S.get(url=URL).json()
    
    return R['entities'][wikidata_pageID]['labels']['en']['value']


### 需要學習怎麼打內含{}的 formatted string
def get_superclass(wikidata_pageID):
    """ Given Wikidata pageID and get en_label of its superclass.
    """
    query = """
    SELECT ?descendant ?descendantLabel
    WHERE
    {
        wd:""" + wikidata_pageID + """ wdt:P279 ?descendant.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]". }
    }
    """
    DATA = wikidata_query(query)
    superclass_IDs = [DATA['results']['bindings'][i]['descendantLabel']['value'] for i in range(len(DATA['results']['bindings']))]

    return [get_enLabel(super_id) for super_id in superclass_IDs]


def readfile_redirect(PATH):
    with open(PATH, 'r', encoding="utf-8") as f:
        data = f.readlines()

    redirects = defaultdict(lambda: dict())
    
    titles      = [line.split('\t')[0] for line in data]
    redir_pages = [line.split('\t')[1] for line in data]
    counts      = [line.split('\t')[3] for line in data]
    for idx, title in enumerate(titles):
        redirects[title][redir_pages[idx]] = counts[idx]
    
    return redirects


redirects = readfile_redirect('/home/nlplab/patina/WikiSense/data/en.link.redirect.txt')
writer = open("wikidata_superclass.txt", "w")
for word in WORDS_30:
    print("Processing word:", word, "...")
    print(word, "\n----------\n", file=writer)
    for redirect in redirects[word]:
        if(int(redirects[word][redirect]) > 1):
            try:
                wikidata_pageID = get_wikidataID(redirect)
                print(redirect, int(redirects[word][redirect]), wikidata_pageID, get_superclass(wikidata_pageID), sep='\t', file=writer)
            except:
                print("@@@", redirect, "no result.", file=writer)
    print("\n", file=writer)

writer.close()