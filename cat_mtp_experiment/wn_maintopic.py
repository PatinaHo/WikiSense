from core_wiki import *

# WordNet
def get_unambig_daughter(wn_word, wiki_obj, pos='n'):
    """
    Return:
        unambig_dt(dict) = {'party.n.01': ['American_Party', 'Anti-Masonic_Party', 'Federalist_Party', 'Prohibition_Party', 'British_Labour_Party'],
                            'party.n.02': ['housewarming', 'shindig', 'soiree', 'gaudy'],
                            'party.n.03': [], ...}
    """
    unambig_dt = {}
    for syn in wn.synsets(wn_word, pos):
        hypos = lambda s:s.hyponyms()
        daughters = list(syn.closure(hypos)) # list of synsets

        ud = []
        for daughter in daughters:
            if (daughter.lemma_names()[0] in wiki_obj.unambig_words):
                ud.append(daughter.lemma_names()[0])    # 只取第一個

        unambig_dt[syn.name()] = ud

    return unambig_dt

(get_unambig_daughter(party))