// LogMessage.tsx
interface LogMessageProps {
  logs: {
    type: string;
    content?: string;
    output?: string;
    link?: string;
    tool_calls?: any[];
  }[];
}

const LogMessage: React.FC<LogMessageProps> = ({ logs }) => {
  return (
    <>
      {logs.map((message, index) => {
        if (message.type === 'langgraphButton') {
          return (
            <div key={index} className="w-full max-w-4xl mx-auto rounded-lg pt-2 mt-3 pb-2 px-4 bg-gray-900 shadow-md">
              <a href={message.link} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">
                View in Langsmith
              </a>
            </div>
          );
        }

        if (message.type === 'report' || message.type === 'differences') {
          return (
            <div key={index} className="w-full max-w-4xl mx-auto rounded-lg pt-2 mt-3 pb-2 px-4 bg-gray-900 shadow-md">
              <p className="py-3 text-base leading-relaxed text-white">
                {message.output}
              </p>
            </div>
          );
        }

        return (
          <div key={index} className="w-full max-w-4xl mx-auto rounded-lg pt-2 mt-3 pb-2 px-4 bg-gray-900 shadow-md">
            <p className={`py-3 text-base leading-relaxed ${
              message.type === 'question' ? 'text-blue-300' : 'text-white'
            }`}>
              {message.content}
            </p>
          </div>
        );
      })}
    </>
  );
};

export default LogMessage;