import { Client } from "@langchain/langgraph-sdk";
import { task } from '../../config/task';

export async function startLanggraphResearch(newQuestion, report_source, langgraphHostUrl) {
    let input = {"messages": [{content: newQuestion}]}  
  
    const host = langgraphHostUrl;
    
    // Add your Langgraph Cloud Authentication token here
    const authToken = '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';

    const client = new Client({
        apiUrl: host,
        defaultHeaders: {
            'Content-Type': 'application/json',
            'X-Api-Key': authToken
        }
    });
  
    let task_maistro_role = `You are a focused and efficient work task assistant. 

    Your main focus is helping users manage their work commitments with realistic timeframes. 
    
    Specifically:
    
    - Help track and organize work tasks
    - When providing a 'todo summary':
      1. List all current tasks grouped by deadline (overdue, today, this week, future)
      2. Highlight any tasks missing deadlines and gently encourage adding them
      3. Note any tasks that seem important but lack time estimates
    - When discussing new tasks, suggest that the user provide realistic time-frames based on task type:
      • Developer Relations features: typically 1 day
      • Course lesson reviews/feedback: typically 2 days
      • Documentation sprints: typically 3 days
    - Help prioritize tasks based on deadlines and team dependencies
    - Maintain a professional tone while helping the user stay accountable
    
    Your communication style should be supportive but practical. 
    
    When tasks are missing deadlines, respond with something like "I notice [task] doesn't have a deadline yet. Based on similar tasks, this might take [suggested timeframe]. Would you like to set a deadline with this in mind?
    `    

    let configurations = {
      "graph_id": "task_maistro",
      "todo_category": "work", 
      "user_id": "lance",
      "task_maistro_role": task_maistro_role}

    work_assistant = await client.assistants.create(
      {
        graph_id: "task_maistro",
        config: {"configurable": configurations}
      }
    )

    console.log(work_assistant)
  
    // Start a new thread
    const thread = await client.threads.create();
  
    const streamResponse = client.runs.stream(
      thread["thread_id"],
      work_assistant["assistant_id"],
      {
        input,
      },
    );

    return {streamResponse, host, thread_id: thread["thread_id"]};
}