FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

# Install JupyterLab and LangGraph Studio
RUN pip install jupyterlab langgraph-cli[inmem]

# Install requirements
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt
