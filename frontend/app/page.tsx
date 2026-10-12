"use client";

import { useEffect, useMemo, useState } from "react";
import { ChatInterface } from "@/components/chat";
import { AuthForm, AuthSession } from "@/components/auth/AuthForm";

const TOKEN_KEY = "chat_token";

/**
 * Widget do chat, feito para ser embutido por iframe no sistema principal.
 * Sem token, mostra login/cadastro próprios. O token (JWT) também pode chegar no fragmento da URL (#token=...), que não vai para logs de servidor,
 * ou por postMessage ({ type: "chat-token", token }) quando o token é renovado.
 */
export default function ChatWidget() {
  const sessionId = useMemo(() => crypto.randomUUID(), []);
  const [token, setToken] = useState<string | undefined>(undefined);

  useEffect(() => {
    const saved = sessionStorage.getItem(TOKEN_KEY);
    if (saved) setToken(saved);
    const fromHash = new URLSearchParams(window.location.hash.slice(1)).get("token");
    if (fromHash) {
      setToken(fromHash);
      history.replaceState(null, "", window.location.pathname);
    }
    const allowed = process.env.NEXT_PUBLIC_PARENT_ORIGIN;
    const onMessage = (e: MessageEvent) => {
      if (allowed && e.origin !== allowed) return;
      if (e.data?.type === "chat-token" && typeof e.data.token === "string") setToken(e.data.token);
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  const onAuthenticated = (s: AuthSession) => {
    sessionStorage.setItem(TOKEN_KEY, s.token);
    setToken(s.token);
  };

  const logout = () => {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(undefined);
  };

  if (!token) return <AuthForm onAuthenticated={onAuthenticated} />;

  return (
    <main className="h-screen">
      <ChatInterface sessionId={sessionId} authToken={token} onUnauthorized={logout} />
    </main>
  );
}
