import React, { useState, KeyboardEvent, ChangeEvent } from 'react';

interface MessageInputProps {
  onSend: (message: string) => void;
  isDisabled?: boolean;
  placeholder?: string;
}

const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  isDisabled = false,
  placeholder = 'Ask me anything...',
}) => {
  const [input, setInput] = useState('');

  const handleSend = () => {
    const trimmed = input.trim();
    if (trimmed && !isDisabled) {
      onSend(trimmed);
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
  };

  const isEmpty = !input.trim();

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-end gap-3 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-lg focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all">
          {/* Textarea */}
          <textarea
            value={input}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isDisabled}
            rows={1}
            className="flex-1 resize-none bg-transparent px-4 py-3 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none disabled:opacity-50 max-h-32 scrollbar-thin"
            style={{
              minHeight: '48px',
              maxHeight: '128px',
            }}
          />

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={isEmpty || isDisabled}
            className={`
              flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center
              transition-all duration-200 m-1.5
              ${
                isEmpty || isDisabled
                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed'
                  : 'bg-primary hover:bg-primary/90 active:scale-95 text-primary-foreground shadow-md'
              }
            `}
            aria-label="Send message"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </div>

        {/* Hint */}
        <p className="text-[11px] text-gray-400 mt-2 px-1">
          Press <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-[10px]">Enter</kbd> to send,{' '}
          <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-[10px]">Shift + Enter</kbd> for new line
        </p>
      </div>
    </div>
  );
};

export default MessageInput;