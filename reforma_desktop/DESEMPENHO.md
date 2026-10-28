# Etapa 5 — Fluidez do desktop integrado

A etapa foi autorizada após as seis correções da revisão. O objetivo é medir os aplicativos ligados ao núcleo real e remover custos comprovados, mantendo dados corretos. A versão 1.7.1, o banco pessoal e a PWA permanecem preservados. O layout aprovado não foi alterado.

## Método e reprodução

[Medidor](desempenho/medir.py): três repetições por ferramenta/volume, processos novos em ordem alternada, 224 ou 5.000 vendas e 75 ou 1.667 despesas fictícias. Mesmo gerador, hash e total conferidos a cada par; datas relativas ao dia da execução. Preferência Mês atual, Grafite e janela solicitada 1536 × 960. Componentes/fontes próprios dos aplicativos são preservados. Qt exibe a página atual, Tk todas as linhas: é comparação dos produtos, não isolamento do custo dos toolkits.

Abertura inclui importação gráfica, montagem e processamento da primeira exibição; exclui início do interpretador, preparação da base e importações do núcleo usadas para gerá-la. Cache do SO não é limpo. Primeiras visitas são separadas de dez ciclos de retorno sem mudança e da atualização após uma escrita controlada na fixture. Todas e repetição leem o banco novamente. SQL é cronometrado separadamente. Partes instrumentadas podem se sobrepor; não somar.

RSS é memória residente, não tamanho instalado. O crescimento após dez ciclos aquecidos é separado da carga de outras consultas. O indicador de pulso usa callbacks de 10 ms bombeados pelo ensaio; seus intervalos não representam latência de cada clique. Não há conta, sessão ou Drive configurados, e rede é bloqueada. Dados e operações financeiras são conferidos contra o núcleo. A escrita de invalidação não mede cadastro ou backup.

```powershell
.\.venv-estudo\Scripts\python.exe reforma_desktop/desempenho/medir.py --saida desempenho-local.json
```

Requer sessão gráfica, dependências do estudo e SQLite compatível. O medidor sempre cria/remove sua própria base, sem opção para abrir um banco existente. [Workflow Windows](../.github/workflows/reforma-desempenho-windows.yml): a referência `18592c2` é aberta em worktree separado e recebe somente uma cópia do mesmo medidor; os aplicativos dessa referência não são editados. Antes/depois rodam na mesma VM e os relatórios são publicados em uma branch de evidências, sem executável.

## Otimizações e segurança dos resultados

O piloto local identificou leitura duplicada da base completa para o resumo semanal e formatação repetida de todas as linhas da tabela. A consulta completa agora compartilha sua leitura com a semana dentro do mesmo comando. Consultas filtradas preservam a semana independente.

A tabela guarda somente datas/textos/chaves da consulta aplicada, pela tupla inteira do registro. Busca e ordenação reaproveitam essa apresentação. Uma mudança no valor gera outra entrada; exclusão e mudança de recorte descartam entradas antigas. Aplicar e atualização continuam lendo o banco: nenhum prazo de cache esconde sincronização ou edição externa. [Cinco testes novos](tests/test_fluidez_qt.py) verificam esses caminhos, além da regressão existente.

## Resultados

Coletas completas e validação nativa em andamento. Resultados individuais e tabelas serão registrados após a conferência, sem usar o piloto de uma repetição como resultado definitivo.

## Limitações e sequência

Ensaios de curta duração em máquinas de teste não garantem ausência de vazamento, desempenho do PC do usuário, latência autenticada de Supabase/Drive ou comportamento após dias de uso. DPI real, leitores de tela, integrações reais e pacote/atualização continuam pendentes. A Etapa 6 original deve validar esses pontos e a equivalência antes da publicação aprovada da 2.0. Nenhum executável é gerado nesta etapa.
