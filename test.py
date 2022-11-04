import requests
import os

def get_request(url, params):
    try:
        r = requests.get(url = url, params = params)
        return r.json()
    except Exception as e:
        print(e)

def get_key():
    return "key="+str(os.getenv('API_KEY'))

def get_cx():
    return "cx=416041b5afb9e4692"

def get_query(query):
    return "q="+query

def get_url(query, start):
    return f"https://www.googleapis.com/customsearch/v1?{get_key()}&{get_cx()}&{get_query(query)}&num=10&start={start}"

def update_stopword(phrase, stopword):
    """
    File obtained from https://github.com/xiamx/node-nltk-stopwords/blob/master/data/stopwords/spanish 
    and modified so it can adapt to this program.
    """
    new_text = []
    phrase_splitted = phrase.split()
    for i in range(len(phrase_splitted)):
        if phrase_splitted[i] != stopword:
            new_text.append(phrase_splitted[i])
    return " ".join(new_text)
            
def clean_query(food, place, extras):
    try:
        stopwords_file = open("stopwords.txt", "r")
        for stopword in stopwords_file:
            stopword = stopword.replace("\n", "") # sanitize
            food = update_stopword(food, stopword)
            place = update_stopword(place, stopword)
            extras = update_stopword(extras, stopword)

        query = food + " en " + place + " Costa Rica " + extras
        stopwords_file.close()
        return True, query
    except:
        return False, "Couldn't open the file"

def hostname_allowed(link):
    denied_sites_keywords = ["instagram", "five", "mochil", "ihop", "economi" , "miami", "new", "yelp", "tips", "ucr", "deli", "wiki","viaje", "travel","facebook", "twitter", "top", "tripadvisor", "ubereats", "expedia", "tiktok", "find", "search", "free"]   
    for keyword in denied_sites_keywords:
        if keyword in link:
            return False
    return True

def get_results(query_or_error, logger, user):
    start = 1
    items = []
    api_calls_amount = int(os.getenv('API_CALLS_AMOUNT'))
    #print("Buscando :')")
    while True:
        try:
            for _ in range(api_calls_amount): # Amount of API calls, meaning 10 results per call.
                url = get_url(query_or_error, start)
                data = get_request(url, None)
                items += data["items"]
                start += 10
            # If made it here, there are results
            break
        except Exception as e:
            logger.error("Error %s in get api call for user %s", str(e), user.first_name)
            api_calls_amount -= 1
    return items

def filter_results_by_hostname(items):
    results = []
    pages_already_seen = []
    for item in items:
        if item["displayLink"] not in pages_already_seen and hostname_allowed(item["displayLink"]):
            results.append(item)
            pages_already_seen.append(item["displayLink"])
    return results

def update_top(ranking_weights, new_weight, new_result):
    tmp_weight = 0
    tmp_result = None
    changed = False
    for i,tuple in enumerate(ranking_weights):
        weight_in_top = tuple[0]
        result_in_top = tuple[1]
        #print(f"Comparing {weight_in_top} with type {type(weight_in_top)} and {new_weight} with type {type(new_weight)}")
        # Move the values if it was updated
        if changed:
            ranking_weights[i] = (tmp_weight, tmp_result)
            tmp_weight = weight_in_top
            tmp_result = result_in_top

        # Check if needs to update
        elif weight_in_top <= new_weight:
            tmp_weight = weight_in_top
            tmp_result = result_in_top
            ranking_weights[i] = (new_weight, new_result)
            changed = True # Top updated.

def get_ranking(results, query, logger, user):
    ranking = {} # URL : ( total_weight, { word: weight })
    top_more_weights = [(0, None), 
                        (0, None), 
                        (0, None),
                        (0, None),
                        (0, None) ] # as will be top 5. (Weight Count, Result)
    for result in results:
        words = {}
        weight_sum = 0
        try:
            #print("\n\nTESTING", result["link"])
            data = requests.get(result["link"])
            data = str(data.text).lower()
            for word in query.split(" "):
                if word == "" or word == "en" or word == " ": continue # ignore
                #print("Testing word", word)
                counter = data.count(word.lower())
                #print("Counter:", str(counter))
                if counter > 0: # if appears
                    words[word] = counter
                weight_sum += counter # updating total weight
        except:
            continue # will ignore as there will be several matches
        if len(words) > 0:
            ranking[result["link"]] = (weight_sum, words, result)
            #print("Now testing top with ", str(weight_sum), "for", result["link"])
            update_top(top_more_weights, weight_sum, result)
    #print("\n\n\n Ranking:", ranking)
    #print("\n\n\n TOP:", top_more_weights)
    return top_more_weights
    
def get_relevant_results(items, query, logger, user):
    if len(items) > 0:
        results = filter_results_by_hostname(items)
        ranking = get_ranking(results, query, logger, user)
        return ranking
    return None # No results

def main():
    #print("Hola! Soy el bot Coco, me gustaría ayudarte a encontrar un lugar para comer.")
    food = input("¿Qué te gustaria comer? ")
    place = input("En que lugar te gustaría que esté ubicado el restaurante? ")
    extras = input("¿Detalles extras que desees del lugar? ")

    status, query_or_error = clean_query(food.lower(), place.lower(), extras.lower())
    #print(query_or_error)
    if status:
        items = get_results(query_or_error)
        relevant_results = get_relevant_results(items, query_or_error)
    else:
        print(query_or_error)

#main()