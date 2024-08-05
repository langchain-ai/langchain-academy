import operator
import os
import time
import requests
from typing import List, Optional, Union
from typing import Annotated
from typing_extensions import TypedDict

import praw

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
from langgraph.checkpoint.sqlite import SqliteSaver


### --- User Inputs --- ###

# 1) Global varianbles

# Set a path for saving the state of your graph
save_db_path = "state_db/assistant.db"

# Webhook URL for Slack
slack_bot_url = os.getenv('LANCE_BOT_SLACK_URL')

# Max turns for interviews 
max_num_turns = 6

# 2) Commentary to create analysts 

# Reddit creds
reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')

# URL of the Reddit post
url = 'https://www.reddit.com/r/LocalLLaMA/comments/1eabf4l/lets_discuss_llama31_paper_a_lot_of_details_on/'

# Initialize the Reddit instance
reddit = praw.Reddit(client_id=reddit_client_id, client_secret=reddit_client_secret, user_agent='Local Llama Loader')

# Fetch the submission and comments
submission = reddit.submission(url=url)
submission.comments.replace_more(limit=None)
comments = submission.comments.list()

# Concatenate comments into a single string
ANALYST_TOPIC_GENERATION_CONTEXT = "\n *** user commnent *** \n".join([comment.body for comment in comments])

# Mark Zuckerberg's blog post as an alternative source
url = "https://about.fb.com/news/2024/07/open-source-ai-is-the-path-forward/"
ANALYST_TOPIC_GENERATION_CONTEXT_BLOG = WebBaseLoader(url).load()

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
    interviews: list # This key is duplicated between "inner state" ...
    reports: list # This key is duplicated between "inner state" ...

# TODO: Remove topic and max_analysts this when the input type is supported in Studio
class ResearchGraphState(TypedDict):
    analysts: List[Analyst]
    interviews: Annotated[list, operator.add] # ... and "outer state"
    reports: Annotated[list, operator.add] # ... and "outer state"
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
            
            2. Carefully read and analyze the following documents related to the topic:
            
            {documents}
            
            3. Think carefully about the documents.
            
            4. Identify the most interesting themes for further research from the documents. 
            
            5. Assign an AI analyst persona to each of the indentified themes. 
            
            6. Choose the top {max_analysts} themes. The maximum number of personas you should create is:
            
            {max_analysts}
            
            7. If the user has specified any analyst personas they want included, incorporate them into your set of analysts. 
            
            Here is the user's optional input: {analyst_feedback}            
            """,
            
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
    perspectives = gen_perspectives_chain.invoke({"documents": ANALYST_TOPIC_GENERATION_CONTEXT_BLOG, 
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
            
            """You are an experienced analyst tasked with interviewing an expert to learn about a specific topic. 

            Your goal is boil down to non-obvious and specific insights related to your topic:

            1. Non-obvious: Insights that people will find surprising.
            
            2. Specific: Insights that avoid generalities and include specific examples from the exprt.
    
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

gen_expert_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            
            """You are an expert on the topic of {topic}.
            
            You are being interviewed by an analyst who focused on learning about a specific topic. 
            
            Your goal is to share non-obvious and specific insights related to your topic:

            1. Non-obvious: Insights that people will find surprising and therefore interesting.
            
            2. Specific: Insights that avoid generalities and include specific examples from the exprt.

            Here is the context you should use to inform your answers:
            {context}

            When answering questions, follow these guidelines:
            
            1. Use only the information provided in the context. Do not introduce external information or make assumptions beyond what is explicitly stated in the context.
                     
            2. If a question cannot be answered based on the given context, state that you don't have enough information to provide a complete answer.
            
            Remember, your ultimate goal is to help the analyst drill down to specific and non-obvious insights about the topic.""",
            
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

def reflect(state: InterviewState):

    """ Reflect on the interview, assess whether web search is needed """

    # Get messages state
    messages = state['messages']

    # Get query for reflection
    gen_search_query = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                
                """You will be given a conversation between an analyst and an expert. 
                
                Your task is to assess whether the expert's answers fully address the analyst's questions.
                
                And also your task is to determine if additional web search would be beneficial.
    
                Carefully analyze the conversation by following these steps:
                1. Identify the main questions asked by the analyst.
                2. Examine the expert's responses to each question.
                3. Determine if any questions were left unanswered or only partially addressed.
                4. Consider if there are any gaps in information or areas that could benefit from additional research.
    
                Based on your analysis, decide whether the conversation would benefit from an additional web search. 
                
                Output your decision as a single word, either 'yes' or 'no':
                
                If your decision is 'yes', complete the following additional steps:
                1. Reflect on the conversation and identify the key topics or questions that were not fully addressed.
                2. Generate a concise search query that would best capture the information needed to fill in the gaps.
                3. Provide a brief explanation of your reasoning for suggesting a web search.""",
                
            ),
            
                MessagesPlaceholder(variable_name="messages", optional=True),
            ]
    )

    # Schema 
    class SearchQuery(BaseModel):
        search: str = Field(..., description="Indicate whether to perform a search. Allowed values are 'yes' or 'no'.")
        search_query: Optional[str] = Field(None, description="The search query to use if search is 'yes'.")
        reasoning: Optional[str] = Field(None, description="Reasoning for performing additional search to supplement the interview.")

    # Reflect
    query_gen_chain = gen_search_query | llm.with_structured_output(SearchQuery)
    result = query_gen_chain.invoke({'messages': messages})

    # Perform web search
    if result.search.lower() == 'yes':

        # Search tool
        web_search_tool = TavilySearchResults(k=3)
        
        # Get search results
        search_results = web_search_tool.invoke(result.search_query)
        formatted_search_results = "\n\n".join([f"Added web search result # {i}\n{search['content']}" for i, search in enumerate(search_results, start=1)])

        # Append it to state
        return {"messages": [AIMessage(content=formatted_search_results)]}

### --- Report Generation --- ###

report_gen_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            
            """You are tasked with generating a short summary of a technical interview. 
            
            Your summary should focus on two main aspects:
            
            1. The historical context, past ways of thinking about the problem, or prior approaches
            
            2. What is new, novel, and interesting about the approaches discussed in the conversation, especially if they diverge from conventional wisdom

            Please follow these steps to create your summary:

            1. Carefully read and analyze the provided technical interview.

            2. Identify the historical context, past approaches, or conventional wisdom related to the topic discussed. Use you general knowledge and look for mentions of these in the interview:
            - Previous methods or technologies
            - Traditional ways of thinking about the problem
            - Established practices or theories in the field

            3. Determine what is new, novel, or interesting about the approach discussed in the interview. Pay attention to:
            - Innovative ideas or methodologies
            - Unconventional solutions or perspectives
            - Improvements or advancements over existing approaches

            4. Use markdown ## header for the summary title, and create an engaging title for the summary.

            5. Use markdown ### header for the first section of the report and call this "Context".

            6. In the "Context" section, summarize the historical context, past approaches, or conventional wisdom related to the topic discussed.

            7. Use markdown ### header for the second section of the report and call this "Why Is This Interesting?".

            8. In the "Why Is This Interesting?" section, summarize what is new, novel, or interesting about the approach discussed in the interview. 

            9. Do not mention the names of the interviewers or expert in your report.
                           
            10. If editor feedback is provided, incorporate those points seamlessly into your report.

            11. Remember to focus on the most significant points and provide a clear contrast between the historical context and the novel approach discussed in the conversation.
            
            12. Aim for ~300 words maximum.""",
        
        ),
        ("human", """Here are the interviews to summarize:
                        <interviews>
                        {interviews}
                        </interviews>
            
                        Here is any editor feedback that should be incorporated into the report:
                        <editor_feedback>
                        {editor_feedback}
                        </editor_feedback>"""),
    ]
)

def generate_report(state: InterviewState):
    """ Node to generate report based upon interview """

    # State 
    topic = state["topic"]
    interviews = state["interviews"]
    editor_feedback = state.get("editor_feedback", [])

    # Full set of interviews
    formatted_str_interview = "\n\n".join([f"Interview # {i}\n{interview}" for i, interview in enumerate(interviews, start=1)])

    # Generate report
    report_gen_chain = report_gen_prompt | report_writer_llm | StrOutputParser()
    report = report_gen_chain.invoke({"interviews": formatted_str_interview, 
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

    """ Route between question and save interview (finish) """
    
    # Get messages
    messages = state["messages"]

    # Check the number of expert answers 
    num_responses = len(
        [m for m in messages if isinstance(m, AIMessage) and m.name == name]
    )

    # End if expert has answered more than the max turns
    if num_responses >= max_num_turns:
        return "reflect"

    # This router is perform after each question - answer pair 
    # Get the last question asked to check if it signals the end of discussion
    last_question = messages[-2]
    
    if "Thank you so much for your help!" in last_question.content:
        return "reflect"
    return "ask_question"

# Add nodes and edges 
interview_builder = StateGraph(InterviewState)
interview_builder.add_node("ask_question", generate_question)
interview_builder.add_node("answer_question", generate_answer)
interview_builder.add_node("reflect", reflect)
interview_builder.add_node("save_interview", save_interview)
interview_builder.add_node("generate_report", generate_report) 

# Flow
interview_builder.add_edge(START, "ask_question")
interview_builder.add_edge("ask_question", "answer_question")
interview_builder.add_conditional_edges("answer_question", route_messages,["ask_question","reflect"])
interview_builder.add_edge("reflect", "save_interview")
interview_builder.add_edge("save_interview", "generate_report")
interview_builder.add_edge("generate_report", END)

sub_graph = interview_builder.compile()

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
    """ The is the "reduce" step where we gather all the sections, and combine them """
    
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
    """ Write the report to external service (Slack) """
    
    # Write to slack
    slack_fmt_promopt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                
                """Your goal is to first analyze a short report, which is in markdown.

                The report title will have ## header.

                The report will have two sections, each with ### header. 
                
                The first section will be titled "Context" and the second section will be titled "Why Is This Interesting?".

                Re-format these sections as Slack blocks so that it can be written to the Slack API.
            
                Be sure to include divider blocks between each section of the report.""",
            
            ),
            ("human", """Here is the report to re-format: {report}"""),
        ]
    )

    # Full set of interview reports
    sections = state["reports"]

    # Write each section of the report indvidually 
    for section_to_write in sections:
    
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
builder.add_node("finalize_report", finalize_report)
builder.add_node("write_report", write_report)

builder.add_edge(START, "generate_analysts")
builder.add_conditional_edges("generate_analysts", initiate_all_interviews, ["conduct_interview"])
builder.add_edge("conduct_interview", "finalize_report")
builder.add_edge("finalize_report", "write_report")
builder.add_edge("write_report", END)

# Set memory
memory = SqliteSaver.from_conn_string(save_db_path)

# Compile
# Interrupt after generate_analysts to see if we want to modify any personas
# Interrupt before write_report to see if we want to write the reports to Slack
graph = builder.compile(checkpointer=memory, interrupt_after=["generate_analysts"], interrupt_before=["write_report"],)