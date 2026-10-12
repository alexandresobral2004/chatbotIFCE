"use client";

import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { FiType, FiZoomIn, FiZoomOut, FiRotateCcw, FiClock, FiChevronsRight, FiChevronsLeft } from "react-icons/fi";
import FormattedResponse from "./FormattedResponse";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface SSEPayload {
  type: "status" | "token" | "error";
  status?: string;
  content?: string;
  error?: string;
}

interface ChatInterfaceProps {
  sessionId: string;
  /** JWT emitido pelo sistema principal; enviado como Bearer em todas as chamadas. */
  authToken?: string;
  /** Chamado quando a API responde 401 (token expirado ou inválido): o pai deve voltar ao login. */
  onUnauthorized?: () => void;
  initialMessages?: ChatMessage[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const FONT_SIZE_LEVELS = [
  { label: "85%", px: 13, name: "Pequena" },
  { label: "100%", px: 15, name: "Padrão" },
  { label: "115%", px: 17, name: "Média" },
  { label: "130%", px: 19, name: "Grande" },
  { label: "150%", px: 22, name: "Extra Grande" },
];

const MessageBubble = ({
  message,
  isStreaming,
  feedback,
  fontSizePx = 15,
  onLike,
  onDislike,
  onCopy,
  onPasteToInput,
}: {
  message: ChatMessage;
  isStreaming: boolean;
  feedback?: "like" | "dislike";
  fontSizePx?: number;
  onLike: (id: string) => void;
  onDislike: (id: string) => void;
  onCopy: (text: string) => void;
  onPasteToInput: (text: string) => void;
}) => {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  return (
    <div data-message-id={message.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`flex flex-col max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
        {isAssistant && (
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center shadow-sm">
              <svg className="w-4 h-4 text-primary-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <span className="text-sm font-semibold text-foreground">JupiterClass</span>
              <p className="text-xs text-muted-foreground">Assistente de Pesquisa</p>
            </div>
          </div>
        )}

        <div
          style={{ fontSize: `${fontSizePx}px` }}
          className={`
            relative px-5 py-4 rounded-2xl shadow-sm transition-all duration-150
            ${isUser
              ? "bg-primary text-primary-foreground rounded-br-md"
              : "bg-card border border-border text-card-foreground rounded-bl-md"
            }
            ${isStreaming && !isUser ? "animate-pulse" : ""}
          `}
        >
          {isUser && (
            <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-0 h-0 border-t-8 border-t-transparent border-b-8 border-b-transparent border-r-8 border-r-primary" />
          )}

          {!isUser && (
            <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-0 h-0 border-t-8 border-t-transparent border-b-8 border-b-transparent border-r-8 border-r-card" />
          )}

          {!isUser && (
            <FormattedResponse
              text={message.content}
              className="leading-relaxed"
            />
          )}

          {isUser && (
            <p className="leading-relaxed whitespace-pre-wrap break-words">
              {message.content}
            </p>
          )}

          {isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse align-middle" />
          )}
        </div>

        <div className="flex items-center justify-between w-full mt-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>

          {isAssistant && !isStreaming && (
            <div className="flex items-center gap-1 text-muted-foreground ml-4">
              <button
                onClick={() => onLike(message.id)}
                aria-label="Gostei"
                title="Gostei da resposta"
                className={`p-1 rounded-lg hover:text-emerald-600 hover:bg-emerald-500/10 transition-all ${
                  feedback === "like" ? "text-emerald-500 bg-emerald-500/10" : ""
                }`}
              >
                <svg className="w-3.5 h-3.5" fill={feedback === "like" ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3zM7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3" />
                </svg>
              </button>

              <button
                onClick={() => onDislike(message.id)}
                aria-label="Não gostei"
                title="Não gostei da resposta"
                className={`p-1 rounded-lg hover:text-rose-600 hover:bg-rose-500/10 transition-all ${
                  feedback === "dislike" ? "text-rose-500 bg-rose-500/10" : ""
                }`}
              >
                <svg className="w-3.5 h-3.5" fill={feedback === "dislike" ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3zm7-13h3a2 2 0 012 2v7a2 2 0 01-2 2h-3" />
                </svg>
              </button>

              <span className="w-px h-3 bg-border mx-0.5" />

              <button
                onClick={() => onCopy(message.content)}
                aria-label="Copiar resposta"
                title="Copiar resposta para área de transferência"
                className="p-1 rounded-lg hover:text-foreground hover:bg-muted transition-all flex items-center gap-0.5 text-[10px]"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                </svg>
                Copiar
              </button>

              <button
                onClick={() => onPasteToInput(message.content)}
                aria-label="Colar no campo de texto"
                title="Colar esta resposta no campo de digitação do chat"
                className="p-1 rounded-lg hover:text-foreground hover:bg-muted transition-all flex items-center gap-0.5 text-[10px]"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                Colar
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const StatusBadge = ({ status }: { status: string }) => (
  <div className="inline-flex items-center gap-2 px-4 py-2 bg-secondary rounded-full animate-in slide-in-from-bottom-2">
    <div className="flex gap-0.5">
      <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-dot" />
      <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-dot" style={{ animationDelay: "150ms" }} />
      <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-dot" style={{ animationDelay: "300ms" }} />
    </div>
    <span className="text-xs font-medium text-muted-foreground">{status}</span>
  </div>
);

const WelcomeScreen = ({ onSelectQuery }: { onSelectQuery: (text: string) => void }) => (
  <div className="flex flex-col items-center justify-center h-full py-16 px-4">
    <div className="w-full max-w-md overflow-hidden rounded-2xl border border-border shadow-md mb-8 aspect-[4/3] relative bg-muted flex items-center justify-center">
      <img
        src="/man_researching.jpg"
        alt="Ilustração de um pesquisador focado estudando em uma biblioteca com livros e notebook"
        className="w-full h-full object-cover object-center"
      />
    </div>

    <h2 className="text-2xl font-bold text-foreground mb-3 text-center">
      Olá, sou o JupiterClass
    </h2>

    <p className="text-muted-foreground text-center max-w-md mb-10 leading-relaxed">
      Seu assistente de pesquisa acadêmica. Posso ajudar com normas ABNT, metodologia científica e referências bibliográficas.
    </p>

    <section aria-labelledby="como-funciona" className="w-full max-w-lg mb-10 rounded-xl border border-border bg-card p-5">
      <h3 id="como-funciona" className="text-sm font-semibold text-foreground mb-3">Como funciona</h3>
      <ol className="space-y-3 text-sm text-muted-foreground list-decimal list-inside">
        <li>
          <span className="text-foreground font-medium">Pergunte do seu jeito.</span>{" "}
          Escreva em linguagem natural, por exemplo sobre normas ABNT, estrutura de TCC, métodos de pesquisa ou ética em pesquisa.
        </li>
        <li>
          <span className="text-foreground font-medium">Busco nos documentos oficiais.</span>{" "}
          As respostas se baseiam no manual de normalização do IFCE, nos modelos de trabalho e em materiais de metodologia, e não em palpites.
        </li>
        <li>
          <span className="text-foreground font-medium">Confiro antes de responder.</span>{" "}
          Verifico se a resposta é sustentada pelos documentos e listo as referências consultadas (ABNT). Se parte dela não tiver base nos documentos, acrescento um aviso.
        </li>
      </ol>
      <p className="mt-4 text-xs text-muted-foreground">
        Dica: faça uma pergunta por vez e seja específico (curso, tipo de trabalho). Use 👍 e 👎 nas respostas para me ajudar a melhorar.
        Só respondo sobre pesquisa acadêmica; outros assuntos serão recusados.
      </p>
    </section>

    <div className="w-full max-w-lg space-y-3">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-center mb-4">
        Perguntas sugeridas
      </p>
      <div className="grid gap-2">
        {[
          { icon: "📚", text: "Como fazer uma referência ABNT completa?" },
          { icon: "🔬", text: "Explique o método científico" },
          { icon: "📝", text: "Diferença entre resumo e abstract" },
          { icon: "📋", text: "Estrutura padrão de um TCC" },
        ].map((item, i) => (
          <button
            key={i}
            onClick={() => onSelectQuery(item.text)}
            aria-label={`Sugerir pergunta: ${item.text}`}
            className="flex items-center gap-3 p-4 rounded-xl bg-card border border-border hover:border-primary/50 hover:bg-secondary/50 transition-all duration-200 text-left group focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary"
          >
            <span className="text-xl" aria-hidden="true">{item.icon}</span>
            <span className="text-sm text-foreground group-hover:text-primary transition-colors">
              {item.text}
            </span>
          </button>
        ))}
      </div>
    </div>

    <div className="flex items-center gap-2 mt-10 text-xs text-muted-foreground">
      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
      <span>Conectado ao servidor</span>
    </div>
  </div>
);

const EmptyState = () => (
  <div className="flex flex-col items-center justify-center h-full py-16 px-4">
    <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-6">
      <svg className="w-8 h-8 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    </div>
    <h3 className="text-lg font-semibold text-foreground mb-2">Inicie uma conversa</h3>
    <p className="text-sm text-muted-foreground text-center max-w-sm">
      Digite uma mensagem abaixo para começar a conversar com o assistente de pesquisa.
    </p>
  </div>
);

export function ChatInterface({
  sessionId,
  authToken,
  onUnauthorized,
  initialMessages = [],
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState("");
  const [loadingStatus, setLoadingStatus] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [feedbacks, setFeedbacks] = useState<Record<string, "like" | "dislike">>({});
  const [showWarningModal, setShowWarningModal] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(true);

  // Font Size Accessibility State (persisted in localStorage)
  const [fontSizeIndex, setFontSizeIndex] = useState<number>(1); // Default: 100% (15px)

  useEffect(() => {
    try {
      const savedIdx = localStorage.getItem("nexus_chat_font_idx");
      if (savedIdx !== null) {
        const parsed = parseInt(savedIdx, 10);
        if (!isNaN(parsed) && parsed >= 0 && parsed < FONT_SIZE_LEVELS.length) {
          setFontSizeIndex(parsed);
        }
      }
    } catch {
      // Ignore localStorage errors
    }
  }, []);

  const changeFontSize = useCallback((newIdx: number) => {
    const clamped = Math.max(0, Math.min(FONT_SIZE_LEVELS.length - 1, newIdx));
    setFontSizeIndex(clamped);
    try {
      localStorage.setItem("nexus_chat_font_idx", String(clamped));
    } catch {
      // Ignore
    }
  }, []);

  const increaseFontSize = useCallback(() => {
    changeFontSize(fontSizeIndex + 1);
  }, [changeFontSize, fontSizeIndex]);

  const decreaseFontSize = useCallback(() => {
    changeFontSize(fontSizeIndex - 1);
  }, [changeFontSize, fontSizeIndex]);

  const resetFontSize = useCallback(() => {
    changeFontSize(1); // 100% (15px)
  }, [changeFontSize]);

  const currentFontSizePx = FONT_SIZE_LEVELS[fontSizeIndex]?.px || 15;

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    setShowWarningModal(true);
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, []);

  const userQuestions = useMemo(
    () => messages.filter((m) => m.role === "user"),
    [messages]
  );

  const scrollToMessage = useCallback((id: string) => {
    const el = messagesContainerRef.current?.querySelector(`[data-message-id="${id}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("ring-2", "ring-primary/50", "rounded-2xl");
      setTimeout(() => el.classList.remove("ring-2", "ring-primary/50", "rounded-2xl"), 1500);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleLike = useCallback((id: string) => {
    setFeedbacks((prev) => {
      const nextVal = prev[id] === "like" ? undefined : "like";
      fetch(`${API_BASE_URL}/chat/message/${id}/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({ feedback: nextVal || null }),
      }).catch(console.error);
      return {
        ...prev,
        [id]: nextVal,
      };
    }) as any;
  }, [authToken]);

  const handleDislike = useCallback((id: string) => {
    setFeedbacks((prev) => {
      const nextVal = prev[id] === "dislike" ? undefined : "dislike";
      fetch(`${API_BASE_URL}/chat/message/${id}/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({ feedback: nextVal || null }),
      }).catch(console.error);
      return {
        ...prev,
        [id]: nextVal,
      };
    }) as any;
  }, [authToken]);

  const handleCopy = useCallback((text: string) => {
    navigator.clipboard.writeText(text);
  }, []);

  const handlePasteToInput = useCallback((text: string) => {
    setInput(text);
    textareaRef.current?.focus();
  }, []);

  const processMessage = useCallback(
    async (userMessage: string) => {
      const userMsg: ChatMessage = {
        id: `msg_${Date.now()}`,
        role: "user",
        content: userMessage,
        timestamp: new Date(),
      };

      const assistantMsg: ChatMessage = {
        id: `msg_${Date.now()}_assistant`,
        role: "assistant",
        content: "",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsLoading(true);
      setLoadingStatus("Processando...");
      setStreamingMessageId(assistantMsg.id);
      setInput("");
      scrollToBottom();

      try {
        const response = await fetch(`${API_BASE_URL}/chat/${sessionId}`, {
          method: "POST",
          headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
          body: JSON.stringify({ user_message: userMessage }),
        });

        if (response.status === 401) {
          onUnauthorized?.();
          throw new Error("Sessão expirada. Entre novamente.");
        }
        if (!response.ok || !response.body) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          let eolIndex: number;
          while ((eolIndex = buffer.indexOf("\n\n")) !== -1) {
            const chunk = buffer.slice(0, eolIndex).trim();
            buffer = buffer.slice(eolIndex + 2);

            if (chunk.startsWith("data:")) {
              const jsonString = chunk.slice(5).trim();
              try {
                const payload: SSEPayload = JSON.parse(jsonString);

                if (payload.type === "status") {
                  setLoadingStatus(payload.status || null);
                } else if (payload.type === "token") {
                  setLoadingStatus(null);
                  const tokenContent = payload.content || "";
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMsg.id
                        ? { ...msg, content: msg.content + tokenContent }
                        : msg
                    )
                  );
                } else if (payload.type === "error") {
                  setLoadingStatus(`Erro: ${payload.error}`);
                }
              } catch {
                // Skip malformed JSON
              }
            }
          }
        }
      } catch (error) {
        console.error("Error:", error);
        setLoadingStatus("Erro na conexão");
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsg.id
              ? { ...msg, content: "Desculpe, ocorreu um erro ao processar sua mensagem." }
              : msg
          )
        );
      } finally {
        setIsLoading(false);
        setLoadingStatus(null);
        setStreamingMessageId(null);
      }
    },
    [sessionId, authToken, onUnauthorized, streamingMessageId, scrollToBottom]
  );

  return (
    <div className="flex h-full">
    <div className="flex flex-col h-full flex-1 min-w-0">
      {/* Top Header Accessibility & Font Size Bar */}
      <div className="px-4 py-2 border-b border-border bg-card/60 backdrop-blur-sm flex items-center justify-between gap-3 sticky top-0 z-20">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-bold text-foreground">Orientador Virtual</span>
          <span className="text-[10px] text-muted-foreground hidden sm:inline">• Metodologia Científica & ABNT</span>
        </div>

        <button
          type="button"
          onClick={() => setIsHistoryOpen((v) => !v)}
          title={isHistoryOpen ? "Ocultar histórico de perguntas" : "Mostrar histórico de perguntas"}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
        >
          <FiClock className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Histórico</span>
          {isHistoryOpen ? <FiChevronsRight className="w-3 h-3" /> : <FiChevronsLeft className="w-3 h-3" />}
        </button>

        {/* Font Size Toolbar */}
        <div className="flex items-center gap-1 bg-muted/60 p-1 rounded-xl border border-border shadow-xs">
          <span className="text-[10px] text-muted-foreground font-semibold px-1.5 hidden md:inline-flex items-center gap-1">
            <FiType className="w-3 h-3 text-primary" /> Fonte:
          </span>
          <button
            type="button"
            onClick={decreaseFontSize}
            disabled={fontSizeIndex <= 0}
            title="Diminuir tamanho da fonte (A-)"
            aria-label="Diminuir tamanho da fonte"
            className="flex items-center gap-0.5 px-2 py-1 rounded-lg text-xs font-bold text-muted-foreground hover:text-foreground hover:bg-background transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <FiZoomOut className="w-3 h-3" />
            <span>A-</span>
          </button>
          <span className="text-[11px] font-mono font-bold text-primary px-1.5 min-w-[42px] text-center" title={`Nível: ${FONT_SIZE_LEVELS[fontSizeIndex].name}`}>
            {FONT_SIZE_LEVELS[fontSizeIndex].label}
          </span>
          <button
            type="button"
            onClick={increaseFontSize}
            disabled={fontSizeIndex >= FONT_SIZE_LEVELS.length - 1}
            title="Aumentar tamanho da fonte (A+)"
            aria-label="Aumentar tamanho da fonte"
            className="flex items-center gap-0.5 px-2 py-1 rounded-lg text-xs font-bold text-muted-foreground hover:text-foreground hover:bg-background transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>A+</span>
            <FiZoomIn className="w-3 h-3" />
          </button>
          {fontSizeIndex !== 1 && (
            <button
              type="button"
              onClick={resetFontSize}
              title="Redefinir para tamanho padrão (100%)"
              className="px-1.5 py-1 text-[10px] text-muted-foreground hover:text-foreground hover:bg-background transition-all rounded ml-0.5 flex items-center gap-1"
            >
              <FiRotateCcw className="w-2.5 h-2.5" />
              <span className="hidden sm:inline">Padrão</span>
            </button>
          )}
        </div>
      </div>

      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-6 scrollbar-thin">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 && !isLoading ? (
            <WelcomeScreen onSelectQuery={processMessage} />
          ) : (
            <div className="space-y-6">
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  fontSizePx={currentFontSizePx}
                  isStreaming={message.id === streamingMessageId}
                  feedback={feedbacks[message.id]}
                  onLike={handleLike}
                  onDislike={handleDislike}
                  onCopy={handleCopy}
                  onPasteToInput={handlePasteToInput}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {loadingStatus && (
        <div className="px-4 py-3 border-t border-border bg-muted/30">
          <div className="max-w-3xl mx-auto">
            <StatusBadge status={loadingStatus} />
          </div>
        </div>
      )}

      <div className="border-t border-border bg-card px-4 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-3 p-1.5 bg-background rounded-2xl border border-border focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/50 transition-all">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPaste={handlePaste}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (input.trim()) processMessage(input);
                }
              }}
              placeholder="Digite sua mensagem..."
              rows={1}
              disabled={isLoading}
              aria-label="Mensagem do chat"
              className="flex-1 resize-none bg-transparent px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50 max-h-40 scrollbar-thin"
              style={{ minHeight: "52px", maxHeight: "160px", fontSize: `${Math.max(14, currentFontSizePx - 1)}px` }}
            />

            <button
              onClick={() => input.trim() && processMessage(input)}
              disabled={!input.trim() || isLoading}
              aria-label="Enviar mensagem"
              className={`
                flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center
                transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/40
                ${!input.trim() || isLoading
                  ? "bg-muted text-muted-foreground cursor-not-allowed"
                  : "bg-primary text-primary-foreground hover:bg-primary/90 active:scale-95 shadow-lg shadow-primary/25"
                }
              `}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>

          <div className="flex items-center justify-between mt-3 px-1">
            <p className="text-xs text-muted-foreground">
              Pressione <kbd className="px-1.5 py-0.5 rounded bg-muted text-xs font-medium">Enter</kbd> para enviar
            </p>
            <p className="text-xs text-muted-foreground">
              Powered by JupiterClass
            </p>
          </div>
        </div>
      </div>
    {/* Copy-Paste Warning Modal */}
    {showWarningModal && (
      <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 shadow-2xl text-center space-y-4 animate-in fade-in zoom-in duration-200">
          <div className="w-14 h-14 rounded-full bg-amber-500/10 flex items-center justify-center mx-auto text-amber-500 border border-amber-500/20">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-xl font-bold text-foreground">
            Valorizamos a sua escrita! ✍️
          </h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            O objetivo do **JupiterClass** é ajudar você a desenvolver suas próprias ideias ativamente. Copiar e colar textos prontos prejudica seu aprendizado e seu rigor acadêmico.
          </p>
          <p className="text-xs text-primary font-semibold bg-primary/10 py-2 rounded-lg">
            Vamos construir esse texto juntos, parágrafo por parágrafo!
          </p>
          <button
            type="button"
            onClick={() => setShowWarningModal(false)}
            className="w-full py-3 bg-primary hover:bg-primary/95 text-primary-foreground rounded-xl font-semibold active:scale-98 transition-all shadow-md"
          >
            Compreendi e vou escrever
          </button>
        </div>
      </div>
    )}
    </div>

    {/* Histórico compacto e numerado das perguntas do aluno */}
    {isHistoryOpen && (
      <aside className="hidden md:flex w-60 flex-shrink-0 flex-col border-l border-border bg-card/40">
        <div className="px-3 py-2.5 border-b border-border flex items-center gap-1.5">
          <FiClock className="w-3.5 h-3.5 text-primary" />
          <span className="text-xs font-bold text-foreground">Suas perguntas</span>
          <span className="ml-auto text-[10px] text-muted-foreground">{userQuestions.length}</span>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin py-2 px-2 space-y-1">
          {userQuestions.length === 0 ? (
            <p className="text-[11px] text-muted-foreground px-2 py-4 text-center leading-relaxed">
              Suas perguntas aparecerão aqui, numeradas, à medida que você conversar.
            </p>
          ) : (
            userQuestions.map((q, idx) => (
              <button
                key={q.id}
                onClick={() => scrollToMessage(q.id)}
                title={q.content}
                className="w-full flex items-start gap-2 px-2 py-1.5 rounded-lg text-left hover:bg-muted transition-colors group"
              >
                <span className="flex-shrink-0 w-4 h-4 mt-0.5 rounded-full bg-primary/10 text-primary text-[9px] font-bold flex items-center justify-center group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                  {idx + 1}
                </span>
                <span className="text-[11px] text-muted-foreground group-hover:text-foreground leading-snug line-clamp-2">
                  {q.content}
                </span>
              </button>
            ))
          )}
        </div>
      </aside>
    )}
    </div>
  );
}
