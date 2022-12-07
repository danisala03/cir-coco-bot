# Coco Restaurant Finder Bot

Owner: Daniel Salazar Mora.

## Description

This project was made to test a simple Conversational Information Retrieval Bot to find restaurants that may be relevant for the user. The algorithm used to calculate the ranking of the results was Weight Terms and the implementation was made by using the Google Search and Place API.

The algorithm used to retrieve and create a ranking for the Restaurants its the Weight Terms Algorithm, taking the term frequency as the weight. A dictionary is used to save the restaurant URL as a key and a tuple of the total weight and another dictionary of weight as a value.

## How to run it

First, install the package needed for the Telegram bot:

```
pip install python-telegram-bot -U --pre 
```

And then, set the following environment variables:

> Windows

```powershell
set API_KEY=<Google Place API Key>
set API_CALLS_AMOUNT=1
set API_KEY_SEARCH=<Custom Search JSON API Key>
set BOT_TOKEN=<Telegram Chatbot Token>
set SEARCHENGINEID=<Search Engine Id>
```

> Linux

```powershell
export API_KEY=<Google Place API Key>
export API_CALLS_AMOUNT=1
export API_KEY_SEARCH=<Custom Search JSON API Key>
export BOT_TOKEN=<Telegram Chatbot Token>
export SEARCHENGINEID=<Search Engine Id>
```

Finally, just run the command: ``` py -3 newbot.py```
