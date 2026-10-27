# Reforma desktop — primeira integração PySide6

A escolha do PySide6 foi aprovada pelo usuário em 27/10/2026, após a comparação técnica. Esta entrega inicia **navegação e Vendas**, primeiro item da Etapa 4 do [plano](../docs/PLANO_REFORMA_DESKTOP.txt), seção 19. Não é uma nova release nem substitui o executável 1.7.1.

![Vendas integrada em banco fictício](imagens/vendas-integrada.png)

## O que já funciona nesta entrada

- Cadastro, edição por ID e cancelamento, com mensagens no formulário. Data repetida é recusada e permite corrigir/continuar sem bloquear a próxima gravação.
- Ano, mês, fechamento por vigência e dias da semana. Não é necessário escolher outro “tipo” para os seletores funcionarem. Alterações ficam pendentes até Aplicar.
- Indicadores e comparação anterior calculados pelos módulos existentes, incluindo registros zerados. A semana atual vai de segunda até hoje e independe do filtro; seus detalhes abrem em janela própria. A virada do dia é conferida a cada minuto.
- Histórico paginado, ordenação numérica/cronológica, seleção da página e exclusão individual/em lote confirmada. O lote é transacional; qualquer registro divergente impede excluir o conjunto. O backup local é verificado antes de alterações; sua falha impede gravar/excluir.
- CSV e Excel pela consulta aplicada completa. Paginação e busca na tabela não reduzem a exportação nem os indicadores. O campo de busca explica esse alcance.
- Navegação conserva a tela de Vendas e um único timer. Não há menu Exportar duplicado.

Os módulos `database/banco.py`, `database/armazenamento.py`, `fechamento.py`, `resumos.py`, `semanas.py`, `preferencias.py` e `exportacao.py` são reutilizados. Não foram alterados. O adaptador `vendas.py` reúne somente a consulta e as ações desta interface; não importa `ProgramFeira.main`, não cria janela Tkinter e não usa os cálculos fictícios da demo.

Os recursos e componentes visuais aprovados continuam compartilhados com `prototipos/reforma`. Essa dependência está explícita e será organizada ao consolidar a interface; não se instanciam a aplicação ou o estado fictício da demo. A captura mostra dados fictícios criados pelo próprio lançador.

## Abrir no VS Code, na cópia de estudo

No terminal PowerShell da pasta **Gestao-da-Feira-Estudo**, já na branch `reforma/estudo-interface`:

```powershell
git pull --ff-only origin reforma/estudo-interface
.\.venv-estudo\Scripts\python.exe -m pip install -r prototipos/reforma/requirements.txt -r requirements.txt
.\.venv-estudo\Scripts\python.exe executar_reforma.py --exemplo
```

Isso abre a implementação funcional Qt em um banco temporário com exemplos. Pode cadastrar, editar, excluir e exportar. **Os testes são descartados ao fechar**, e os seus dados pessoais não são abertos.

Para conservar somente os testes entre execuções, escolha uma pasta nova e separada:

```powershell
.\.venv-estudo\Scripts\python.exe executar_reforma.py --pasta-estudo D:\Feira2026\Dados-Estudo-Qt --exemplo
```

Nas próximas vezes, use o mesmo comando. `--exemplo` só inclui os exemplos se o banco estiver vazio; omita essa opção se quiser começar sem registros. Não a use após apagar todos os testes se não quiser repovoar o banco. A pasta conserva também os backups locais das alterações.

**Não aponte para `%LOCALAPPDATA%\ProgramFeira` nem copie seu banco real.** O lançador recusa a pasta pessoal e pastas ocupadas sem o marcador de estudo. O marcador identifica a pasta criada pelo lançador, não é uma proteção contra alguém que deliberadamente o falsifique. A variável de dados é definida apenas no processo da entrada Qt, antes de importar o banco; o programa instalado continua usando seu caminho normal.

O lançador original `executar.py`, o executável instalado e `noturno_demo.py` continuam funcionando como antes. As demos continuam sendo somente visuais; o novo comando acima é a entrada funcional desta etapa.

## O que ainda não foi migrado

Análises e Finanças têm acessos identificados como integração pendente. Não apresentam dados demonstrativos como se estivessem conectados. Sua prévia completa permanece na demo aprovada, e suas funções reais continuam na versão 1.7.1.

Configurações completas, editor da preferência de abertura, cinco temas, sincronização/sessão, Drive, restauração e atualizador serão integrados na ordem do plano. Esta entrada fica **offline**; os registros de teste não vão para celular ou nuvem. A preferência de abertura existente já é lida quando presente na pasta de estudo. Existe apenas a identidade Noturno nesta fatia.

A aprovação visual não foi reaberta. A integração ainda não representa equivalência completa, estabilidade de uma release, validação manual Windows/DPI/leitor de tela ou teste do atualizador.

## Verificações

Os testes da primeira fatia verificam gravação e backup, falhas, atomicidade do lote, filtros e regras de fechamento, dados zerados, semana, virada do dia, ordenação, seleção/paginação, exportação completa, formulários, janela de 1.000 × 700 sem corte lateral e navegação sem timers duplicados. Cada teste usa diretório temporário; não há conta configurada.

```powershell
.\.venv-estudo\Scripts\python.exe reforma_desktop/validar.py --saida resultado-vendas-qt.json
```

O workflow `reforma-vendas-windows.yml` repete essa suíte e as suítes existentes da aplicação e dos protótipos no Windows, sem gerar release, executável público ou acessar dados pessoais. Os resultados desta entrega serão vinculados abaixo após sua conferência.

Para sua revisão manual: cadastre uma venda fictícia; tente repetir a data e depois corrija; edite e cancele uma edição; aplique mês/ano/fechamento; deixe um filtro pendente e confira que o resumo não muda; selecione/exclua registros; exporte com mais de uma página; visite Análises/Finanças e retorne para Vendas. São verificações da entrada isolada, não do seu banco real.

A próxima integração prevista é **Análises: resultados semanais, comparação A/B e detalhes do período**. Depois, Finanças e configurações/formulários. A entrada estável só será substituída após as verificações previstas nas Etapas 5 e 6.
