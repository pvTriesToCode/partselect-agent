import React, { useState, useEffect, useRef } from "react";
import "./ChatWindow.css";
import { getAIMessage } from "../api/api";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import PartCard from "./PartCard";
import CompatBadge from "./CompatBadge";
import VideoCard from "./VideoCard";

function ChatWindow() {

  const defaultMessage = [{
    role: "assistant",
    content: `👋 **Welcome to PartSelect AI Assistant!**

I'm here to help you with your refrigerator and dishwasher repairs. Here's what I can do:

- 🔍 **Find parts** — describe what broke or what you need
- 📋 **Part details** — share a part number for pricing, availability and install info
- ✅ **Compatibility check** — tell me a part number and your model number
- 🔧 **Repair guidance** — describe the symptom and I'll walk you through the fix

You can just describe your issue and I'll figure out the rest. What's going on with your appliance?`
  }];

  const LOADING_MESSAGES = [
    "Searching PartSelect...",
    "One moment...",
    "Looking that up for you...",
    "On it...",
    "Checking PartSelect data...",
    "Almost ready...",
    "Pulling the latest info...",
  ];

  const [messages, setMessages] = useState(defaultMessage);
  const [cardMetadata, setCardMetadata] = useState([null]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [loadingMsgIndex, setLoadingMsgIndex] = useState(0);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!isLoading) return;
    setLoadingMsgIndex(0);
    const interval = setInterval(() => {
      setLoadingMsgIndex(prev => (prev + 1) % LOADING_MESSAGES.length);
    }, 1500);
    return () => clearInterval(interval);
  }, [isLoading]);

  const handleSend = async (input) => {
    if (input.trim() !== "" && !isLoading) {
      setMessages(prev => [...prev, { role: "user", content: input }]);
      setCardMetadata(prev => [...prev, null]);

      setMessages(prev => [...prev, { role: "assistant", content: "" }]);
      const assistantIndex = messages.length + 1;
      setCardMetadata(prev => [...prev, null]);

      setInput("");
      setIsLoading(true);
      setIsStreaming(true);
      try {
        await getAIMessage(
          input,
          (partialContent) => {
            setMessages(prev => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                role: "assistant",
                content: partialContent
              };
              return updated;
            });
          },
          (metadata) => {
            setCardMetadata(prev => {
              const updated = [...prev];
              updated[assistantIndex] = metadata;
              return updated;
            });
          }
        );
      } finally {
        setIsLoading(false);
        setIsStreaming(false);
      }
    }
  };

  return (
    <div className="messages-container">
      {messages.map((message, index) => {
        const isLastMessage = index === messages.length - 1;
        return (
        <div key={index} className={`${message.role}-message-container`}>
          <div className={`message ${message.role}-message`}>
            {isLastMessage && isLoading ? (
              <div className="thinking-indicator">
                <span className="thinking-dot"></span>
                <span className="thinking-dot"></span>
                <span className="thinking-dot"></span>
                <span className="thinking-text">{LOADING_MESSAGES[loadingMsgIndex]}</span>
              </div>
            ) : (
              message.content && (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              )
            )}
          </div>
          {cardMetadata[index] && cardMetadata[index].type === "part" && (
            <PartCard metadata={cardMetadata[index]} />
          )}
          {cardMetadata[index] && cardMetadata[index].type === "repair" && (
            <VideoCard metadata={cardMetadata[index]} />
          )}
        </div>
        );
      })}
      <div ref={messagesEndRef} />
      <div className="input-area">
        <div className="input-wrapper">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            disabled={isLoading}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                handleSend(input);
                e.preventDefault();
              }
            }}
          />
          <button
            className="send-button"
            onClick={() => handleSend(input)}
            disabled={isLoading}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;
