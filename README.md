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

### Create an enviorment and install dependencies 
```
$ python3 -m venv lc-academy-env
$ source lc-academy-env/bin/activate
$ pip install -r assistant/requirements.txt
```

### Create a .env file 
* Create a .env file for the relevant environment variables
```
cp assistant/.env.example assistant/.env
```

### Set OpenAI API key

* If you don't have an OpenAI API key, you can sign up [here](https://openai.com/index/openai-api/).
* Append the `OPENAI_API_KEY` to your shell configuration (e.g., `~/.zshrc`)
```
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```
* Save this to the .env file 
```
echo "OPENAI_API_KEY=\"$OPENAI_API_KEY\"" > assistant/.env
```

### Sign up for LangSmith

* Sign up [here](https://docs.smith.langchain.com/) 
* Append the  to your shell configuration (e.g., `~/.zshrc`)
```
echo 'export LANGCHAIN_API_KEY="your-api-key-here"' >> ~/.zshrc
echo 'export LANGCHAIN_TRACING_V2=true' >> ~/.zshrc
source ~/.zshrc
```

### Set up LangGraph Studio (only macOS support)

* Download the latest `.dmg` file [here](https://github.com/langchain-ai/langgraph-studio?tab=readme-ov-file#download)
* Install Docker desktop for Mac [here](https://docs.docker.com/engine/install/)

### Tavily for web search

You can sign up for an API key [here](https://tavily.com/).

Some lessons (in Module 4) will use Tavily, but you can use other search tools.

* Save this to the .env file 
```
echo "TAVILY_API_KEY=\"$TAVILY_API_KEY\"" >> assistant/.env
```