# Padrão JSON para Aulas - JupiterClass

## Estrutura do JSON

```json
{
  "title": "Título da Aula",
  "description": "Descrição breve da aula",
  "blocks": [
    {
      "type": "text",
      "content": "<h1>Título</h1><p>Texto em HTML...</p>"
    },
    {
      "type": "code",
      "language": "python",
      "code": "print('Hello World')"
    }
  ]
}
```

## Tipos de Blocos

### 1. Bloco de Texto
```json
{
  "type": "text",
  "content": "<h1>Título</h1><p>Parágrafo com <strong>negrito</strong> e <em>itálico</em>.</p><ul><li>Item 1</li><li>Item 2</li></ul>"
}
```

**Tags HTML suportadas:**
- `<h1>`, `<h2>`, `<h3>` - Títulos
- `<p>` - Parágrafos
- `<strong>`, `<b>` - Negrito
- `<em>`, `<i>` - Itálico
- `<u>` - Sublinhado
- `<ul>`, `<ol>`, `<li>` - Listas
- `<code>` - Código inline
- `<blockquote>` - Citação
- `<a href="">` - Links

### 2. Bloco de Código
```json
{
  "type": "code",
  "language": "python",
  "code": "def hello():\n    print('Hello World')"
}
```

**Linguagens suportadas:**
- `python` - Python
- `javascript` - JavaScript
- `typescript` - TypeScript
- `java` - Java
- `c` - C
- `cpp` - C++
- `sql` - SQL
- `html` - HTML
- `css` - CSS
- `bash` - Bash/Shell
- `json` - JSON

## Prompt para o Gemini

Copie e cole este prompt no Gemini quando quiser gerar uma aula:

---

**PROMPT PARA GEMINI:**

```
Gere uma aula completa sobre [TEMA DA AULA] no seguinte formato JSON estruturado.

IMPORTANTE:
- Retorne APENAS o JSON, sem texto adicional antes ou depois
- Use HTML válido no campo "content" dos blocos de texto
- Use tags HTML como <h1>, <h2>, <p>, <strong>, <em>, <ul>, <ol>, <li>, <code>
- Para blocos de código, use "type": "code" com a linguagem apropriada
- Alterne entre blocos de texto explicativo e blocos de código quando necessário
- Seja didático e progressivo na explicação

FORMATO JSON OBRIGATÓRIO:

{
  "title": "Título da Aula",
  "description": "Descrição breve",
  "blocks": [
    {
      "type": "text",
      "content": "<h1>Seção 1</h1><p>Explicação...</p>"
    },
    {
      "type": "code",
      "language": "python",
      "code": "código aqui"
    },
    {
      "type": "text",
      "content": "<h2>Seção 2</h2><p>Mais explicação...</p>"
    }
  ]
}

TEMA DA AULA: [INSERIR TEMA AQUI]
```

---

## Exemplo Completo

```json
{
  "title": "Introdução ao Python",
  "description": "Aprenda os fundamentos da linguagem Python",
  "blocks": [
    {
      "type": "text",
      "content": "<h1>O que é Python?</h1><p>Python é uma linguagem de programação <strong>de alto nível</strong>, conhecida por sua <em>simplicidade</em> e <em>legibilidade</em>.</p><p>É amplamente utilizada em:</p><ul><li>Desenvolvimento Web</li><li>Ciência de Dados</li><li>Inteligência Artificial</li><li>Automação</li></ul>"
    },
    {
      "type": "text",
      "content": "<h2>Primeiro Programa</h2><p>Vamos criar nosso primeiro programa em Python. O clássico <code>Hello World</code>:</p>"
    },
    {
      "type": "code",
      "language": "python",
      "code": "# Meu primeiro programa em Python\nprint('Hello, World!')\n\n# Você também pode usar aspas duplas\nprint(\"Hello, World!\")"
    },
    {
      "type": "text",
      "content": "<h2>Variáveis</h2><p>Em Python, você não precisa declarar o tipo da variável. O interpretador identifica automaticamente:</p>"
    },
    {
      "type": "code",
      "language": "python",
      "code": "# Variáveis em Python\nnome = 'Maria'      # String\nidade = 25           # Integer\naltura = 1.65        # Float\nestudante = True     # Boolean\n\n# Exibindo as variáveis\nprint(f'Nome: {nome}')\nprint(f'Idade: {idade}')\nprint(f'Altura: {altura}')\nprint(f'É estudante? {estudante}')"
    },
    {
      "type": "text",
      "content": "<h2>Condicionais</h2><p>Use <code>if</code>, <code>elif</code> e <code>else</code> para tomar decisões:</p>"
    },
    {
      "type": "code",
      "language": "python",
      "code": "idade = 18\n\nif idade < 18:\n    print('Menor de idade')\nelif idade == 18:\n    print('Exatamente 18 anos')\nelse:\n    print('Maior de idade')"
    }
  ]
}
```

## Como Usar

1. **No Gemini**: Cole o prompt acima e substitua [TEMA DA AULA] pelo tema desejado
2. **Copie o JSON**: O Gemini retornará um JSON estruturado
3. **No JupiterClass**: 
   - Vá em "Aulas" → "Nova Aula"
   - Clique no botão "Gemini" no editor de texto
   - Cole o JSON completo
   - O sistema irá reconhecer e criar os blocos automaticamente
4. **Salve**: Clique em "Salvar" para guardar a aula

## Dicas

- O Gemini pode gerar aulas completas com múltiplas seções
- Alterne entre explicação (texto) e exemplos (código)
- Use HTML para formatar o texto (negrito, itálico, listas, etc.)
- Especifique a linguagem correta nos blocos de código
- O sistema suporta até 11 linguagens de programação
