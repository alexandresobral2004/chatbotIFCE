"use client";

import { FormEvent, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface AuthSession {
  token: string;
  user: { id: string; nome: string; email: string };
}

export function AuthForm({ onAuthenticated }: { onAuthenticated: (s: AuthSession) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const isRegister = mode === "register";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(isRegister ? { nome, email, senha } : { email, senha }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Não foi possível continuar. Tente novamente.");
      onAuthenticated(data as AuthSession);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha de conexão.");
    } finally {
      setLoading(false);
    }
  };

  const field = "w-full h-11 rounded-md border border-input bg-background px-3 text-base focus:outline-none focus:ring-2 focus:ring-ring";

  return (
    <main className="min-h-screen flex items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-lg border bg-card p-6" aria-labelledby="auth-title">
        <p className="text-sm font-semibold text-primary">Methodology.ia</p>
        <h1 id="auth-title" className="text-xl font-semibold">{isRegister ? "Criar conta" : "Entrar"}</h1>

        {isRegister && (
          <div className="space-y-1">
            <label htmlFor="nome" className="text-sm font-medium">Nome</label>
            <input id="nome" className={field} value={nome} onChange={(e) => setNome(e.target.value)} autoComplete="name" required />
          </div>
        )}
        <div className="space-y-1">
          <label htmlFor="email" className="text-sm font-medium">E-mail</label>
          <input id="email" type="email" className={field} value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
        </div>
        <div className="space-y-1">
          <label htmlFor="senha" className="text-sm font-medium">Senha</label>
          <input
            id="senha" type="password" className={field} value={senha} onChange={(e) => setSenha(e.target.value)}
            autoComplete={isRegister ? "new-password" : "current-password"} minLength={isRegister ? 8 : undefined} required
          />
          {isRegister && <p className="text-xs text-muted-foreground">Mínimo de 8 caracteres.</p>}
        </div>

        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}

        <button type="submit" disabled={loading} className="w-full h-11 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-60">
          {loading ? "Aguarde..." : isRegister ? "Criar conta" : "Entrar"}
        </button>
        <button type="button" className="w-full text-sm underline" onClick={() => { setMode(isRegister ? "login" : "register"); setError(""); }}>
          {isRegister ? "Já tenho conta" : "Criar uma conta"}
        </button>
      </form>
    </main>
  );
}
