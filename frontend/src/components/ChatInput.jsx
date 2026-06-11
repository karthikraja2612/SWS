import { useState } from "react";

function ChatInput({ onSend, disabled, loading }) {
  const [value, setValue] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();
    const question = value.trim();
    if (!question || disabled) {
      return;
    }
    onSend(question);
    setValue("");
  };

  return (
    <footer className="chat-input-shell">
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Ask a question about the documents..."
          disabled={disabled}
          aria-label="Ask a document question"
        />
        <button type="submit" disabled={disabled || !value.trim()} aria-label="Send">
          {loading ? <span className="spinner tiny" /> : "Send"}
        </button>
      </form>
      <p className="input-helper">Answers are sourced only from retrieved documents. Press Enter to send.</p>
    </footer>
  );
}

export default ChatInput;
