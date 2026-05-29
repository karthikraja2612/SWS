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
          placeholder="Compose a policy question..."
          disabled={disabled}
          aria-label="Ask a policy question"
        />
        <button type="submit" disabled={disabled || !value.trim()} aria-label="Send">
          {loading ? <span className="spinner tiny" /> : "Send"}
        </button>
      </form>
      <p className="input-helper">Answers sourced from SWS AI company documents only. Press Enter to send.</p>
    </footer>
  );
}

export default ChatInput;
