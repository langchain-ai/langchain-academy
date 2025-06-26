import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { ChatOpenAI } from "@langchain/openai";
import { getWeather } from "./tools/getWeather";
import { searchFiles } from "./tools/searchFiles";
import { listFiles } from "./tools/listFiles";
import { viewFile } from "./tools/viewFile";
import { searchWeb } from "./tools/searchWeb";
import { createSwarm, createHandoffTool } from "@langchain/langgraph-swarm";
// const model = new ChatOpenAI({
// model: "gpt-4.1-mini"
// });
const geminiModel = new ChatOpenAI({
model: "google/gemini-2.5-flash-preview",
configuration: {
baseURL: "https://openrouter.helicone.ai/api/v1",
defaultHeaders: {
"Helicone-Auth": `Bearer ${process.env.HELICONE_API_KEY}`,
"Helicone-Cache-Enabled": "true",
"Helicone-LLM-Security-Enabled": "true",
"Helicone-LLM-Security-Advanced": "true",
},
},
});
// Weather Agent
const weatherAgent = createReactAgent({
llm: geminiModel,
tools: [
getWeather,
createHandoffTool({
agentName: "GeneralAgent",
description: "Transfer to GeneralAgent for other tasks.",
}),
],
name: "WeatherAgent",
prompt: "You are a weather assistant. You can get the current weather.",
});
// General Agent
const generalAgent = createReactAgent({
llm: geminiModel,
tools: [
searchFiles,
listFiles,
viewFile,
searchWeb,
createHandoffTool({
agentName: "WeatherAgent",
description: "Transfer to WeatherAgent for weather-related queries."
}),
],
name: "GeneralAgent",
prompt: "You are a general assistant. You can search files, list files, view files, and perform web searches. You can also hand off to a weather specialist.",
});
//Swarm workflow
const workflow = createSwarm({
agents: [generalAgent, weatherAgent],
defaultActiveAgent: "GeneralAgent",
});
export const app = workflow