"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { startLanggraphResearch } from '../components/Langgraph/Langgraph';
import findDifferences from '../helpers/findDifferences';
import { ChatBoxSettings, QuestionData } from '../types/data';

import Header from "@/components/Header";
import Hero from "@/components/Hero";
import Footer from "@/components/Footer";
import InputArea from "@/components/Blocks/InputArea";
import AgentLogs from "@/components/Blocks/AgentLogs";
import HumanFeedback from "@/components/HumanFeedback";
import LoadingDots from "@/components/LoadingDots";

export default function Home() {
  const [promptValue, setPromptValue] = useState("");
  const [showResult, setShowResult] = useState(false);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatBoxSettings, setChatBoxSettings] = useState<ChatBoxSettings>({ 
    report_source: 'web', 
    report_type: 'research_report', 
    tone: 'Objective' 
  });
  const [showHumanFeedback, setShowHumanFeedback] = useState(false);
  const [questionForHuman, setQuestionForHuman] = useState<true | false>(false);
  const [allLogs, setAllLogs] = useState<any[]>([]);
  const [isStopped, setIsStopped] = useState(false);
  const [orderedData, setOrderedData] = useState<Data[]>([]);

  const handleFeedbackSubmit = (feedback: string | null) => {
    if (socket) {
      socket.send(JSON.stringify({ type: 'human_feedback', content: feedback }));
    }
    setShowHumanFeedback(false);
  };

  const handleDisplayResult = async (newQuestion: string) => {
    setShowResult(true);
    setLoading(true);
    setPromptValue("");
    setAnswer("");
    
    const storedConfig = localStorage.getItem('apiVariables');
    const apiVariables = storedConfig ? JSON.parse(storedConfig) : {};
    const langgraphHostUrl = 'http://localhost:8123'

    if (langgraphHostUrl) {
      let { streamResponse, host, thread_id } = await startLanggraphResearch(newQuestion, chatBoxSettings.report_source, langgraphHostUrl);
      const langsmithGuiLink = `https://smith.langchain.com/studio/thread/${thread_id}?baseUrl=${host}`;
      setOrderedData((prevOrder) => [...prevOrder, { type: 'langgraphButton', link: langsmithGuiLink }]);

      let previousChunk = null;
      for await (const chunk of streamResponse) {
        if (chunk.data.report != null && chunk.data.report != "Full report content here") {
          setOrderedData((prevOrder) => [...prevOrder, { ...chunk.data, output: chunk.data.report, type: 'report' }]);
          setLoading(false);
        } else if (previousChunk) {
          const differences = findDifferences(previousChunk, chunk);
          setOrderedData((prevOrder) => [...prevOrder, { type: 'differences', content: 'differences', output: JSON.stringify(differences) }]);
        }
        previousChunk = chunk;
      }
    } else {
      initializeWebSocket(newQuestion, chatBoxSettings);
    }
  };

  const reset = () => {
    setShowResult(false);
    setPromptValue("");
    setAnswer("");
  };

  /**
   * Handles starting a new research
   * - Clears all previous research data and states
   * - Resets UI to initial state
   * - Closes any existing WebSocket connections
   */
  const handleStartNewResearch = () => {
    // Reset UI states
    setShowResult(false);
    setPromptValue("");
    setIsStopped(false);
    setAnswer("");
    setAllLogs([]);
    
    // Reset feedback states
    setShowHumanFeedback(false);
    setQuestionForHuman(false);
    
    // Clean up connections
    if (socket) {
      socket.close();
    }
    setLoading(false);
  };

  return (
    <>
      <Header 
        loading={loading}
        isStopped={isStopped}
        showResult={showResult}
        onNewResearch={handleStartNewResearch}
      />
      <main className="min-h-[100vh] pt-[120px]">
        {!showResult && (
          <Hero
            promptValue={promptValue}
            setPromptValue={setPromptValue}
            handleDisplayResult={handleDisplayResult}
          />
        )}

        {showResult && (
          <div className="flex h-full w-full grow flex-col justify-between">
            <div className="container w-full space-y-2">
              <div className="container space-y-2 task-components">
                <AgentLogs
                  agentLogs={orderedData}
                  answer={answer}
                  allLogs={allLogs}
                />
              </div>

              {showHumanFeedback && (
                <HumanFeedback
                  questionForHuman={questionForHuman}
                  websocket={socket}
                  onFeedbackSubmit={handleFeedbackSubmit}
                />
              )}

              <div className="pt-1 sm:pt-2"></div>
            </div>
            <div id="input-area" className="container px-4 lg:px-0">
              {loading ? (
                <LoadingDots />
              ) : (
                <InputArea
                  promptValue={promptValue}
                  setPromptValue={setPromptValue}
                  handleSubmit={handleChat}
                  handleSecondary={handleDisplayResult}
                  disabled={loading}
                  reset={reset}
                  isStopped={isStopped}
                />
              )}
            </div>
          </div>
        )}
      </main>
      <Footer setChatBoxSettings={setChatBoxSettings} chatBoxSettings={chatBoxSettings} />
    </>
  );
}