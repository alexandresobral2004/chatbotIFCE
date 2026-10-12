import React from 'react';
import TypewriterText from './TypewriterText';
import StatusBadge from './StatusBadge';
import { ChatMessage } from '@/types/chat';

interface MessageListProps {
  messages: ChatMessage[];
  isLoading?: boolean;
}

const MessageList: React.FC<MessageListProps> = ({ messages, isLoading }) => {
  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="w-16 h-16 mb-4 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-200 mb-2">
          Welcome to RAG Chat
        </h2>
        <p className="text-gray-500 dark:text-gray-400 max-w-sm">
          Ask me anything about your documents. I&apos;ll search through the knowledge base and provide accurate answers.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 px-4 py-6">
      {messages.map(message => {
        const isUser = message.role === 'user';

        return (
          <div
            key={message.id}
            className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`flex flex-col max-w-[85%] ${
                isUser ? 'items-end' : 'items-start'
              }`}
            >
              {/* Avatar + Name for AI */}
              {!isUser && (
                <div className="flex items-center gap-2 mb-1.5 ml-1">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                    <svg
                      className="w-3.5 h-3.5 text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                      />
                    </svg>
                  </div>
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    AI Assistant
                  </span>
                </div>
              )}

              {/* Status badge for AI messages */}
              {!isUser && message.status && message.status !== 'sent' && (
                <div className="mb-1.5">
                  <StatusBadge
                    status={message.status}
                    variant={
                      message.status === 'error'
                        ? 'error'
                        : message.status === 'context_loaded'
                        ? 'success'
                        : 'info'
                    }
                  />
                </div>
              )}

              {/* Message bubble */}
              <div
                className={`
                  relative px-4 py-3 rounded-2xl shadow-sm
                  ${
                    isUser
                      ? 'bg-blue-600 text-white rounded-br-md'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-md'
                  }
                  ${message.isStreaming ? 'animate-pulse-subtle' : ''}
                `}
              >
                <TypewriterText
                  text={message.content}
                  isStreaming={message.isStreaming}
                  className="text-sm leading-relaxed"
                />
              </div>

              {/* Timestamp */}
              <span
                className={`
                  text-[10px] mt-1 px-1
                  ${isUser ? 'text-gray-400' : 'text-gray-400'}
                `}
              >
                {message.timestamp.toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
          </div>
        );
      })}

      {/* Loading indicator when no messages but still loading */}
      {isLoading && messages.length === 0 && (
        <div className="flex justify-start">
          <div className="flex items-center gap-2 px-4 py-3 rounded-2xl bg-gray-100 dark:bg-gray-800">
            <div className="flex gap-1">
              {[0, 1, 2].map(i => (
                <span
                  key={i}
                  className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
                  style={{ animationDelay: `${i * 200}ms` }}
                />
              ))}
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Thinking...
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageList;