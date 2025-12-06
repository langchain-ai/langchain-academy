FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

# Install LangGraph Studio
RUN pip install langgraph-cli[inmem]

# Copy and install requirements (includes jupyterlab, notebook)
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt
