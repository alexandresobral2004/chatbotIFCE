# Como Usar a Importação do Gemini

## Visão Geral

O JupiterClass agora permite criar aulas completas usando o Gemini AI e importá-las diretamente no sistema. O processo é simples: gere a aula no Gemini, copie o JSON retornado e importe no editor de aulas.

## Passo a Passo

### 1. Acessar o Prompt do Gemini

1. Faça login no JupiterClass
2. Vá em **Aulas** no menu lateral
3. Clique em **"+ Nova Aula"**
4. No editor, clique no botão azul **"Prompt Gemini"** no canto superior direito

### 2. Copiar e Usar o Prompt

1. No modal que abrir, clique no botão **"Copiar Prompt"** (canto superior direito do textarea)
2. O prompt será copiado para sua área de transferência
3. Abra o [Gemini](https://gemini.google.com) em uma nova aba
4. Cole o prompt no Gemini
5. **Importante:** Substitua `[INSERIR TEMA AQUI]` pelo tema da sua aula
6. Envie o prompt e aguarde a resposta

### 3. Copiar o JSON Retornado

O Gemini retornará um JSON estruturado como este:

```json
{
  "title": "Introdução ao Python",
  "description": "Aprenda os fundamentos da linguagem Python",
  "blocks": [
    {
      "type": "text",
      "content": "<h1>O que é Python?</h1><p>Python é uma linguagem de programação...</p>"
    },
    {
      "type": "code",
      "language": "python",
      "code": "print('Hello World')"
    }
  ]
}
```

**Copie todo o JSON retornado pelo Gemini.**

### 4. Importar no JupiterClass

1. Volte ao editor de aulas no JupiterClass
2. Clique no botão verde **"Importar Gemini"**
3. Cole o JSON no textarea
4. Clique em **"Importar e Organizar"**
5. O sistema irá:
   - Preencher automaticamente o título
   - Preencher a descrição
   - Criar todos os blocos de texto e código
   - Aplicar a formatação correta

### 5. Revisar e Salvar

1. Revise o conteúdo importado
2. Faça edições se necessário:
   - Reordene blocos usando as setas ↑ ↓
   - Edite texto nos blocos de texto
   - Edite código nos blocos de código
   - Adicione novos blocos se precisar
3. Clique em **"Salvar"** para guardar a aula

## Estrutura do JSON

O JSON deve seguir esta estrutura:

```json
{
  "title": "string - Título da aula",
  "description": "string - Descrição breve",
  "blocks": [
    {
      "type": "text",
      "content": "string - HTML com o conteúdo do texto"
    },
    {
      "type": "code",
      "language": "string - Linguagem de programação",
      "code": "string - Código fonte"
    }
  ]
}
```

### Tipos de Blocos

**Bloco de Texto:**
- `type`: sempre `"text"`
- `content`: HTML formatado (suporta `<h1>`, `<h2>`, `<p>`, `<strong>`, `<em>`, `<ul>`, `<ol>`, `<li>`, `<code>`, etc.)

**Bloco de Código:**
- `type`: sempre `"code"`
- `language`: Linguagem de programação (python, javascript, typescript, java, c, cpp, sql, html, css, bash, json)
- `code`: Código fonte

## Dicas

### Prompt Eficaz

Para obter melhores resultados do Gemini:
- Seja específico sobre o tema
- Indique o nível de dificuldade (iniciante, intermediário, avançado)
- Especifique se quer exemplos práticos
- Mencione se deve incluir exercícios

### Edição Pós-Importação

Após importar, você pode:
- **Reordenar blocos**: Use as setas ↑ ↓ para mover blocos
- **Editar texto**: Clique nos blocos de texto para editar
- **Editar código**: Clique nos blocos de código para modificar
- **Adicionar blocos**: Use os botões "Adicionar Texto" ou "Adicionar Código"
- **Remover blocos**: Clique no ícone de lixeira em cada bloco

### Syntax Highlighting

O sistema suporta syntax highlighting para:
- Python
- JavaScript
- TypeScript
- Java
- C / C++
- SQL
- HTML
- CSS
- Bash
- JSON

### Exportar para PDF

Após criar a aula, você pode exportá-la como PDF:
1. Na lista de aulas, clique no ícone de download 📥
2. Ou na visualização da aula, clique em **"Exportar PDF"**
3. O PDF será gerado com formatação profissional

## Solução de Problemas

### "Não foi possível detectar o JSON"

Se você receber este erro:
- Verifique se copiou todo o JSON
- Certifique-se de que o JSON está completo (começa com `{` e termina com `}`)
- O sistema tenta detectar JSON em diferentes formatos, mas pode falhar se estiver muito mal formatado

### "blocks.map is not a function"

Este erro foi corrigido na última atualização. Se ainda ocorrer:
- Recarregue a página (Ctrl+F5 ou Cmd+Shift+R)
- O sistema agora normaliza automaticamente o campo `blocks`

### Prompt não copiou

Se o botão "Copiar Prompt" não funcionar:
- Verifique se o navegador permite acesso à área de transferência
- Copie manualmente selecionando todo o texto no textarea (Ctrl+A / Cmd+A)

## Exemplo Completo

### Prompt para o Gemini:

```
Gere uma aula completa sobre "Variáveis e Tipos de Dados em Python" no formato JSON estruturado.

IMPORTANTE:
- Retorne APENAS o JSON, sem texto adicional
- Use HTML válido no campo "content"
- Inclua exemplos de código práticos
- Seja didático e progressivo

FORMATO JSON OBRIGATÓRIO:
{
  "title": "Título da Aula",
  "description": "Descrição breve",
  "blocks": [
    {
      "type": "text",
      "content": "<h1>Seção</h1><p>Explicação...</p>"
    },
    {
      "type": "code",
      "language": "python",
      "code": "código aqui"
    }
  ]
}

TEMA: Variáveis e Tipos de Dados em Python
NÍVEL: Iniciante
INCLUA: Exemplos práticos de cada tipo de dado
```

### JSON Retornado pelo Gemini:

```json
{
  "title": "Variáveis e Tipos de Dados em Python",
  "description": "Aprenda sobre variáveis e os principais tipos de dados em Python",
  "blocks": [
    {
      "type": "text",
      "content": "<h1>O que são Variáveis?</h1><p>Variáveis são <strong>espaços na memória</strong> que armazenam dados. Em Python, você não precisa declarar o tipo da variável - o interpretador identifica automaticamente.</p>"
    },
    {
      "type": "code",
      "language": "python",
      "code": "# Exemplos de variáveis\nnome = \"Maria\"      # String\nidade = 25           # Integer\naltura = 1.65        # Float\nestudante = True     # Boolean\n\nprint(f\"Nome: {nome}\")\nprint(f\"Idade: {idade}\")\nprint(f\"Altura: {altura}\")\nprint(f\"É estudante? {estudante}\")"
    },
    {
      "type": "text",
      "content": "<h2>Tipos de Dados Primitivos</h2><p>Python possui vários tipos de dados primitivos:</p><ul><li><strong>int</strong>: Números inteiros (1, 2, 3, -5)</li><li><strong>float</strong>: Números decimais (1.5, 3.14, -2.7)</li><li><strong>str</strong>: Strings/texto (\"Olá\", 'Mundo')</li><li><strong>bool</strong>: Booleanos (True, False)</li></ul>"
    },
    {
      "type": "code",
      "language": "python",
      "code": "# Verificando tipos de dados\nprint(type(10))        # <class 'int'>\nprint(type(3.14))      # <class 'float'>\nprint(type(\"Olá\"))     # <class 'str'>\nprint(type(True))      # <class 'bool'>\n\n# Conversão de tipos\nnumero_str = \"42\"\nnumero_int = int(numero_str)\nprint(numero_int + 8)  # 50"
    }
  ]
}
```

## Recursos Adicionais

- **Documentação do Padrão JSON**: `documents/gemini-lesson-json-pattern.md`
- **Editor de Aulas**: Menu lateral → Aulas → Nova Aula
- **Syntax Highlighting**: Suporte a 11 linguagens de programação
- **Exportação PDF**: Formatação profissional para impressão

## Suporte

Se encontrar problemas ou tiver sugestões:
1. Verifique se está usando a última versão do navegador
2. Limpe o cache do navegador (Ctrl+Shift+Delete)
3. Entre em contato com o suporte técnico

---

**Dica Final**: O Gemini pode gerar aulas completas em segundos! Use e abuse desse recurso para criar conteúdo didático de alta qualidade rapidamente.
