import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import QuestionChips from "./QuestionChips";

function ChatWindow({ messages, suggestedQuestions, onQuestionChipClick, loading, error }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <section className="chat-window" aria-label="Chat conversation">
      <div className="messages-stack">
        {error ? <div className="error-banner">{error}</div> : null}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {loading ? (
          <div className="assistant-row loading-row">
            <div className="assistant-avatar">AI</div>
            <div className="message-bubble assistant">
              <div className="spinner" aria-label="Loading" />
              <span>Looking through company documents...</span>
            </div>
          </div>
        ) : null}

        <div ref={messagesEndRef} />
      </div>

      <QuestionChips questions={suggestedQuestions} onQuestionClick={onQuestionChipClick} disabled={loading} />
    </section>
  );
}

export default ChatWindow;
