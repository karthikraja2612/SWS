function MessageBubble({ message }) {
  const isAssistant = message.role === "assistant";
  const hasSources = isAssistant && Array.isArray(message.sources) && message.sources.length > 0;

  return (
    <div className={isAssistant ? "assistant-row" : "user-row"}>
      {isAssistant ? <div className="assistant-avatar">AI</div> : null}

      <div className={`message-bubble ${isAssistant ? "assistant" : "user"}`}>
        <p>{message.text}</p>

        {hasSources ? (
          <div className="sources-block">
            <span className="sources-title">Sources</span>
            <div className="sources-list">
              {message.sources.map((source) => (
                <span className="source-pill" key={`${message.id}-${source}`}>
                  {source}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default MessageBubble;
