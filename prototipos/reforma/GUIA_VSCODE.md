# Abrir as demos no VS Code — Windows

A demo é um estudo com dados inventados. Não é necessário abrir o executável, fazer login ou copiar seu banco. Ela não grava vendas nem sincroniza. A versão instalada continua independente.

## 1. Obter a frente de estudo uma única vez

No terminal PowerShell do VS Code, escolha uma pasta para guardar **outra cópia** do projeto, fora da pasta do programa instalado. Por exemplo:

```powershell
cd D:\Feira2026
git clone --branch reforma/estudo-interface --single-branch https://github.com/SilvioCf27/Programa-de-Vendas.git Gestao-da-Feira-Estudo
cd Gestao-da-Feira-Estudo
code .
```

Se `code` não for reconhecido, use **Arquivo → Abrir Pasta** no VS Code e abra `Gestao-da-Feira-Estudo`. Não é preciso reinstalar o Git ou baixar ZIP a cada edição.

Se essa cópia de estudo já existir, abra-a e vá para a etapa seguinte. Seu clone antigo e seu executável não precisam ser movidos ou substituídos.

## 2. Preparar o Python uma única vez

Na raiz dessa cópia, crie um ambiente separado. O exemplo usa Python 3.13 x64:

```powershell
py -3.13 -m venv .venv-estudo
.\.venv-estudo\Scripts\python.exe -m pip install -r prototipos/reforma/requirements.txt
```

Se não tiver o Python 3.13, confira as versões instaladas com `py -0p`. Python 3.11 a 3.13 pode executar as demos; o estudo aqui foi verificado com 3.13. Use, por exemplo, `py -3.11 -m venv .venv-estudo` se essa for sua versão disponível. Não é preciso ativar o ambiente pelo PowerShell.

Para a demo Tkinter sozinha não é necessário instalar os requisitos: ela usa a biblioteca padrão. PySide6 precisa da instalação acima. Caso apareça `No module named tkinter`, modifique a instalação do Python no Windows e habilite Tcl/Tk.

## 3. Rodar pelo terminal ou pelo botão de execução

Pelo terminal:

```powershell
.\.venv-estudo\Scripts\python.exe prototipos/reforma/tkinter_demo.py
```

Feche a janela e abra a outra:

```powershell
.\.venv-estudo\Scripts\python.exe prototipos/reforma/pyside_demo.py
```

Pelo VS Code:

1. Instale as extensões Python e Python Debugger, da Microsoft, se ainda não estiverem instaladas.
2. Use `Ctrl+Shift+P` → **Python: Select Interpreter** → selecione `.venv-estudo\Scripts\python.exe`. Se necessário, use **Enter interpreter path** para localizá-lo.
3. Abra **Executar e Depurar** (`Ctrl+Shift+D`).
4. Selecione **Estudo visual — Tkinter** ou **Estudo visual — PySide6** e pressione `F5`.

A opção **Gestão da Feira** já existente executa o aplicativo real; para esta avaliação use as opções **Estudo visual**. Não execute `main.py` para abrir a demo.

## 4. Receber os próximos ajustes

Feche a demo. No terminal, dentro de `Gestao-da-Feira-Estudo`:

```powershell
git status --short --branch
git pull --ff-only origin reforma/estudo-interface
```

Abra novamente a demo. **Fechar e abrir o VS Code sozinho não baixa as atualizações.** O `git pull` faz isso. Se houver alterações suas ou erro no comando, envie a mensagem antes de tentar forçar ou descartar arquivos. Reinstale dependências somente se o arquivo de requisitos mudar.

## O que observar e o que ainda falta

- Abra Vendas, Análises e Finanças; maximize e restaure a janela.
- Observe bordas, margens internas, alinhamento, leitura, espaço da lista e proporção entre conteúdo e cartão. Anote resolução e escala do Windows para compararmos.
- Em Finanças, altere o tipo de período e clique em Consultar; selecione uma linha, visite outra área e retorne. O exemplo tem datas fixas de outubro de 2026, não seu mês atual.
- As ajudas e os detalhes demonstrativos funcionam. Cadastro, edição, exclusão, exportação, comparação A/B e configurações ainda exibem avisos de posicionamento. Isso é uma limitação da demo, não uma regressão do aplicativo.
- Vendas e Análises estão mais esquemáticas que Finanças. Não representam o acabamento final nem todos os formulários.
- As imagens do GitHub foram capturadas em Linux. A avaliação no seu Windows ainda é necessária; não afirmamos equivalência de fontes e escalas sem essa conferência.

Para enviar feedback, use: **tela → elemento → problema → resultado desejado**, acompanhado de imagem quando possível. Exemplo: “Finanças → cartão Despesas → muito espaço após o número → cartão compacto, sem reduzir o valor”.
