from feature_selection import read_categories, get_parentCategories
from collections import Counter, defaultdict
from nltk.corpus import wordnet as wn
import logging
import nltk
import operator
import re

def get_definition(definitionFILE_PATH):
    """ Filter disambigation page and named entities page; then page read definition.
    - Input: wiki.definition.txt
        ex. Apple    An apple is a sweet, edible fruit produced by an apple tree (Malus pumila).
    - Return: 
        - definitions(dict, length: 4997097)
          ex. {"Apple": "An apple is a sweet, edible fruit produced by an apple tree (Malus pumila)."}
    """

    print("Reading definition...")
    definitions = defaultdict(str)
    with open(definitionFILE_PATH, 'r') as f:
        for line in f:
            title, definition = line.strip().split('\t')
            headword = re.sub(r' \(.+\)', '', title)
            # 篩掉 disambiguation page
            # 丟掉 Named entities (title出現在句子的中間且是大寫)
            if '(disambiguation)' not in title and headword not in definition[1:]:
                definitions[title] = definition
    print(f"Read {len(definitions)} page definitions.")
    return definitions


def get_keywords(definitions):
    """
    Keywords:  WordNet sense (itself and its hypernyms lemma) which Wikipage aligned to.
    - Return:
        - keywords(length: 100893): {WIKI_title: {synsets(of_title_headword): [hypernyms]}}
          ex. keywords["Apple"]
          {'apple.n.01': ['edible_fruit', 'pome', 'false_fruit', 'fruit', 'produce', 'green_goods', 'green_groceries', 'garden_truck', 'reproductive_structure', 'food', 'solid_food', 'plant_organ', 'solid', 'plant_part', 'plant_structure', 'object', 'physical_object'],
           'apple.n.02': ['orchard_apple_tree', 'Malus_pumila', 'apple_tree', 'fruit_tree', 'angiospermous_tree', 'flowering_tree', 'tree', 'woody_plant', 'ligneous_plant', 'vascular_plant', 'tracheophyte', 'plant', 'flora', 'plant_life', 'object', 'physical_object']}
        - keyword2sense(length: 100893): {WIKI_title: {synsets(of_title_headword): {hypernym: synset(of_hypernym)}}}
          ex. keyword2sense["Apple"]
          {'apple.n.01': {'apple': 'apple.n.01', 'edible_fruit': 'edible_fruit.n.01', 'pome': 'pome.n.01', 'false_fruit': 'pome.n.01', 'fruit': 'fruit.n.01', 'produce': 'produce.n.01', 'green_goods': 'produce.n.01', 'green_groceries': 'produce.n.01', 'garden_truck': 'produce.n.01', 'reproductive_structure': 'reproductive_structure.n.01', 'food': 'food.n.02', 'solid_food': 'food.n.02', 'plant_organ': 'plant_organ.n.01', 'solid': 'solid.n.01', 'plant_part': 'plant_part.n.01', 'plant_structure': 'plant_part.n.01', 'object': 'object.n.01', 'physical_object': 'object.n.01'}, 
           'apple.n.02': {'apple': 'apple.n.02', 'orchard_apple_tree': 'apple.n.02', 'Malus_pumila': 'apple.n.02', 'apple_tree': 'apple_tree.n.01', 'fruit_tree': 'fruit_tree.n.01', 'angiospermous_tree': 'angiospermous_tree.n.01', 'flowering_tree': 'angiospermous_tree.n.01', 'tree': 'tree.n.01', 'woody_plant': 'woody_plant.n.01', 'ligneous_plant': 'woody_plant.n.01', 'vascular_plant': 'vascular_plant.n.01', 'tracheophyte': 'vascular_plant.n.01', 'plant': 'plant.n.02', 'flora': 'plant.n.02', 'plant_life': 'plant.n.02', 'object': 'object.n.01', 'physical_object': 'object.n.01'}}
    """

    print("Looking for keywords in Wiki definitions...")
    keywords = defaultdict(list)
    keyword2sense = defaultdict(dict)
    reserved_words = ['act', 'animal', 'artifact', 'attribute', 'body', 'cognition', 
                    'communication', 'event', 'feeling', 'food', 'group', 'location',
                    'motive', 'object', 'person', 'phenomenon', 'plant', 'possession',
                    'process', 'quantity', 'relation', 'shape', 'state',
                    'substance', 'time']

    for title in definitions:
        names  = {}
        kw_syn = {}
        headword = re.sub(r' \(.+\)', '', title)
        for synset in wn.synsets(headword, 'n'):
            hyper_syn = list(synset.closure(lambda s:s.hypernyms())) + list(synset.closure(lambda s:s.instance_hypernyms()))
            words = []
            word_synsets = {}
            words.extend(synset.lemma_names())
            for name in synset.lemma_names():
                word_synsets[name] = synset.name()
            for hypernym in hyper_syn:
                if hypernym.lexname() != 'noun.Tops' or hypernym.name().split('.')[0] in reserved_words:
                    words.extend(hypernym.lemma_names())
                    for name in hypernym.lemma_names():
                        word_synsets[name] = hypernym.name()
            if headword in words:
                words.remove(headword)          # 去掉 Page title 本身 (headword) (ex. Eskimo)
            if headword.lower() in words:
                words.remove(headword.lower())  # 去掉 Page title 本身 (headword) (ex. Party->party)
            names[synset.name()] = words
            kw_syn[synset.name()] = word_synsets
                
        if names:
            keywords[title] = names
            keyword2sense[title] = kw_syn

    print(f"{len(keywords)} Wikipages found keywords in their definitions.")
    return keywords, keyword2sense

def get_keywords_score(definitions, keywords):
    """
    Count the score of keywords based on its location in definition, keywords which appear in the front of definition gets higher score.
    - Return:
        - keywords_score(length: 100893)
        ex: keywords_score['Party']
        {'definition': 'A party is a gathering of people who have been invited by a host for the purposes of socializing, conversation, recreation, or as part of a festival or other commemoration of a special occasion.',
        'keywords': {'party.n.02': {34: 'gathering'}, 'party.n.04': {2: 'occasion'}}}
    """
    print("Computing keyword scores...")
    keywords_score = {}
    USELESS_GT = {"group"}
    ILLUSTRATE_WORD = [" is a ", " is an ", " is the ", " refer to ", " refers to "]

    for i, title in enumerate(keywords):
        tmp = {}
        for wn_sense in keywords[title]:
            matched_keywords = {}
            for keyword in keywords[title][wn_sense]:
                # WikiDef 的括弧去掉，從 is a / is an / is the / refer to / refers to 切開，只用之後的字
                # 如果 definition 沒有這些字，就丟掉這筆資料
                valid_def = re.sub(r'\(.+\)', '', definitions[title])
                if(any(word in valid_def for word in ILLUSTRATE_WORD)):
                    illustrate_word = [word for word in ILLUSTRATE_WORD if word in valid_def][0]
                    valid_def = ' '.join(valid_def.split(illustrate_word)[1:])
                    tokenized_definition = nltk.word_tokenize(valid_def)
                    if keyword.replace('_', ' ') in tokenized_definition and keyword not in USELESS_GT:
                        keyword_idx = tokenized_definition.index(keyword.replace('_', ' '))
                        score = len(tokenized_definition) - keyword_idx
                        matched_keywords[score] = keyword
            if matched_keywords:
                tmp[wn_sense] = matched_keywords
        if tmp:
            keywords_score[title] = {}
            keywords_score[title]['definition'] = definitions[title]
            keywords_score[title]['keywords'] = tmp

    return keywords_score


def align_synset(keywords_score, keyword2sense, definitions):
    """
    Synset with highest sum of scores is the aligned sense of the page;
    if multiple synsets have same highest score, choose the synset with smallest number as the alligned sense.
    - Input: 
      ex. keyword_score['Absorption (acoustics)']
          {'definition': 'Acoustic absorption refers to the process by which a material, structure, or object takes in sound energy when sound waves are encountered, as opposed to reflecting the energy.',
          'keywords': {'absorption.n.01': {27: 'process'},
          'absorption.n.02': {27: 'process'},
          'assimilation.n.02': {27: 'process'},
          'assimilation.n.03': {27: 'process'}}}
      ex. keyword_score['Idiom']
          {'definition': 'An idiom ( from , "special feature, special phrasing, a peculiarity", f. , "one\'s own") is a phrase or an expression that has a figurative, or sometimes literal, meaning.',
          'keywords': {'parlance.n.01': {12: 'expression'},
                       'idiom.n.04': {15: 'phrase', 12: 'expression'}}}
    - Return: alignResult
        ex. alignResult['Absorption']
            {'WN_synset': 'absorption.n.01',
             'origGT': 'process.n.06',
             'WIKI_def': 'Acoustic absorption refers to the process by which a material, structure, or object takes in sound energy when sound waves are encountered, as opposed to reflecting the energy.',
             'WN_def': '(chemistry) a process in which one substance permeates another; a fluid permeates or is dissolved by a liquid or solid'}
    """

    print("Aligning WNsynset to Wikipages... based on keyword scores.")
    alignResult = {}
    for title in keywords_score:
        synset_scores  = {synset: sum(keywords_score[title]['keywords'][synset].keys()) for synset in keywords_score[title]['keywords']}
        max_score = max(synset_scores.items(), key=operator.itemgetter(1))[1]
        matched_synset = [synset for synset, score in synset_scores.items() if score == max_score][0]

        highestScoreGT = max(keywords_score[title]['keywords'][matched_synset].items(), key=operator.itemgetter(1))[1]
        GT = keyword2sense[title][matched_synset][highestScoreGT]
        alignResult[title] = {'WN_synset': matched_synset,
                              'origGT': GT,
                              'WIKI_def': definitions[title],
                              'WN_def': wn.synset(matched_synset).definition()}
    print("Finished alignment.")

    return alignResult


def GT_refine(alignResult, GTfreqThreshold):
    """
    Limit number of GTs by setting threshold for less frequent GTs.
    Less frequent GTs will be reassigned to higher level hypernyms (which is also GT); or be filtered out.
    - Input: alignResult
    - Return:
        - alignResult
        ex. alignResult['Absorption']
            {'WN_synset': 'absorption.n.01',
             'origGT': 'process.n.06',
             'refinedGT': '', 
             'WIKI_def': 'Acoustic absorption refers to the process by which a material, structure, or object takes in sound energy when sound waves are encountered, as opposed to reflecting the energy.',
             'WN_def': '(chemistry) a process in which one substance permeates another; a fluid permeates or is dissolved by a liquid or solid'}
    """

    GTs = [title_info['origGT'] for title, title_info in alignResult.items()]
    GT_count = Counter(GTs)
    GT_count_clean = dict(GT_count)
    GT_category    = {}
    
    for gt in GT_count:
        if GT_count[gt] < GTfreqThreshold:
            synset = wn.synset(gt)
            # 只取第一個路徑
            hypers = synset.hypernym_paths()[0]
            hypers.reverse()
            for hyper in hypers:
                if hyper.name() in GT_count and GT_count[hyper.name()] >= GTfreqThreshold:
                    GT_count_clean[hyper.name()] += GT_count_clean[gt]
                    GT_category[gt] = hyper.name()
                    break
            # 不論有沒有找到可以另外歸的 GT，只要小於 GTfreqThreshold 就刪除
            del GT_count_clean[gt]
        else:
            GT_category[gt] = gt
    print(f"{len(GT_category)} GTs are refined to {len({gt_cat for gt, gt_cat in GT_category.items()})} categories.")
    
    titles = [title for title in alignResult]
    for title in titles:
        origGT = alignResult[title]['origGT']
        if origGT in GT_category:
            alignResult[title]['refinedGT'] = GT_category[origGT]
        else:
            del alignResult[title]
                    
    return alignResult


def excl_disambigPage(alignResult, pageCat, parentCatsID, id2cat, cat2id):
    """
    Check categories of all pages. Most pages with [] empty categories are disambiguate pages.
    """
    
    cleanAlignResult = {}
    disambigPage = set()
    
    for title in alignResult:
        parentsName = get_parentCategories(title, pageCat, parentCatsID, id2cat, cat2id)
        if parentsName==[]:
            disambigPage.add(title)
            
    cleanAlignResult = {title:title_info for title, title_info in alignResult.items() if title not in disambigPage}
    print(f"{len(cleanAlignResult)} pairs generated.")
    
    return cleanAlignResult


def writeFile(alignResult, newFilePATH):
    print("Writing file...")
    writer = []
    for title, title_info in alignResult.items():
        writer.append(f"{title}\t{title_info['WN_synset']}\t{title_info['refinedGT']}\t{title_info['origGT']}\t-{title_info['WIKI_def']}\t-{title_info['WN_def']}")
        
    with open(newFilePATH, 'w') as f:
        f.write('\n'.join(writer))
    print(f"Done writing File. Location: {newFilePATH}")


def main():
    definitions = get_definition('/home/nlplab/cykuo/textnet/wiki.definition.txt')
    keywords, keyword2sense = get_keywords(definitions)
    keywords_score = get_keywords_score(definitions, keywords)
    alignResult = align_synset(keywords_score, keyword2sense, definitions)
    newAlignResult = GT_refine(alignResult, GTfreqThreshold=10)
    pageCat, parentCatsID, id2cat, cat2id = read_categories()
    newAlignResult = excl_disambigPage(newAlignResult, pageCat, parentCatsID, id2cat, cat2id)
    writeFile(newAlignResult, newFilePATH="/home/nlplab/patina/WikiSense/data/hypernym_definition_gt.txt")
    

if __name__ == "__main__":
    main()