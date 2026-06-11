import { useMemo, useState } from "react";
import axios from "axios";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";

const suggestedQuestions = [
  "What topics are covered in these documents?",
  "Can you summarize the most important points?",
  "Where is the relevant policy or reference mentioned?",
  "What does the document say about deadlines or requirements?",
  "Which documents mention this topic?",
  "Can you give me a concise answer with sources?",
  "What are the key exceptions or edge cases?",
  "What should I read next for more detail?",
];

const initialMessage = {
  id: "welcome",
  role: "assistant",
  text: "Hi! I'm a document assistant. Ask me anything about the PDFs loaded into this RAG pipeline, and I'll answer using retrieved context only.",
  sources: [],
};

function App() {
  const [messages, setMessages] = useState([initialMessage]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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

    setError("");
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await api.post("/api/chat", { question });
      const answer = response.data?.answer?.trim() || "I don't have that information in the document context.";
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
      const message =
        error?.response?.data?.detail ||
        error?.message ||
        "Unable to reach the document service right now. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="top-header">
        <div className="brand-lockup">
          <span className="logo-badge">RAG</span>
          <div className="title-group">
            <h1>RAG AI Document Hub</h1>
            <p>Private retrieval-augmented answers from your document set</p>
          </div>
        </div>
        <span className="live-badge">LIVE DEMO</span>
      </header>

      <main className="chat-layout">
        <div className="info-banner">
          Powered by Groq AI + ChromaDB retrieval over your local document corpus.
        </div>

        <ChatWindow
          messages={messages}
          suggestedQuestions={suggestedQuestions}
          onQuestionChipClick={sendQuestion}
          loading={loading}
          error={error}
        />
      </main>

      <ChatInput onSend={sendQuestion} disabled={loading} loading={loading} />
    </div>
  );
}

export default App;
