import { useMemo, useState } from "react";
import axios from "axios";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";

const suggestedQuestions = [
  "What is the annual leave policy?",
  "How many sick leave days do I get?",
  "What is the notice period for resignation?",
  "What are the WFH guidelines?",
  "What health insurance benefits do we have?",
  "How does the performance review work?",
  "What tools does SWS AI use for communication?",
  "What is the IT password policy?",
];

const initialMessage = {
  id: "welcome",
  role: "assistant",
  text: "Hi! I'm the SWS AI company assistant. Ask me anything about our HR policies, leave, benefits, resignation process, WFH guidelines, or any other company policy.",
  sources: [],
};

function App() {
  const [messages, setMessages] = useState([initialMessage]);
  const [loading, setLoading] = useState(false);

  const api = useMemo(() => {
    const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    return axios.create({ baseURL, timeout: 30000 });
  }, []);

  const sendQuestion = async (questionText) => {
    const question = questionText.trim();
    if (!question || loading) {
      return;
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: question,
      sources: [],
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await api.post("/api/chat", { question });
      const answer = response.data?.answer?.trim() || "I don't have that information in the company documents.";
      const sources = Array.isArray(response.data?.sources) ? response.data.sources : [];

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: answer,
          sources,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: "I don't have that information in the company documents.",
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="top-header">
        <div className="header-left">
          <button className="back-btn" type="button" aria-label="Back">
            <span className="back-arrow">&lt;</span>
            <span>Back</span>
          </button>
          <div className="title-group">
            <span className="logo-badge">AI</span>
            <h1>SWS AI Document Hub</h1>
            <span className="live-badge">LIVE DEMO</span>
          </div>
        </div>
        <button className="notify-btn" type="button" aria-label="Notifications">
          N
        </button>
      </header>

      <nav className="tabs-row">
        <button className="tab-item" type="button">Document Upload</button>
        <button className="tab-item active" type="button">AI Assistant</button>
      </nav>

      <main className="chat-layout">
        <div className="info-banner">
          Powered by Ollama AI + 10 SWS AI company documents. Ask anything about company policies.
        </div>

        <ChatWindow
          messages={messages}
          suggestedQuestions={suggestedQuestions}
          onQuestionChipClick={sendQuestion}
          loading={loading}
        />
      </main>

      <ChatInput onSend={sendQuestion} disabled={loading} loading={loading} />
    </div>
  );
}

export default App;
