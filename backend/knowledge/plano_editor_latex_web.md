# Plano: Editor Web Colaborativo para Escrita Acadêmica (estilo Overleaf)

**Data:** 30/08/2026
**Objetivo:** Levantamento dos padrões de escrita e da tecnologia usados pelo Overleaf, avaliação técnica e planejamento de requisitos para construir um editor equivalente.

---

## 1. Levantamento: padrões de escrita suportados pelo Overleaf

O Overleaf é uma referência consolidada para escrita acadêmica online. Os padrões que ele suporta definem o que um editor equivalente precisa cobrir.

### 1.1 Padrões de escrita e formatação

| Padrão | Como o Overleaf lida |
|---|---|
| **LaTeX / pdfLaTeX / XeLaTeX / LuaLaTeX** | Motores de compilação selecionáveis por projeto |
| **BibTeX / Biber + `.bib`** | Gerenciamento de referências bibliográficas, múltiplos estilos |
| **Classes e pacotes** | `.cls`, `.sty`, `.bst`; TeX Live completo (texlive-full) com milhares de pacotes |
| **Templates acadêmicos** | Galeria com IEEE, ACM, Elsevier, Springer, ABNT/NBR, teses/dissertações de universidades (incl. IFCE) |
| **Formatos de saída** | PDF (principal), também `.dvi`, `.synctex.gz`, `.log`, `.aux` |
| **Compilação múltipla** | Executa sequências automáticas (ex.: `pdflatex → bibtex → pdflatex ×2`) conforme necessário |
| **SyncTeX** | Navegação bidirecional entre código-fonte e PDF |
| **Figuras e recursos** | Imagens, `.bib`, classes, arquivos anexos em árvore de projeto |

### 1.2 Workflow de escrita colaborativa

| Recurso | Descrição |
|---|---|
| Edição em tempo real | Vários autores editando o mesmo `.tex` simultaneamente |
| Compartilhamento | Convites por e-mail, permissões de leitura/edição, links |
| Comentários | Anotações em trechos do texto, menções a colaboradores |
| Histórico de versões | Versões nomeadas, comparação (diff) visual |
| Track changes | Controle de alterações com aceite/recusa |
| Rich text (Visual Editor) | Modo visual WYSIWYG para usuários sem LaTeX |
| Logs de compilação | Erros/warnings clicáveis que levam à linha do código |
| Chat | Comunicação entre colaboradores no projeto |
| Auto-compile | Recompilação automática ao salvar (ou manual) |

---

## 2. Avaliação da tecnologia usada pelo Overleaf

### 2.1 Arquitetura (microserviços)

O Overleaf roda como um conjunto de microserviços em Node.js, orquestrados dentro de containers (imagem `sharelatex`) com o gerenciador de processos `runit`:

| Serviço | Responsabilidade |
|---|---|
| `web` | API HTTP (Express), páginas, projetos, contas, sessões |
| `real-time` | WebSockets (socket.io), autenticação e retransmissão de edições |
| `document-updater` | Aplica operações de edição, OT, cache em Redis, persistência |
| `clsi` | Serviço de compilação LaTeX (gera o PDF) |
| `filestore` | Armazenamento de arquivos binários |
| `docstore` | Persistência de documentos (MongoDB) |
| `project-history` | Histórico de versões e blobs |
| `track-changes` | Histórico granular de edições |
| `spelling` / `chat` / `contacts` | Correção ortográfica, chat, contatos |

**Bancos de dados:** MongoDB (persistência) + Redis (estado ao vivo dos documentos, pub/sub para colaboração multi-nó, cache). Em escala horizontal: PostgreSQL (alguns metadados) e S3-compatível para arquivos/histórico.

### 2.2 Colaboração em tempo real

- **Operational Transformation (OT)** — estilo ShareJS: operações `{insert, delete, comment}` com posições; transformação de operações concorrentes para convergência.
- Diffs calculados com **diff-match-patch** e convertidos em operações ShareJS.
- **WebSockets** via socket.io, com fallback a polling.
- **Redis pub/sub** para sincronizar entre múltiplas instâncias do servidor.
- Estado "quente" do documento em Redis; persistência eventual no MongoDB (flush após inatividade).

### 2.3 Compilação LaTeX (o coração técnico)

1. O `web` envia o pedido de compilação com hash da árvore de arquivos ("project state").
2. O `clsi` grava os arquivos do projeto em disco, baixa binários do `filestore` (se necessário) e roda o motor.
3. **Modos de sync:** `full` (reescreve tudo) e `incremental` (aproveita cache; se o hash divergir, responde 409 e o web refaz com `full`).
4. **Sandbox (Server Pro):** cada compilação roda em um container Docker "irmão" com imagem TeX Live, seccomp restrito, sem rede, sem acesso ao host. A edição Community Edition compila em subprocesso (sem isolamento — inseguro para multi-tenant).
5. Saídas copiadas para diretórios únicos (`build-id`); retenção limitada (últimos N builds). Cache por projeto.
6. Stdout/stderr limitado (~2MB) e timeouts.

### 2.4 Frontend

- **React** (migração de Angular 1), webpack, TypeScript.
- **Editor:** CodeMirror 6 (novo editor de código e Visual Editor). Antes usava ACE.
- **Visualizador PDF:** PDF.js (`pdfjs-dist`) com renderização incremental por página, zoom, posição preservada entre compiles, SyncTeX.
- CSS: LESS/SCSS, layout em painéis redimensionáveis (código | PDF | árvore de arquivos).

### 2.5 Observações importantes

- Código-fonte aberto (AGPL-3.0), monorepo `github.com/overleaf/overleaf`. Originado do ShareLaTeX (CoffeeScript → JS/TS).
- **Limitação da edição CE:** sem sandbox para compilação → isolamento inexistente entre usuários. Não é recomendado para serviço público multi-tenant.

---

## 3. Decisões para construir um editor "daquele jeito"

### 3.1 Fork do Overleaf CE vs. construção própria

**Recomendação: construir uma implementação própria, enxuta, em TypeScript moderno.** Usar o CE apenas como referência de comportamento (benchmark).

- Prós de construir: stack moderna, UI controlada, segurança de compilação do zero, sem dívida técnica legada, sem obrigações AGPL sobre modificações.
- Quando o fork seria melhor: requisito de paridade total de features ou self-hosting imediato, e equipe disposta a manter um codebase grande e antigo.
- Atenção: AGPL exige publicar o código-fonte modificado a quem usa o serviço pela rede; revisar licenças de dependências.

### 3.2 Colaboração: CRDT (Yjs) vs OT

**Recomendação: Yjs (CRDT).** Para implementação nova é a opção moderna: robusto a reconexão/offline, integração madura com CodeMirror 6, sem lógica custom de transformação. Manter **um documento Yjs por arquivo de texto**; metadados (árvore, permissões, raiz) em PostgreSQL. Persistir updates do Yjs e gerar snapshots/compactação periódicas.

OT continua válido apenas se houver compatibilidade com Overleaf (caso de fork).

### 3.3 Stack recomendada

| Camada | Tecnologia |
|---|---|
| Frontend | React + TypeScript + Vite |
| Editor | CodeMirror 6 + pacote de linguagem LaTeX |
| Colaboração | Yjs + Hocuspocus (WebSocket) |
| API | Node.js + TypeScript + Fastify + Zod |
| Banco | PostgreSQL (usuários, projetos, permissões, metadados) |
| Arquivos | Armazenamento S3-compatível |
| Fila | PostgreSQL (fila simples) → BullMQ/Redis se escalar |
| PDF | `pdfjs-dist` (PDF.js) |
| Compilação | Worker dedicado com imagens TeX Live fixas |
| Autenticação | OIDC / provedor gerenciado |
| Deploy | Docker Compose (local); DB/storage gerenciados + hosts de worker (prod) |

**Padrão:** monólito modular (web/API + servidor real-time + worker de compilação), não replicar a topologia de 10 serviços do Overleaf.

### 3.4 Sandbox de compilação

- MVP: **host de worker dedicado** rodando containers rootless: usuário não-root, imagem base read-only, filesystem efêmero, **sem rede**, capabilities reduzidas, seccomp, limites de CPU/memória, timeout e limite de saída, sem acesso ao socket Docker, sem banco.
- Evolução para serviço público: gVisor (melhor isolamento) ou Firecracker (máximo, porém complexo).
- **Regra dura:** compilação em subprocesso sem isolamento (modelo do CE) só para uso interno confiável; nunca para multi-tenant público.

---

## 4. Requisitos

### 4.1 Requisitos funcionais — MVP (Fase 1)

| # | Requisito |
|---|---|
| F1 | Autenticação de usuários e permissões de projeto/membros (leitura/edição) |
| F2 | Criar, importar, exportar, renomear, mover e excluir arquivos (`.tex`, `.bib`, imagens, `.sty`, `.cls`) |
| F3 | Seleção do arquivo raiz do projeto para compilação |
| F4 | Edição LaTeX com CodeMirror 6 (destaque de sintaxe, autocomplete básico) |
| F5 | Autosave com persistência durável |
| F6 | Edição colaborativa em tempo real: cursores e presença |
| F7 | Fila de compilação com cancelamento, timeout e limites de concorrência |
| F8 | Preview de PDF com PDF.js (renderização incremental) |
| F9 | Logs de compilação com erros/warnings clicáveis |
| F10 | Download do PDF e artefatos |
| F11 | Conjunto inicial de templates acadêmicos (ABNT, IEEE, teses, artigos) |
| F12 | Recuperação básica: restaurar última revisão salva |
| F13 | Motores: pdfLaTeX e XeLaTeX; suporte a BibTeX/Biber |
| F14 | Compilação de snapshot imutável do projeto (consistência entre arquivos) |

### 4.2 Requisitos funcionais — Fase 2

| # | Requisito |
|---|---|
| F15 | Histórico de versões nomeadas e diff visual |
| F16 | Comentários, menções e fluxo de revisão |
| F17 | Navegação SyncTeX código ↔ PDF |
| F18 | Import/export via Git |
| F19 | Suporte offline-first |
| F20 | Cache de compilação e diagnóstico avançado de build |
| F21 | Gestor de citações e integrações de referências |
| F22 | SSO, administração enterprise, logs de auditoria |

### 4.3 Requisitos funcionais — Fase 3 (diferencial)

| # | Requisito |
|---|---|
| F23 | Track changes com aceite/recusa |
| F24 | Modo visual (rich text) com round-trip fonte ↔ LaTeX |
| F25 | Paridade ampla de features com Overleaf |

### 4.4 Requisitos não funcionais

| Categoria | Requisito |
|---|---|
| **Segurança** | Compilação isolada; sem execução arbitrária no host; WebSockets autenticados e permissões validadas no servidor; sem `shell-escape`; seccomp + sem rede |
| **Performance** | Autosave < 1s percebido; compilação típica < 30–60s; renderização incremental do PDF |
| **Escalabilidade** | Estado de colaboração em memória/Redis; múltiplas instâncias com pub/sub; fila de compilação justa |
| **Confiabilidade** | Persistência durável (Yjs updates + snapshots), backup/restore testado, recuperação de sessão |
| **Custos** | Quotas de compilação por usuário, limites de artefato, retenção de builds, storage S3 com ciclo de vida |
| **Conformidade** | Revisão de licenças (AGPL, TeX, pacotes, PDF.js, fontes, assets de usuário) |
| **Observabilidade** | Logs estruturados, métricas, tracing, Sentry/OpenTelemetry |

### 4.5 Requisitos de infraestrutura

- Docker Compose (dev/local) e deploy gerenciado (prod)
- PostgreSQL gerenciado, storage S3-compatível, Redis opcional (fila/pub-sub)
- Hosts de worker de compilação separados da aplicação web
- Load balancer com suporte a WebSocket e payloads grandes (POST até 50MB), timeouts de keep-alive ajustados

---

## 5. Riscos e armadilhas de custo

1. **Segurança do compilador** — `shell-escape`, pacotes maliciosos, loops infinitos, estouro de memória/processos, ataque a filesystem/rede. Maior área de risco.
2. **Ilusão de paridade** — editar + PDF é o fácil; colaboração, importação, permissões, histórico, diagnóstico e recuperação são o trabalho real.
3. **Crescimento de storage do CRDT** — planejar snapshots, compactação, IDs de revisão e backup desde o início.
4. **Custo volátil de compilação** — LaTeX é pesado em CPU/memória; quotas, fairness de fila, cache e limite de artefatos são obrigatórios.
5. **Consistência entre arquivos** — compilar snapshots imutáveis, não arquivos vivos em edição.
6. **Autorização WebSocket** — autenticar cada sala e validar permissões no servidor, nunca confiar no front.
7. **Custos de storage** — PDFs, logs, imagens e histórico crescem rápido; definir retenção.
8. **Licenciamento** — AGPL, pacotes TeX, bibliotecas de editor, PDF.js, fontes, uploads de usuários.

---

## 6. Conclusão e próximo passo

Recomenda-se construir um **editor próprio moderno e enxuto**: React + CodeMirror 6 + Yjs/Hocuspocus + PostgreSQL + S3 + PDF.js + workers de compilação isolados, seguindo o escopo MVP da seção 4.1 como primeira entrega.

**Próximo passo sugerido:** validar a decisão de stack (seção 3) com a equipe, detalhar o MVP em épicos/estórias de usuário e prototipar o fluxo principal *editar → compilar → visualizar PDF* ponta a ponta antes de investir em colaboração avançada.