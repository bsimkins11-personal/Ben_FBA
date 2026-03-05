"use client";

import { useState, useRef, useEffect } from "react";
import { streamChat, type SSEEvent } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [toolStatus, setToolStatus] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, toolStatus]);

  async function handleSend() {
    const text = input.trim();
    if (!text || streaming) return;

    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);
    setToolStatus("");

    let assistantText = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      for await (const event of streamChat(text, history)) {
        if (event.event === "tool_use") {
          setToolStatus(`Analyzing: ${event.data.replace(/_/g, " ")}...`);
        } else if (event.event === "text_delta") {
          setToolStatus("");
          assistantText += event.data;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: assistantText,
            };
            return updated;
          });
        } else if (event.event === "error") {
          assistantText += `\n\nError: ${event.data}`;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: assistantText,
            };
            return updated;
          });
        }
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: "Connection error. Is the backend running?",
        };
        return updated;
      });
    }

    setStreaming(false);
    setToolStatus("");
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-navy px-4 py-2.5 flex items-center gap-2">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/80">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        <span className="text-white text-xs font-bold uppercase tracking-wider">Co-Pilot Chat</span>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-white">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-surface flex items-center justify-center">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-navy">
                <circle cx="12" cy="12" r="10" />
                <path d="M8 12a4 4 0 0 1 8 0" />
                <line x1="12" y1="8" x2="12" y2="12" />
              </svg>
            </div>
            <p className="text-sm font-semibold text-navy">Bush League Co-Pilot</p>
            <p className="text-xs text-muted mt-1 max-w-[240px] mx-auto">
              Ask about your roster, matchup, waiver wire, or keepers
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-1.5">
              {[
                "How's my matchup this week?",
                "Who should I pick up?",
                "Analyze my keepers",
                "Where am I weakest?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => { setInput(q); }}
                  className="text-[11px] px-2.5 py-1.5 rounded-full border border-border text-subtle hover:bg-surface hover:border-navy/20 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-[13px] leading-relaxed whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-navy text-white"
                  : "bg-surface text-gray-800 border border-border"
              } ${streaming && i === messages.length - 1 && msg.role === "assistant" ? "cursor-blink" : ""}`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {toolStatus && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 px-3 py-2 bg-surface rounded-lg border border-border">
              <div className="w-3 h-3 border-2 border-navy border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-subtle">{toolStatus}</span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border p-3 bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about your team..."
            disabled={streaming}
            className="flex-1 text-sm px-3 py-2 rounded-lg border border-border focus:outline-none focus:border-navy focus:ring-1 focus:ring-navy/20 disabled:opacity-50 bg-white"
          />
          <button
            onClick={handleSend}
            disabled={streaming || !input.trim()}
            className="px-4 py-2 bg-mlb-red text-white text-xs font-bold uppercase rounded-lg hover:bg-mlb-red-hover disabled:opacity-40 transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
