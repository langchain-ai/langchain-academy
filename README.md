# LangChain Academy 

## Introduction

Welcome to LangChain Academy! This course is dedicated to exploring foundational concepts within the LangChain ecosystem, beginning with LangGraph. Throughout the course, we’ll build a strong understanding of LangGraph through a series of progressively detailed modules, each focusing on a specific theme. 

For each module, we’re providing accompanying notebooks, which can be found in the designated folders below, and videos to guide you through each topic. In the `assistants` subdirectory, you’ll discover a collection of graphs that will be utilized with the LangGraph API and Studio throughout the modules.

## Setup

### Clone repo
```
git clone https://github.com/langchain-ai/langchain-academy.git
$ cd langchain-academy
```

### Create an environment and install dependencies  
```
$ python3 -m venv lc-academy-env
$ source lc-academy-env/bin/activate
$ pip install -r requirements.txt
```

### Running notebooks
Notebooks for each module are in the `module-` folders.
```
$ jupyter notebook
```

### Set OpenAI API key
* If you don't have an OpenAI API key, you can sign up [here](https://openai.com/index/openai-api/).
*  Set `OPENAI_API_KEY` in your environment 

### Sign up for LangSmith

* Sign up [here](https://docs.smith.langchain.com/) 
*  Set `LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2=true` in your environment 

### Tavily for web search

Tavily Search API is a search engine optimized for LLMs and RAG, aimed at efficient, quick, and persistent search results. You can sign up for an API key [here](https://tavily.com/). It's easy to sign up and offers a generous free tier. Some lessons (in Module 4) will use Tavily. Set `TAVILY_API_KEY` in your environment.

### Set up LangGraph Studio

* Current Studio only has macOS support
* Download the latest `.dmg` file [here](https://github.com/langchain-ai/langgraph-studio?tab=readme-ov-file#download)
* Install Docker desktop for Mac [here](https://docs.docker.com/engine/install/)
* Add relevant API keys to .env files 
```
$ cp module-1/studio/.env.example module-1/studio/.env
$ echo "OPENAI_API_KEY=\"$OPENAI_API_KEY\"" > module-1/.env

$ cp module-2/studio/.env.example module-2/studio/.env
$ echo "OPENAI_API_KEY=\"$OPENAI_API_KEY\"" > module-2/.env

$ cp module-3/studio/.env.example module-3/studio/.env
$ echo "OPENAI_API_KEY=\"$OPENAI_API_KEY\"" > module-3/.env

$ cp module-4/studio/.env.example module-4/studio/.env
$ echo "OPENAI_API_KEY=\"$OPENAI_API_KEY\"" > module-4/.env
$ echo "TAVILY_API_KEY=\"$TAVILY_API_KEY\"" > module-4/.env
```