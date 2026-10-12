import React, { useEffect, useRef } from 'react';

interface TypewriterTextProps {
  text: string;
  isStreaming?: boolean;
  className?: string;
  typingSpeed?: number;
}

const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  isStreaming = false,
  className = '',
  typingSpeed = 12,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [text]);

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <span className="whitespace-pre-wrap break-words">{text}</span>
      {isStreaming && (
        <span
          className="inline-block w-2 h-4 ml-0.5 bg-blue-500 animate-pulse align-middle"
          aria-hidden="true"
        />
      )}
    </div>
  );
};

export default TypewriterText;