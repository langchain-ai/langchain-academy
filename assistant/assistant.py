import os
import operator
import praw
import requests

from typing_extensions import TypedDict, List, Annotated

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import chain as as_runnable

from langchain_openai import ChatOpenAI

from langgraph.graph import MessagesState
from langgraph.graph import END, START, StateGraph
from langgraph.constants import Send

### --- Global parameters --- ###

# Webhook URL for Slack
slack_bot_url = os.getenv('LANCE_BOT_SLACK_URL')

# Max turns for interviews 
max_num_turns = 2

# LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0) 

# Reddit creds
reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')

# Initialize the Reddit instance
reddit = praw.Reddit(client_id=reddit_client_id,
                     client_secret=reddit_client_secret,
                     user_agent='Fantasy Football Loader')

### --- Data loaders --- ###

def get_recent_reddit_posts(subreddit_name,
                            filter_to_use,
                            number_of_posts,
                            number_of_comments,
                           ):

    ''' Get comments from top posts in a particular subreddit '''

    # Access the subreddit
    subreddit = reddit.subreddit(subreddit_name)
    
    # Get top posts based on the specified filter
    top_posts = subreddit.top(time_filter=filter_to_use, limit=number_of_posts)
    
    # Initialize an empty string to store the output
    reddit_expert_context = ""
    
    # Process each post
    for post in top_posts:
        reddit_expert_context += f"Title: {post.title}\n"
        reddit_expert_context += f"URL: {post.url}\n"
        reddit_expert_context += f"Score: {post.score}\n"
        
        post.comments.replace_more(limit=0)  # Flatten the comment tree
        
        # Get the specified number of top comments
        for i, comment in enumerate(post.comments[:number_of_comments]):
            reddit_expert_context += f"Top Comment {i+1}: {comment.body}\n"
            reddit_expert_context += f"Comment Score: {comment.score}\n\n"
        
        reddit_expert_context += "="*50 + "\n\n"

    return reddit_expert_context

def get_reddit_post(url,
                   number_of_comments):
    
    ''' Get reddit post comments '''

    # Fetch the submission
    post = reddit.submission(url=url)
    
    # Load the comments
    post.comments.replace_more(limit=None) # Flatten the comment tree

    # Initialize an empty string to store the output
    reddit_expert_context = ""
    reddit_expert_context += f"Title: {post.title}\n"
    reddit_expert_context += f"URL: {post.url}   \n"
    reddit_expert_context += f"Post: {post.selftext}\n"

    # Get the specified number of top comments
    for i, comment in enumerate(post.comments[:number_of_comments]):
        reddit_expert_context += f"Top Comment {i+1}: {comment.body}\n"
        reddit_expert_context += f"Comment Score: {comment.score}\n\n"
        reddit_expert_context += "="*50 + "\n\n"

    return reddit_expert_context

### --- Graph state --- ###

class Expert(BaseModel):
    name: str = Field(
        description="Name of the expert.", pattern=r"^[a-zA-Z0-9_-]{1,64}$"
    )
    role: str = Field(
        description="Role of the expert.",
    )
    context: SystemMessage = Field(
        description="Instructions used by the expert.",
    )

    def answer(self, dicussion: List) -> AIMessage:
        return llm.invoke([self.context]+dicussion)

class Take(BaseModel):
    title: str = Field(
        description="Punchy summary title for the take or perspective",
    )
    take: str = Field(
        description="Fun, punchy observation from the discussion between expert and interviewer.",
    )

class Takes(BaseModel):
    takes: List[Take] = Field(
        description="A list of takes, each containing a title and a take observation."
    )

class OverallState(TypedDict):
    topic: str
    contexts: dict
    experts: List[Expert]
    takes: Annotated[List[Take], operator.add]

class InterviewState(MessagesState):
    topic: str
    expert: Expert
    
class InterviewOutputState(TypedDict):
     takes: List[Take]

### --- Graph --- ###

def load_context(state: OverallState):
    """ Generate our contexts from Reddit """
    
    # Replace with the subreddit you're interested in
    subreddit_name = 'fantasyfootball'
    
    # Get top comments from past <day, month, etc>
    filter_to_use = 'day'
    
    # Number of posts to gather
    number_of_posts = 5
    
    # Number of top comments to gather per post
    number_of_comments = 10

    # Pull recent posts 
    reddit_recent_posts = get_recent_reddit_posts(subreddit_name,
                                                  filter_to_use,
                                                  number_of_posts,
                                                  number_of_comments)
    # Any specific posts to include
    url = "https://www.reddit.com/r/fantasyfootball/comments/1ewk6kr/theres_only_one_draft_strategy_that_ill_ever/"
    number_of_comments = 20
    reddit_draft_strategy_context = get_reddit_post(url,number_of_comments)
    
    url = "https://www.reddit.com/r/fantasyfootball/comments/1espdv7/who_is_one_guy_you_arent_leaving_the_draft/"
    number_of_comments = 20
    reddit_top_player_context = get_reddit_post(url,number_of_comments)

    return {"contexts": {"reddit_recent_posts":reddit_recent_posts,
                        "reddit_draft_strategy_context": reddit_draft_strategy_context,
                        "reddit_top_player_context": reddit_top_player_context}
           }

def generate_experts(state: OverallState):
    """ Generate our experts """

    contexts = state['contexts']
    
    preamble = "You are an expert in in Fantasy Football. You are being interviewed by an analyst. Only use the provided sources, don't make up your own answers."
    
    draft_strategy_expert = Expert(
        name="Moe",
        role="Fantasy Draft Strategy Expert",
        context=SystemMessage(content=f"{preamble} Use only this information to answer questions from the analyst: {contexts['reddit_draft_strategy_context']}"),
    )
    
    top_player_expert = Expert(
        name="Jimbo",
        role="Top Players To Draft Expert", 
        context=SystemMessage(content=f"{preamble} Use only this information to answer questions from the analyst: {contexts['reddit_top_player_context']}"),
    )

    recent_events_expert = Expert(
        name="Barney",
        role="Following recent news", 
        context=SystemMessage(content=f"{preamble} Use only this information to answer questions from the analyst: {contexts['reddit_recent_posts']}"),
    )

    return {"experts": [draft_strategy_expert, top_player_expert, recent_events_expert]}

def generate_question(state: InterviewState):
    """Node to generate a question """

    instructions = SystemMessage(content=f"""
    
    You are an analyst tasked with interviewing an expert to learn about a specific topic. 
    
    Here is your topic: {state["topic"]}
    
    1. Interesting: Insights that people will find surprising or non-obvious.
    
    2. Specific: Insights that avoid generalities and include specific examples from the expert.
    
    Begin by introducing yourself, and then ask your question.
    
    Continue to ask questions to drill down and refine your understanding of the topic.
    
    As the interview proceeds for a bit, assess your understanding.
    
    If you are satisfied, then complete the interview with: "Thank you so much for your help!"
    
    Remember to stay in character throughout your response, reflecting the persona and goals provided to you.""")
    
    # Generate question 
    result = llm.invoke([instructions]+state["messages"])   
    
    # Write messages to state
    return {"messages": [HumanMessage(content=result.content,name='Interviewer')]}

def generate_answer(state: InterviewState):
    """ Node to answer a question """

    messages = state["messages"]
    expert = state["expert"]
   
    # Answer question
    answer = expert.answer(messages)
    
    # Use this to track expert responses
    answer.name = 'expert'
    
    # Append it to state
    return {"messages": [answer]}

def generate_takes(state: InterviewState):
    """ Node to answer a question """

    # Get discussion
    messages = state["messages"]

    # Instructions
    instructions = SystemMessage(content=f"""
    
    Distill the conversation between the analyst and expert into a set of fun and informative takes. 
    
    Each take should have a punchy subject line. 
    
    Each take should be specific and provide examples to back-up the statement.
    
    Aim for 5 - 10 different takes per interview that 1) cover the most interesting points raised and 2) avoid repetition.""")

    # Enforce structured output
    structured_llm = llm.with_structured_output(Takes)
    
    # Generate takes
    takes = structured_llm.invoke([instructions]+messages)
        
    # * Write to state, returning takes as a list so that it can be addended from all interviews * 
    return {"takes": [takes]}

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
        return "generate_takes"

    # This router is run after each question - answer pair 
    last_question = messages[-2]
    
    if "Thank you so much for your help" in last_question.content:
        return "generate_takes"
    return "ask_question"

def initiate_all_interviews(state: OverallState):
    """ This is the "map" step where we run each interview sub-graph using Send API """    

    topic = state["topic"]
    return [Send("conduct_interview", {"topic": topic,
                                       "expert": expert}) for expert in state["experts"]]

def write_to_slack(state: OverallState):
    """ Write the report to external service (Slack) """
    
    # Full set of interview reports
    takes = state["takes"]

    # Write to your Slack Channel via webhook
    true = True
    headers = {
        'Content-Type': 'application/json',
    }

    # Write to slack
    for t in takes:
        for take in t.takes:
            
            # Blocks
            blocks = []
            
            # Block 1: Title section
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{take.title}*"
                }
            })
            
            # Block 2: Divider
            blocks.append({
                "type": "divider"
            })
            
            # Block 3: Content section
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{take.take}"
                }
            })
    
            blocks.insert(0, {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":fire: :robot_face: Take-Bot is heating up ...",
                    "emoji": true
                }
            })
            
            data = {
                "blocks": blocks,
            }
            
            response = requests.post(slack_bot_url, headers=headers, json=data)

# Add nodes and edges for interview 
interview_builder = StateGraph(input=InterviewState, output=InterviewOutputState)
interview_builder.add_node("ask_question", generate_question)
interview_builder.add_node("answer_question", generate_answer)
interview_builder.add_node("generate_takes", generate_takes)

# Flow for interview
interview_builder.add_edge(START, "ask_question")
interview_builder.add_edge("ask_question", "answer_question")
interview_builder.add_conditional_edges("answer_question", route_messages,['ask_question','generate_takes'])
interview_builder.add_edge("generate_takes", END)

# Add nodes and edges for overall graph
overall_builder = StateGraph(OverallState)

# Add nodes and edges for overall graph
overall_builder.add_node("load_context", load_context)
overall_builder.add_node("generate_experts", generate_experts)
overall_builder.add_node("conduct_interview", interview_builder.compile())
overall_builder.add_node("write_to_slack",write_to_slack)

overall_builder.add_edge(START, "load_context")
overall_builder.add_edge("load_context", "generate_experts")
overall_builder.add_conditional_edges("generate_experts", initiate_all_interviews, ["conduct_interview"])
overall_builder.add_edge("conduct_interview", "write_to_slack")
overall_builder.add_edge("write_to_slack", END)

# Compile
graph = overall_builder.compile(interrupt_before=['write_to_slack'])