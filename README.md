![LangChain Academy](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66e9eba1020525eea7873f96_LCA-big-green%20(2).svg)

## Introduction

Welcome to LangChain Academy, Introduction to LangGraph! 
This is a growing set of modules focused on foundational concepts within the LangChain ecosystem. 
Module 0 is basic setup and Modules 1 - 5 focus on building in LangGraph, progressively adding more advanced themes.  Module 6 addresses deploying your agents. 
In each module folder, you'll see a set of notebooks. A link to the LangChain Academy lesson is at the top of each notebook to guide you through the topic. Each module also has a `studio` subdirectory, with a set of relevant graphs that we will explore using the LangGraph API and Studio.

## Setup

### Python version

Make sure you're using Python version 3.11, 3.12, or 3.13.
```
python3 --version
```

### Clone repo
```
git clone https://github.com/langchain-ai/langchain-academy.git
$ cd langchain-academy
```
Or, if you prefer, you can download a zip file [here](https://github.com/langchain-ai/langchain-academy/archive/refs/heads/main.zip).

### Create an environment and install dependencies
#### Mac/Linux/WSL
```
$ python3 -m venv lc-academy-env
$ source lc-academy-env/bin/activate
$ pip install -r requirements.txt
```
#### Windows Powershell
```
PS> python3 -m venv lc-academy-env
PS> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
PS> .\lc-academy-env\Scripts\Activate.ps1
PS> pip install -r requirements.txt
```

### Running notebooks
If you don't have Jupyter set up, follow the installation instructions [here](https://jupyter.org/install).
```
$ jupyter notebook
```

### Setting up env variables
Briefly going over how to set up environment variables. 
#### Mac/Linux/WSL
```
$ export API_ENV_VAR="your-api-key-here"
```
#### Windows Powershell
```
PS> $env:API_ENV_VAR = "your-api-key-here"
```

### Set OpenAI API key
* If you don't have an OpenAI API key, you can sign up [here](https://openai.com/index/openai-api/).
*  Set `OPENAI_API_KEY` in your environment 

### Optional: use LangSmith LLM Gateway for chat models

Direct OpenAI access remains the default. If your organization uses
[LangSmith LLM Gateway](https://docs.langchain.com/langsmith/llm-gateway-direct-model-access),
you can route the course's `ChatOpenAI` calls through it instead. Install the
requirements above, which require `langchain-openai>=1.4.1` and
`langchain-core>=1.5.3`, and configure an OpenAI provider secret and model access
in your LangSmith workspace.

Before starting Jupyter, set these variables in the terminal that launches it:

```bash
export LANGSMITH_GATEWAY="true"
export LANGSMITH_API_KEY="lsv2_..."
```

For PowerShell:

```powershell
$env:LANGSMITH_GATEWAY = "true"
$env:LANGSMITH_API_KEY = "lsv2_..."
```

Replace the placeholder with your real LangSmith API key. Optionally set
`LANGSMITH_GATEWAY_API_KEY` to a separate gateway key; otherwise chat calls use
`LANGSMITH_API_KEY`. The notebook setup cells prompt for the selected credential,
not an OpenAI key in gateway mode. You do not need to copy a LangSmith key into
`OPENAI_API_KEY`. Keep a real provider key for any separate direct-provider use.

`LANGSMITH_GATEWAY` accepts `true`, `1`, or `yes`, or a regional gateway root URL
such as `https://eu.gateway.smith.langchain.com`. The integration adds `/openai/v1`.
Unset it or use `false`, `0`, `no`, or an empty string to restore direct access.
Remove `OPENAI_API_BASE` and `OPENAI_BASE_URL` overrides first to avoid conflicting
endpoint settings. `OPENAI_API_BASE` takes precedence over the flag.
Restart the kernel and recreate model instances after changing routing. A root
`.env` is not loaded automatically by these notebooks; use the launching shell or
set the variables in a notebook cell before constructing the model.

For local Studio, configure the optional gateway entries in each module's
`studio/.env` instead of supplying an OpenAI key. Module 4 uses the root
requirements; the other Studio and deployment requirements include the same
integration minimum. The copy commands below are a direct-provider example and
do not populate gateway settings. Remote deployments in Module 6 need their own
runtime environment settings; exporting a local flag does not configure the server.

This setup affects chat model calls, not Tavily search, embeddings, remote API
access, or other services. Keep their credentials where required. LangSmith
tracing is independent of gateway routing: disabling tracing does not disable
Gateway, and `LANGSMITH_ENDPOINT` selects the LangSmith API, not the gateway URL.

### Sign up and Set LangSmith API
* Sign up for LangSmith [here](https://docs.langchain.com/langsmith/create-account-api-key#create-an-account-and-api-key), find out more about LangSmith and how to use it within your workflow [here](https://www.langchain.com/langsmith). 
*  Set `LANGSMITH_API_KEY`, `LANGSMITH_TRACING_V2="true"` `LANGSMITH_PROJECT="langchain-academy"`in your environment 
*  If you are on the EU instance also set `LANGSMITH_ENDPOINT`="https://eu.api.smith.langchain.com" as well.

### Set up Tavily API for web search

* Tavily Search API is a search engine optimized for LLMs and RAG, aimed at efficient, 
quick, and persistent search results. 
* You can sign up for an API key [here](https://tavily.com/). 
It's easy to sign up and offers a very generous free tier. Some lessons (in Module 4) will use Tavily. 

* Set `TAVILY_API_KEY` in your environment.

### Set up Studio

* Studio is a custom IDE for viewing and testing agents.
* Studio can be run locally and opened in your browser on Mac, Windows, and Linux.
* See documentation [here](https://docs.langchain.com/langsmith/studio#local-development-server) on the local Studio development server. 
* Graphs for LangGraph Studio are in the `module-x/studio/` folders for module 1-5.
* To start the local development server, make sure your virtual environment is active and run the following command in your terminal in the `/studio` directory in each module:

```
langgraph dev
```

You should see the following output:
```
- 🚀 API: http://127.0.0.1:2024
- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 API Docs: http://127.0.0.1:2024/docs
```

Open your browser and navigate to the Studio UI: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`.

* To use Studio, you will need to create a .env file with the relevant API keys
* Run this from the command line to create these files for module 1 to 5, as an example:
```
for i in {1..5}; do
  cp module-$i/studio/.env.example module-$i/studio/.env
  echo "OPENAI_API_KEY=\"$OPENAI_API_KEY\"" > module-$i/studio/.env
done
echo "TAVILY_API_KEY=\"$TAVILY_API_KEY\"" >> module-4/studio/.env
```

### Troubleshooting: `langgraph dev` and `print_text` / `langchain_core.utils`

If `langgraph dev` suddenly fails everywhere (any `studio` folder) with an error like:

`ImportError: cannot import name 'print_text' from 'langchain_core.utils'`

the `langchain-core` install in our venv may be corrupted. On macOS this sometimes happens when files end up in duplicate folders (for example `utils 2` instead of `utils`) under `site-packages/langchain_core/`, so Python loads an incomplete package.

With `lc-academy-env` activated, force a clean reinstall:

```
pip install --force-reinstall --no-cache-dir langchain-core
```

To match whatever version we had pinned or resolved before, we can check `pip show langchain-core` and reinstall that version explicitly, e.g. `pip install --force-reinstall --no-cache-dir "langchain-core==1.2.25"`.

If stray `* 2` directories remain under `lc-academy-env/lib/python3.*/site-packages/langchain_core/`, we remove them after the reinstall—or recreate the venv and run `pip install -r requirements.txt` again.
