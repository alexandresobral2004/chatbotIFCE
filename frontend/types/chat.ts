export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  status?: string;
  node?: string;
  contextLoaded?: boolean;
}

export type ChatStatus = 'idle' | 'connecting' | 'receiving' | 'sending' | 'error';

export interface RetrievedContext {
  id: string;
  content: string;
  metadata?: Record<string, unknown>;
  score?: number;
}

export interface ChatState {
  messages: ChatMessage[];
  status: ChatStatus;
  context: RetrievedContext[];
  error: string | null;
}