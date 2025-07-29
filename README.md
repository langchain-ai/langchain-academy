# ![LangChain Academy](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66e9eba1020525eea7873f96_LCA-big-green%20(2).svg)

## Introduction

Welcome to LangChain Academy!
This is a growing set of modules focused on foundational concepts within the LangChain ecosystem.
Module 0 is basic setup and Modules 1 - 4 focus on LangGraph, progressively adding more advanced themes.
In each module folder, you'll see a set of notebooks. A LangChain Academy accompanies each notebook
to guide you through the topic. Each module also has a `studio` subdirectory, with a set of relevant
graphs that we will explore using the LangGraph API and Studio.

## Setup

### Python version

To get the most out of this course, please ensure you're using Python 3.11 or later.
This version is required for optimal compatibility with LangGraph. If you're on an older version,
upgrading will ensure everything runs smoothly.

```bash
python3 --version
```

### Clone repo

```bash
git clone https://github.com/langchain-ai/langchain-academy.git
$ cd langchain-academy
```

### Create an environment and install dependencies

#### Using Mac/Linux/WSL

```bash
python3 -m venv lc-academy-env
source lc-academy-env/bin/activate
pip install -r requirements.txt
```

#### Using Windows Powershell

```powershell
PS> python3 -m venv lc-academy-env
PS> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
PS> lc-academy-env\scripts\activate
PS> pip install -r requirements.txt
```

### Running notebooks

If you don't have Jupyter set up, follow [Jupyter installation instructions](https://jupyter.org/install).

```bash
jupyter notebook
```

### Setting up env variables

Briefly going over how to set up environment variables. You can also
use a `.env` file with `python-dotenv` library.

#### On Mac/Linux/WSL

```bash
export API_ENV_VAR="your-api-key-here"
```

#### Windows Powershell environment variables

```powershell
PS> $env:API_ENV_VAR = "your-api-key-here"
```

### Set OpenAI API key

* If you don't have an OpenAI API key, you can [sign up for OpenAI API](https://openai.com/index/openai-api/).
* Set `OPENAI_API_KEY` in your environment

### Sign up and Set LangSmith API

* [Sign up for LangSmith](https://smith.langchain.com/), find out more about LangSmith
* and how to use it within your workflow [on the LangSmith website](https://www.langchain.com/langsmith), and relevant library [docs](https://docs.smith.langchain.com/)!
* Set `LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2=true` in your environment

### Set up Tavily API for web search

* Tavily Search API is a search engine optimized for LLMs and RAG, aimed at efficient,
quick, and persistent search results.
* You can [sign up for a Tavily API key](https://tavily.com/).
It's easy to sign up and offers a very generous free tier. Some lessons (in Module 4) will use Tavily.

* Set `TAVILY_API_KEY` in your environment.

### Set up LangGraph Studio

* LangGraph Studio is a custom IDE for viewing and testing agents.
* Studio can be run locally and opened in your browser on Mac, Windows, and Linux.
* See documentation [on the local Studio development server](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/#local-development-server) and [how to run the development server](https://langchain-ai.github.io/langgraph/how-tos/local-studio/#run-the-development-server).
* Graphs for LangGraph Studio are in the `module-x/studio/` folders.
* To start the local development server, run the following command in your terminal in the `/studio` directory each module:

```bash
langgraph dev
```

You should see the following output:

```text
- 🚀 API: http://127.0.0.1:2024
- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 API Docs: http://127.0.0.1:2024/docs
```

Open your browser and navigate to the Studio UI: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`.

* To use Studio, you will need to create a .env file with the relevant API keys
* Run this from the command line to create these files for module 1 to 5, as an example:

```bash
for i in {1..5}; do
  cp module-$i/studio/.env.example module-$i/studio/.env
  echo "OPENAI_API_KEY=\"$OPENAI_API_KEY\"" > module-$i/studio/.env
done
echo "TAVILY_API_KEY=\"$TAVILY_API_KEY\"" >> module-4/studio/.env
```
