import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import { getHealth, postChat } from './services/api';
import { Sparkles, AlertCircle, Bot, Loader2 } from 'lucide-react';

function generateSessionId() {
  return `s-${Math.random().toString(36).substring(2, 9)}`;
}

export default function App() {
  const [sessionId, setSessionId] = useState(generateSessionId);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [simulateFailure, setSimulateFailure] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [health, setHealth] = useState({ status: 'connecting', keys_configured: 0, cache_enabled: true });

  const messagesEndRef = useRef(null);

  // Check health on mount
  useEffect(() => {
    let isMounted = true;
    getHealth().then((data) => {
      if (isMounted) setHealth(data);
    });
    return () => { isMounted = false; };
  }, []);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, errorMessage]);

  const handleNewSession = () => {
    setSessionId(generateSessionId());
    setMessages([]);
    setInput('');
    setErrorMessage(null);
    setIsLoading(false);
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    // 1. Append user message to UI state immediately
    const userMessageId = `user-${Date.now()}`;
    const userMessage = {
      id: userMessageId,
      role: 'user',
      content: text,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput(''); // Clear input immediately after sending
    setIsLoading(true);
    setErrorMessage(null);

    try {
      // 2. Call backend POST /chat
      const data = await postChat({
        sessionId,
        message: text,
        systemPrompt: systemPrompt || undefined,
        simulateFailure: simulateFailure || undefined,
      });

      // 3. Append assistant response to UI state
      const assistantMessage = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: data.reply,
        metadata: data.metadata,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Chat error:', err);
      // Clean error presentation (never raw stack trace)
      let displayError = err.message || 'An unexpected error occurred.';
      if (err.status === 503) {
        displayError = 'HTTP 503: All LLM providers are currently unavailable or rate-limited. Automatic failover exhausted all configured keys.';
      } else if (err.status === 422) {
        displayError = `HTTP 422 Validation Error: ${err.message}`;
      }
      setErrorMessage(displayError);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-[#090d16] text-slate-100 font-sans">
      {/* Header */}
      <Header
        sessionId={sessionId}
        health={health}
        onNewSession={handleNewSession}
        systemPrompt={systemPrompt}
        setSystemPrompt={setSystemPrompt}
        simulateFailure={simulateFailure}
        setSimulateFailure={setSimulateFailure}
      />

      {/* Main Chat Scrollable Container */}
      <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="max-w-4xl mx-auto flex flex-col min-h-full">
          {/* Welcome Screen when conversation is empty */}
          {messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-12 px-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-xl shadow-blue-500/20 mb-4">
                <Sparkles className="w-7 h-7" />
              </div>
              <h2 className="text-xl font-bold tracking-tight text-white mb-2">
                Lyftr AI Resilient Chatbot
              </h2>
              <p className="text-sm text-slate-400 max-w-md leading-relaxed mb-6">
                Powered by Google Gemini through LiteLLM with multi-key automatic failover, response caching, and failure simulation.
              </p>

              {/* Sample Prompts */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg text-left">
                {[
                  "Explain quantum computing in simple terms",
                  "What is the capital of France?",
                  "Write a Python function to check for palindromes",
                  "How does response caching improve latency?"
                ].map((sample, idx) => (
                  <button
                    key={idx}
                    onClick={() => { setInput(sample); }}
                    className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-slate-700 text-xs text-slate-300 transition-colors text-left"
                  >
                    "{sample}"
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Messages Stream */}
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex justify-start mb-6">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="rounded-2xl rounded-tl-sm bg-slate-800/80 border border-slate-700 px-4 py-3 text-slate-300 text-sm flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                  <span>Thinking & querying model pool...</span>
                </div>
              </div>
            </div>
          )}

          {/* Error Message Banner */}
          {errorMessage && (
            <div className="mb-6 rounded-xl border border-red-500/30 bg-red-950/40 p-4 text-xs text-red-300 flex items-start gap-3 shadow-sm">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="font-semibold text-red-200 mb-0.5">Request Failed</div>
                <div>{errorMessage}</div>
              </div>
              <button
                onClick={() => setErrorMessage(null)}
                className="text-red-400 hover:text-red-200 text-xs font-medium"
              >
                Dismiss
              </button>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Chat Input */}
      <ChatInput
        input={input}
        setInput={setInput}
        onSend={handleSend}
        isLoading={isLoading}
      />
    </div>
  );
}
