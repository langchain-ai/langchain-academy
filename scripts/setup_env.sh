#!/bin/bash

# Set up .env files in studio directories for modules 1-5
# Uses environment variables: OPENAI_API_KEY, LANGSMITH_API_KEY, LANGSMITH_TRACING_V2, LANGSMITH_PROJECT, TAVILY_API_KEY

for i in {1..5}; do
    mkdir -p "module-$i/studio"
    
    cat > "module-$i/studio/.env" << EOF
OPENAI_API_KEY=$OPENAI_API_KEY
LANGSMITH_API_KEY=$LANGSMITH_API_KEY
LANGSMITH_TRACING_V2=$LANGSMITH_TRACING_V2
LANGSMITH_PROJECT=$LANGSMITH_PROJECT
EOF

    if [ $i -eq 4 ]; then
        echo "TAVILY_API_KEY=$TAVILY_API_KEY" >> "module-$i/studio/.env"
    fi
done
