import operator
import os
import time
import requests
from typing import List, Optional, Union
from typing import Annotated
from typing_extensions import TypedDict

from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.vectorstores import SKLearnVectorStore

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage, get_buffer_string
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import chain as as_runnable

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.constants import Send
from langgraph.channels import Topic
from langgraph.checkpoint.sqlite import SqliteSaver


### --- User Inputs --- ###

# 1) Global varianbles

# Set a path for saving the state of your graph
save_db_path = "state_db/assistant.db"

# Webhook URL for Slack
slack_bot_url = os.getenv('LANCE_BOT_SLACK_URL')

# Max turns for interviews 
max_num_turns = 3

# 2) Commentary to create analysts 

# Mark Zuckerberg's blog post as an alternative source
url = "https://about.fb.com/news/2024/07/open-source-ai-is-the-path-forward/"
ANALYST_TOPIC_GENERATION_CONTEXT = WebBaseLoader(url).load()

# 3) Content for expert 

# Full llama3.1 paper
loader = PyPDFLoader("docs/llama3_1.pdf")
pages = loader.load_and_split()

# Embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# Full paper, except for references 
all_pages_except_references=pages[:100]

# Index
vectorstore = SKLearnVectorStore.from_documents(all_pages_except_references,embedding=embeddings)

# Build retriever
retriever = vectorstore.as_retriever(k=10)

# Load a technical blog post from the web 
url = "https://ai.meta.com/blog/meta-llama-3-1/"
EXPERT_CONTEXT_BLOG = WebBaseLoader(url).load()

# 4) Web search

tavily_search = TavilySearchResults(max_results=4)

### --- State --- ###

class Analyst(BaseModel):
    affiliation: str = Field(
        description="Primary affiliation of the analyst.",
    )
    name: str = Field(
        description="Name of the analyst.", pattern=r"^[a-zA-Z0-9_-]{1,64}$"
    )
    role: str = Field(
        description="Role of the analyst in the context of the topic.",
    )
    description: str = Field(
        description="Description of the analyst focus, concerns, and motives.",
    )

    @property
    def persona(self) -> str:
        return f"Name: {self.name}\nRole: {self.role}\nAffiliation: {self.affiliation}\nDescription: {self.description}\n"

class Perspectives(BaseModel):
    analysts: List[Analyst] = Field(
        description="Comprehensive list of analysts with their roles and affiliations.",
    )

class InterviewState(TypedDict):
    topic: str
    messages: Annotated[List[AnyMessage], add_messages]
    analyst: Analyst
    editor_feedback: str
    context: Annotated[list, Topic(typ=list, accumulate=True, unique=True)]
    interviews: list
    reports: list 

# TODO: Remove topic and max_analysts this when the input type is supported in Studio
class ResearchGraphState(TypedDict):
    analysts: List[Analyst]
    interviews: Annotated[list, operator.add] 
    reports: Annotated[list, operator.add] 
    final_report: str
    analyst_feedback: str 
    editor_feedback: str 
    topic: str
    max_analysts: int

# TODO: Use this when the input type is supported in Studio
class ResearchGraphStateInput(TypedDict):
    topic: str
    max_analysts: int

# Data model for Slack
class TextObject(BaseModel):
    type: str = Field(
        ..., 
        description="The type of text object, should be 'mrkdwn' or 'plain_text'.", 
        example="mrkdwn"
    )
    text: str = Field(
        ..., 
        description="The text content.",
        example="Hello, Assistant to the Regional Manager Dwight! ..."
    )

class SectionBlock(BaseModel):
    type: str = Field(
        "section", 
        description="The type of block, should be 'section'.", 
        const=True
    )
    text: TextObject = Field(
        ..., 
        description="The text object containing the block's text."
    )

class DividerBlock(BaseModel):
    type: str = Field(
        "divider", 
        description="The type of block, should be 'divider'.", 
        const=True
    )

class SlackBlock(BaseModel):
    blocks: List[Union[SectionBlock, DividerBlock]] = Field(
        ..., 
        description="A list of Slack block elements."
    )

### --- LLM --- ###

llm = ChatOpenAI(model="gpt-4o", temperature=0) 
report_writer_llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0) 

### --- Analysts --- ###

gen_perspectives_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            
            """
            You are tasked with creating a set of AI analyst personas. 
            
            Follow these instructions carefully:

            1. First, review the research topic:
            
            {topic}
            
            2. Examine any documents that have been optionally provided to guide creation of the analysts:
            
            {documents}

            3. Examine any editorial feedback that has been optionally provided to guide creation of the analysts: 
            
            {analyst_feedback}  
            
            4. Determine the most interesting themes based upon documents and / or feedback above.
                        
            5. Pick the top {max_analysts} themes.

            6. Assign one analyst to each theme.""",
            
        ),
    ]
)

def generate_analysts(state: ResearchGraphState):
    """ Node to generate analysts """

    # Get topic and max analysts from state
    topic = state["topic"]
    max_analysts = state["max_analysts"]
    analyst_feedback = state.get("analyst_feedback", "")

    # Generate analysts
    gen_perspectives_chain = gen_perspectives_prompt | llm.with_structured_output(Perspectives)
    perspectives = gen_perspectives_chain.invoke({"documents": ANALYST_TOPIC_GENERATION_CONTEXT, 
                                                  "topic": topic, 
                                                  "analyst_feedback": analyst_feedback, 
                                                  "max_analysts": max_analysts})
    
    # Write the list of analysis to state
    return {"analysts": perspectives.analysts}

### --- Question Asking --- ###

gen_qn_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            
            """You are an analyst tasked with interviewing an expert to learn about a specific topic. 

            Your goal is boil down to interesting and specific insights related to your topic.

            1. Interesting: Insights that people will find surprising or non-obvious.
            
            2. Specific: Insights that avoid generalities and include specific examples from the expert.
    
            Here is your topic of focus and set of goals: {persona}
            
            Begin by introducing yourself using a name that fits your persona, and then ask your question.

            Continue to ask questions to drill down and refine your understanding of the topic.
            
            When you are satisfied with your understanding, complete the interview with: "Thank you so much for your help!"

            Remember to stay in character throughout your response, reflecting the persona and goals provided to you.""",
        
        ),
        MessagesPlaceholder(variable_name="messages", optional=True),
    ]
)

def get_description(analyst: Union[Analyst, dict]) -> str:
    """ TODO: This is a hack until Studio supports Pydantic models with state edits"""

    # State is a Pydantic model, Analyst, as defined in graph 
    if isinstance(analyst, Analyst):
        return analyst.persona
    # If you edit state in Studio, it will be a dict
    elif isinstance(analyst, dict):
        return analyst.get("description", "")
    else:
        raise TypeError("Invalid type for analyst. Expected Analyst or dict.")

def generate_question(state: InterviewState):
    """ Node to generate a question """

    # Get state
    analyst = state["analyst"]
    messages = state["messages"]

    # Generate question 
    gen_question_chain = gen_qn_prompt.partial(persona=get_description(analyst)) | llm   
    result = gen_question_chain.invoke({"messages": messages})
    
    # Write messages to state
    return {"messages": [result]}

### --- Expert --- ###

gen_search_query = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            
            """You will be given a conversation between an analyst and an expert. 

            Your goal is to generate a well-structured query for use in retrieval and / or web-search related to the conversation.
            
            First, analyze the full conversation.

            Pay particular attention to the final question posed by the analyst.

            Convert this final question into a well-structured query.""",
            
        ),
        
            MessagesPlaceholder(variable_name="messages", optional=True),
        ]
)

# Schema 
class SearchQuery(BaseModel):
    search_query: str = Field(None, description="The search query to use.")

# Query re-writing
query_gen_chain = gen_search_query | llm.with_structured_output(SearchQuery)

def retrieve_docs(state: InterviewState):
    """ Retrieve docs from vectorstore """

    # Get messages
    messages = state['messages']

    # Search query
    search_query = query_gen_chain.invoke({'messages': messages})

    # Retrieve
    docs = retriever.invoke(search_query.search_query)

    # Format
    formatted_retrieved_docs = "\n\n---\n\n".join(
        [
            f'<Document source="{doc.metadata["source"]}" page="{doc.metadata.get("page", "")}"/>\n{doc.page_content}\n</Document>'
            for doc in docs
        ]
    )

    return {"context": [formatted_retrieved_docs]} 

def search_web(state: InterviewState):
    """ Retrieve docs from web search """

    # Get messages
    messages = state['messages']

    # Search query
    search_query = query_gen_chain.invoke({'messages': messages})

    # Search
    search_docs = tavily_search.invoke(search_query.search_query)

     # Format
    formatted_search_docs = "\n\n---\n\n".join(
        [
            f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
            for doc in search_docs
        ]
    )

    return {"context": [formatted_search_docs]} 

gen_expert_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            
            """You are an expert being interviewed by an analyst who focused on learning this topic: {topic}. 
            
            You goal is to answer a question posed by the interviewer.

            To answer question, use this context:
            
            {context}

            When answering questions, follow these guidelines:
            
            1. Use only the information provided in the context. 
            
            2. Do not introduce external information or make assumptions beyond what is explicitly stated in the context.

            3. The context contain sources at the topic of each individual document.

            4. Include these sources your answer next to any relevant statements. For example, for source # 1 use [1]. 

            5. List your sources in order at the bottom of your answer. [1] Source 1, [2] Source 2, etc
            
            6. If the source is: <Document source="assistant/docs/llama3_1.pdf" page="7"/>' then just list: 
            
            [1] assistant/docs/llama3_1.pdf, page 7 
            
            And skip the addition of the brackets as well as the Document source preanble in your citation.""",
            
        ),
        
            MessagesPlaceholder(variable_name="messages", optional=True),
        ]
)

def generate_answer(state: InterviewState):
    """ Node to answer a question """

    # Get state
    topic = state["topic"]
    messages = state["messages"]
    
    # Get context from the index of the paper
    retrieved_docs = retriever.invoke(messages[-1].content)

    # Add the technical blog post
    retrieved_docs.extend(EXPERT_CONTEXT_BLOG)

    # Format
    relevant_docs = "\n *** \n".join([f"Document # {i}\n{p.page_content}" for i, p in enumerate(retrieved_docs, start=1)])
    
    # Answer question
    answer_chain = gen_expert_prompt | llm
    answer = answer_chain.invoke({'messages': messages,
                                  'topic': topic,
                                  'context': relevant_docs})  
    
    # Name the message as coming from the expert
    # We use this later to count the number of times the expert has answered
    answer.name = "expert"
    
    # Append it to state
    return {"messages": [answer]}

### --- Report Generation --- ###

report_gen_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            
            """You are an expert technical analyst, writer, and editor. 
            
            Your task is to create a short, easily digestible report based on a set of source documents.

            1. Analyze the content of the source documents: 
            - The name of each source document is at the start of the document, with the <Document tag.
            
            2. Create a report structure using markdown formatting:
               - Use ## for the report title
               - Use ### for section headers
            
            3. Write the report following this structure:
               a. Title (## header)
               b. Summary (### header)
               c. Sources (### header)

            4. Make your title engaging based upon the focus area of the analyst: 
            {description}

            4. For the summary section:
            - Set up summary with general background / context related to description
            - Emphasize what is novel, interesting, or surprising about insights gathered from the interview
            - Create a numbered list of source documents, as you use them
            - Do not mention the names of interviewers or experts
            - Aim for approximately 400 words maximum
            - Use numbered sources in your report (e.g., [1], [2]) based on information from source documents
            
            5. Incorporate editor feedback seamlessly into your report, if provided.
            
            6. In the Sources section:
               - Include all sources used in your report
               - Provide full links to relevant websites or specific document paths
               - Separate each source by a newline. Use two spaces at the end of each line to create a newline in Markdown.
               - It will look like:

                ### Sources
                [1] Link or Document name
                [2] Link or Document name

            7. Be sure to combine sources. For example this is not correct:

            [3] https://ai.meta.com/blog/meta-llama-3-1/
            [4] https://ai.meta.com/blog/meta-llama-3-1/

            There should be no redundant source. It should simply be:

            [3] https://ai.meta.com/blog/meta-llama-3-1/
            
            8. Final review:
               - Ensure the report follows the required structure
               - Include no preamble before the title of the report
               - Check that all guidelines have been followed""",
        
        ),
        ("human", """Here are the materials you'll be working with:

                        Overall focus on the analyst:
                        {description}
                        
                        Source documents retrieved from an interview w/ an expert:
                        {context}

                        Here is any editor feedback that should be incorporated into the report:
                        {editor_feedback}"""),
    ]
)

def generate_report(state: InterviewState):
    """ Node to generate report based upon interview """

    # State 
    topic = state["topic"]
    context = state["context"]
    analyst = state["analyst"]
    editor_feedback = state.get("editor_feedback", [])

    # Generate report
    report_gen_chain = report_gen_prompt | report_writer_llm | StrOutputParser()
    report = report_gen_chain.invoke({"description": analyst.description, 
                                      "context": context, 
                                      "topic": topic,
                                      "editor_feedback": editor_feedback})
    
    return {"reports": [report]}

### --- Interview -- ###

def save_interview(state: InterviewState):
    
    """ Save interviews """

    # Get messages
    messages = state["messages"]
    
    # Convert interview to a string
    interview = get_buffer_string(messages)
    
    # Save to interviews key
    return {"interviews": [interview]}

def route_messages(state: InterviewState, 
                   name: str = "expert"):

    """ Route between question and answer """
    
    # Get messages
    messages = state["messages"]

    # Check the number of expert answers 
    num_responses = len(
        [m for m in messages if isinstance(m, AIMessage) and m.name == name]
    )

    # End if expert has answered more than the max turns
    if num_responses >= max_num_turns:
        return 'save_interview'

    # This router is run after each question - answer pair 
    # Get the last question asked to check if it signals the end of discussion
    last_question = messages[-2]
    
    if "Thank you so much for your help" in last_question.content:
        return 'save_interview'
    return "ask_question"

# Add nodes and edges for the interview
interview_builder = StateGraph(InterviewState)
interview_builder.add_node("ask_question", generate_question)
interview_builder.add_node("retrieve_docs", retrieve_docs)
interview_builder.add_node("search_web", search_web)
interview_builder.add_node("answer_question", generate_answer)
interview_builder.add_node("save_interview", save_interview)
interview_builder.add_node("generate_report", generate_report)

# Interview Flow
interview_builder.add_edge(START, "ask_question")
interview_builder.add_edge("ask_question", "retrieve_docs")
interview_builder.add_edge("ask_question", "search_web")
interview_builder.add_edge("retrieve_docs", "answer_question")
interview_builder.add_edge("search_web", "answer_question")
interview_builder.add_conditional_edges("answer_question", route_messages,['ask_question','save_interview'])
interview_builder.add_edge("save_interview", "generate_report")
interview_builder.add_edge("generate_report", END)

### --- Main Graph --- ###

def initiate_all_interviews(state: ResearchGraphState):
    """ This is the "map" step where we run each interview sub-graph using Send API """    
    
    topic = state["topic"]
    return [Send("conduct_interview", {"analyst": analyst,
                                       "messages": [HumanMessage(
                                           content=f"So you said you were writing an article on {topic}?"
                                       )
                                                   ]}) for analyst in state["analysts"]]
    
def finalize_report(state: ResearchGraphState):
    """ The is the "reduce" step where we gather reports from each interview, combine them, and add an introduction """
    
    # Full set of interviews
    sections = state["reports"]

    # Combine them
    formatted_str_sections = "\n\n".join([f"{section}" for i, section in enumerate(sections, start=1)])

    # Write the intro
    final_report_gen_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                
                """You are an expert analyst, writer, and editor. You will be given a full report.
    
                Write a crisp and compelling introduction for the report.

                Include no pre-amble for the introduction.
    
                Use markdown formatting. Use # header for the start along with a title for the full report.""",
            
            ),
            ("human", """Here are the interviews conducted with experts on this topic:
                            <sections>
                            {sections}
                            </sections>"""),
        ]
    )

    # Generate intro
    final_report_gen_chain = final_report_gen_prompt | report_writer_llm | StrOutputParser()
    report_intro = final_report_gen_chain.invoke({"sections": formatted_str_sections})

    # Save full / final report
    return {"final_report": report_intro + "\n\n" + formatted_str_sections}

def write_report(state: ResearchGraphState):
    """ Write the report to external service (e.g., Slack) """
    
    # Write to slack
    slack_fmt_promopt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                
                """Your goal is to first analyze a short report, which is in markdown.
    
                Then, re-format it in Slack blocks so that it can be written to the Slack API.
    
                The section of the report will be: title, summary, sources.
    
                Make each section header bold. For example, *Summary* or *Sources*.
    
                Include divider blocks between each section of the report.""",
            
            ),
            ("human", """Here is the report to re-format: {report}"""),
        ]
    )

    # Full set of interview reports
    reports = state["reports"]

    # Write each section of the report indvidually 
    for section_to_write in reports:
    
        # Format the markdown as Slack blocks
        slack_fmt = slack_fmt_promopt | llm.with_structured_output(SlackBlock)
        slack_fmt_report = slack_fmt.invoke({"report": section_to_write})
        list_of_blocks = [block.dict() for block in slack_fmt_report.blocks]

        # Add a header
        true = True
        list_of_blocks.insert(0, {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":robot_face: Lance Bot has been busy ...",
                "emoji": true
            }
        })

        # Write to your Slack Channel via webhook
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            "blocks": list_of_blocks,
        }
        response = requests.post(slack_bot_url, headers=headers, json=data)

# Build the full graph
# builder = StateGraph(ResearchGraphState, input=ResearchGraphStateInput) # Not supported in Studio yet
builder = StateGraph(ResearchGraphState)
builder.add_node("generate_analysts", generate_analysts)
builder.add_node("conduct_interview", interview_builder.compile())
builder.add_node("write_report", write_report)
builder.add_node("finalize_report", finalize_report)

# Flow 
builder.add_edge(START, "generate_analysts")
builder.add_conditional_edges("generate_analysts", initiate_all_interviews, ["conduct_interview"])
builder.add_edge("conduct_interview", "write_report")
builder.add_edge("conduct_interview", "finalize_report")
builder.add_edge("write_report", END)
builder.add_edge("finalize_report", END)

# Set memory
memory = SqliteSaver.from_conn_string(save_db_path)

# Compile
# Interrupt after generate_analysts to see if we want to modify any of the personas
# Interrupt before write_report to confirm / approve that we want to write the reports to Slack
graph = builder.compile(checkpointer=memory, interrupt_after=["generate_analysts"], interrupt_before=["write_report"],)