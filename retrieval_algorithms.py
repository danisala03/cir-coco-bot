"""
@author Daniel Salazar Mora
Algorithms to retrieve information by cleaning a query and then, using the terms weight algorithm,
provide to the user relevant information. This information is related to restaurants that may be
a good fit for the user.
"""
import requests
import os
from threading import Thread

"""
Will make the GET requests with the Google API
"""
def get_request(url, params):
    try:
        r = requests.get(url = url, params = params)
        return r.json()
    except Exception as e:
        print(e)

""" 
Will return the Google API Key thats its set in the environment.
"""
def get_key():
    return "key="+str(os.getenv('API_KEY'))

""" 
Returns the Google Search Engine identifier. Its delimited to only search
in spanish and inside Costa Rica.
"""
def get_cx():
    return "cx=416041b5afb9e4692"

""" 
Returns the query with the requested format.
"""
def get_query(query):
    return "q="+query

""" 
Returns the url to make the get request and get the results.
"""
def get_url(query, start):
    return f"https://www.googleapis.com/customsearch/v1?{get_key()}&{get_cx()}&{get_query(query)}&num=10&start={start}"

""" 
Removes the stopwords such as innecesary or repeated words in the query. Will return the phrase
given without the stopwords in order to create the query afterwards.
"""
def remove_stopwords(phrase, stopword):
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
        
""" 
Cleans the query by removing stopwords and returns the new query with only relevant keywords.
"""
def clean_query(food, place, extras):
    try:
        stopwords_file = open("stopwords.txt", "r")
        for stopword in stopwords_file:
            stopword = stopword.replace("\n", "") # sanitize
            food = remove_stopwords(food, stopword)
            place = remove_stopwords(place, stopword)
            extras = remove_stopwords(extras, stopword)

        query = food + " en " + place + " Costa Rica " + extras
        stopwords_file.close()
        return True, query
    except:
        return False, "Couldn't open the file"

""" 
Check that the results wont be repeated and that they are considered relevant. Returns if is valid.
"""
def hostname_allowed(link):
    # These sites are removed as they provide tops or information not directly relevant.
    denied_sites_keywords = ["instagram","moovitapp","five","mochil","ihop","economi","miami",
            "new","yelp","tips","ucr","deli","wiki","viaje","travel","facebook","twitter","free",
            "top","expedia","tiktok","find","search","foursquare", "baix", "trip", "pdf", "sale"]
    for keyword in denied_sites_keywords:
        if keyword in link:
            return False
    return True

""" 
Will get the results by making the get request to the api. Will do it api_calls_amount of times.
If no results are received, then will return None as an error. Else, will return the array of data.
The param user is the reference of the Telegram user.
"""
def get_results(query, logger, user):
    start = 1
    items = []
    api_calls_amount = int(os.getenv('API_CALLS_AMOUNT'))
    for _ in range(api_calls_amount): # Amount of API calls
        try:
            url = get_url(query, start)
            data = get_request(url, None)
            start += 10 # moves to next page of results
            items += data["items"]
        except Exception as e:
            # May happen if there are not many results or qouta exceeded
            logger.warning("Error %s in get api call for user %s", str(e), user.first_name) 
    return items if len(items) > 0 else None

""" 
Will receive the ranking weights and its an array of 5 tuples (weight, result object).
Asks if the new weight should be inside the top and if thats the case, will add it to the ranking
and move to the end all the rest of results. The last result will disappear as it will no longer 
be top 5.
"""
def update_top(ranking_weights, new_weight, new_result):
    tmp_weight = 0
    tmp_result = None
    changed = False
    for i,tuple in enumerate(ranking_weights):
        weight_in_top = tuple[0]
        result_in_top = tuple[1]
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
            changed = True # Top updated. Following values will reaccommodate.

""" 
Initialize a top 5 with empty tuples (weight, result object) and the complete ranking {}.
Will iterate per every result received and make a GET request to the specific link related to it.

Then, will calculate the terms weight algorithm with the body response of the request and save the results
in a dictionary per result. So, every result has a dictionary (named words) that goes {keyword: weight}. 
Every result will be saved in the ranking dictionary with the URL as key and the value is a tuple of the total
weight and the word dictionary mentioned earlier.

At the end of the process of every result, the program will check if the result should be in the top 5 relevant
results and if thats the case will add it to top_more_weights. Thats a list of tuples (weight, result object) where
the first value is the top 1 relevant result.
"""
def get_ranking(top_more_weights, results, query):
    pages_already_seen = [] # avoids repetition
    ranking = {} # { result url : ( total_weight, { word: weight }) }
    for result in results:
        words = {}
        weight_sum = 0
        try:
            if result["displayLink"] in pages_already_seen or not hostname_allowed(result["displayLink"]):
                continue # ignore as it is repeated or not relevant result
            data = requests.get(result["link"], timeout=3) # GET request
            data = str(data.text).lower() # body response
            for word in query.split(" "):
                if word == "" or word == "en" or word == " ": continue # ignore stopwords
                counter = data.count(word.lower()) # calculate weight of every word in the body
                if counter > 0:
                    words[word] = counter
                weight_sum += counter # updating total weight
            pages_already_seen.append(result["displayLink"]) 
        except:
            continue # There was en error with the result. Will ignore it.

        if len(words) > 0: # If there were results
            ranking[result["link"]] = (weight_sum, words, result)
            # Check if result is in the top 5 of relevant results
            update_top(top_more_weights, weight_sum, result)
    return top_more_weights

""" 
Will split list of results to allow parallelism.
"""
def split_list(a_list):
    half = len(a_list)//2
    return a_list[:half], a_list[half:]

""" 
Will check if results were received from the API GET general request and if thats the case
starts with filtering hostnames and calculating the weights. Returns the ranking as a list og
tuples (weight, result object) or None if an error occurred.
"""
def get_relevant_results(items, query, logger, user):
    if len(items) > 0:
        try:
            logger.info("Starting to get ranking for user %s", user.first_name)
            items1, items2 = split_list(items)
            ranking1 = [(0, None), 
                    (0, None), 
                    (0, None),
                    (0, None),
                    (0, None) ] # as will be top 5. (Weight Count, Result)
            ranking2 = ranking1[:] # Copy
        
            # Init threads
            t1 = Thread(target=get_ranking, args=(ranking1, items1, query,))
            t2 = Thread(target=get_ranking, args=(ranking2, items2, query,))
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            # Compare both new rankings
            for i in range(len(ranking2)): 
                # This way, ranking2 will be the total ranking
                update_top(ranking2, ranking1[i][0], ranking1[i][1])
            return ranking2
        except Exception as e:
            logger.error("Error %s in get relevant results async for user %s", str(e), user.first_name)
    return None # No results or invalid

# Only created for testing purposes before telegram connection
def main():
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

if __name__ == "__main__":
    main()