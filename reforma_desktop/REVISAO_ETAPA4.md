# Revisão conjunta da Etapa 4

**Resultado: a Etapa 4 continua aberta.** O usuário confirmou o teste do ensaio do atualizador nesta conversa. Essa confirmação foi registrada sem tratá-la como aprovação da equivalência completa ou da publicação da 2.0.

A revisão percorreu os **30 itens** do inventário e reproduziu **seis lacunas** em dados fictícios. Nesta entrega, foram alterados apenas documentação e ferramentas de verificação. As correções funcionais ficam no próximo passo, antes de encerrar a Etapa 4. A versão 1.7.1, o banco pessoal, as contas, o Drive em uso e a PWA permanecem intactos.

## Lacunas reproduzidas

| Caso | Item | Resultado observado | Correção necessária antes de encerrar a Etapa 4 |
| --- | --- | --- | --- |
| R01 | V01 | Com o editor de ano ainda em `02/01/2`, `hasAcceptableInput()` é falso, mas chamar Salvar grava a última data válida, `02/01/2035`. | Validar o estado do editor antes de ler a data; não gravar usando um valor anterior quando a entrada está incompleta. |
| R02 | A02 | O mesmo estado incompleto em A/B é aceito pelo comando Comparar, que anuncia comparação aplicada usando a data anterior. | Validar os campos de data e preservar o resultado anterior com aviso claro; revisar também o caminho de atualização após mudança dos dados. |
| R03 | V03 | Enter na tabela com foco não emite edição; o duplo clique emite uma vez. A versão Tk liga Return à edição. | Restaurar o atalho sem duplicar abertura por duplo clique e sem trocar o ID da linha/página selecionada. |
| R04 | G02 | Um erro inesperado no trabalhador de nuvem é sanitizado para a tela, mas nenhum registro técnico é criado em `logs`. Não há ligação do Qt a `diagnostico.registrar`. | Reutilizar o diagnóstico seguro para entrada, callbacks e trabalhadores, sem mensagens, valores, senhas ou variáveis no log. |
| R05 | G03 | Uma chamada direta a `Janela.close()` esconde a janela principal enquanto a operação de backup continua ativa. A própria janela de backup impede fechar, mas o caminho principal não tem esse bloqueio. | Unificar a verificação de operações ativas no encerramento e testar as rotas de saída. |
| R06 | V06 | Na primeira consulta da virada do dia, um erro SQLite propaga. Em dois disparos há uma única tentativa: o dia já foi marcado como exibido antes de atualizar. | Confirmar o dia apenas depois da atualização bem-sucedida, registrar a falha e permitir nova tentativa. |

R01/R02 foram reproduzidos mantendo o campo com foco, digitando um ano parcial com eventos Qt e chamando o comando da interface. Isso comprova a falta de validação no comando; **não afirma que todo clique ou Enter nativo no Windows terá o mesmo comportamento**, pois o editor pode corrigir o texto ao perder foco. A tentativa de inserir `31/02` foi normalizada pelo próprio Qt e não foi classificada como falha.

R05 usa uma tarefa controlada de espera iniciada por `Configuracoes.executar`, para observar o bloqueio de encerramento; não faz I/O de backup nesse cenário. Foi reproduzido por chamada direta de fechamento; a janela do backup permaneceu visível. **Não foi observado nem alegado um travamento ou perda de dados.** As rotas nativas do gerenciador de janelas ainda precisam ser verificadas no Windows interativo.

Os dados dessas reproduções existem apenas em pastas temporárias. Não foi tentada restauração, instalação ou conexão sobre seus dados reais.

## Inventário consolidado

Legenda:

- **I**: implementação localizada e coberta por testes controlados; não significa aprovação de release.
- **P**: implementação parcial com lacuna reproduzida nesta revisão.
- **S**: mecanismos exercitados no estudo com transporte/processos simulados; integração real ainda pendente.

Resultado do rastreamento: **20 I, 6 P e 4 S**. DPI, acessibilidade, desempenho comparável e empacotamento são verificações adicionais aplicáveis ao conjunto, nas etapas previstas.

| ID | Estado | Acesso no estudo | Código e evidência principal |
| --- | --- | --- | --- |
| V01 | P | Nova venda; editar/excluir na linha; cancelar formulário | [aplicacao.py](aplicacao.py), `FormularioVenda.gravar`; [testes Vendas](tests/test_vendas_qt.py); R01. |
| V02 | I | Recusa de cadastro repetido e correção posterior | [vendas.py](vendas.py), `ServicoVendas.salvar`; núcleo `banco.py`; testes de duplicidade, edição e backup. |
| V03 | P | Tabela, ordenação, busca, rolagem e ações por linha | [aplicacao.py](aplicacao.py), `ordenar/preencher_tabela`; `noturno_demo.Tabela` preserva duplo clique, mas falta Enter: R03. |
| V04 | I | Filtros de Vendas, Aplicar e Limpar | `sincronizar/consulta_campos/aplicar/limpar`; testes de consulta pendente e período. |
| V05 | I | Seis blocos superiores e comparação anterior | `ServicoVendas.consultar` e `Janela.exibir_resultado`; `resumos.py`, sem instanciar estado fictício da demo. |
| V06 | P | Semana atual independente e detalhes | `semanas.semana_atual`, `detalhes_semana/verificar_dia`; domingo/segunda e virada normal testados, falha transitória descoberta em R06. |
| V07 | I | Configurações → período inicial | [configuracoes.py](configuracoes.py), `salvar_periodo`; `preferencias.py`; persistência e reabertura testadas. |
| V08 | I | Exportar relatório → CSV/Excel | `exportar_consulta`, `exportacao.py`; consulta aplicada inteira, sem recorte pela busca/página; não há menu duplicado. |
| V09 | I | Selecionar página, excluir selecionados e paginação | `Tabela`, `ServicoVendas.excluir`; backup e transação do lote com conferência de todos os registros. |
| A01 | I | Análises → resultado por semana | [analises.py](analises.py), `analisar`; `agrupar_semanas`; [testes Análises](tests/test_analises_qt.py) de recortes, zeros e snapshot completo. |
| A02 | P | Comparar A/B com seletores independentes | [painel_analises.py](painel_analises.py), `SeletorPeriodo.periodo/PainelAnalises.comparar`; tipos e limites testados; R02 cobre entrada parcialmente digitada. |
| A03 | I | Detalhes: pagamentos, dias, vendas e evolução | `criar_detalhe/criar_evolucao`; `tendencias.evolucao`; até 12 períodos, ausência/zero e comparação anterior preservados. |
| A04 | I | Tela própria; identificação da consulta aplicada | `invalidar/atualizar/aviso_pendente_vendas`; tela oculta só refaz quando visitada; A/B independente de Vendas. |
| F01 | I | Finanças → Semana/Mês/Fechamento/Ano | [campos_financeiros.py](campos_financeiros.py), `SeletorFinanceiro`; [financas.py](financas.py), `ConsultaFinanceira`; [testes Finanças](tests/test_financas_qt.py). |
| F02 | I | Indicadores e avisos financeiros | `ServicoFinanceiro.consultar`, `financeiro.resumir`; cobertura parcial/estimativa e ausência de rateio conferidas. |
| F03 | I | Nova despesa, editar compra e excluir lançamentos | [formularios_financeiros.py](formularios_financeiros.py), `FormularioLancamento`; [painel_financas.py](painel_financas.py), `editar/excluir`. |
| F04 | I | Editar por qualquer parcela | `compra_do_lancamento/salvar_lancamento`; total e distribuição de centavos, histórico completo, concorrência e grupo incompleto testados. |
| F05 | I | Data da compra/fatura e registro antigo | `data_iso/FormularioLancamento.dados`; `primeira_fatura`; dia 09, legado, entrada explícita e datas preservadas testados. |
| F06 | I | Taxas da maquininha → carregar semana | `FormularioTaxas`, `ServicoFinanceiro.salvar_taxas`; vazio/zero, dia da venda e sobreposição anual protegidos. |
| F07 | I | Histórico de taxas → novo/editar/excluir ano | `HistoricoTaxas/FormularioAnual`; confirmado/estimado, cobertura e ano existente rechecados. |
| F08 | I | Despesas por semana e histórico de taxas | `despesas_semanas/historico_taxas`, `financeiro.semanas`; lista completa sem recorte de paginação; taxas separadas de despesas. |
| F09 | S | Regra de fechamento em Configurações e Finanças | [configuracao_fechamento.py](configuracao_fechamento.py), `fechamento.py` e cliente existente; [nove testes](tests/test_fechamento_qt.py); serviço somente fictício. |
| F10 | I | Seleção, exclusão em lote e paginação financeira | `Tabela`, `ServicoFinanceiro.excluir`; transação, conferência e exclusão apenas das parcelas selecionadas. |
| G01 | I | Cinco temas para a próxima abertura | [temas.py](temas.py), `preferencias.py`; 15 cenários de abertura e pares de contraste; DPI/leitor de tela completos pendentes. |
| G02 | P | Configurações, versão base e caminho selecionável | `configuracoes.py/painel_atualizacao.py`; falta conexão a [diagnostico.py](../ProgramFeira/diagnostico.py): R04. |
| G03 | P | Backup, verificar/restaurar, Drive e cópia ao fechar | [configuracoes.py](configuracoes.py), [operacoes_backup.py](operacoes_backup.py); [testes Recuperação](tests/test_recuperacao_qt.py); falta guarda de encerramento R05. |
| G04 | S | Sessão, consultas automáticas e conflitos | [conexao_nuvem.py](conexao_nuvem.py), [painel_nuvem.py](painel_nuvem.py); núcleo/DPAPI reais com serviço fictício; [15 testes](tests/test_nuvem_qt.py). |
| G05 | S | Conferir e transferir dados conferidos | `migracao_nuvem.preparar/transferir`; backup, conferência e rechecagem; sem conta ou PWA reais. |
| G06 | S | Atualizações → consulta/preparação/ensaio | [atualizacoes.py](atualizacoes.py), [servico_atualizacao_estudo.py](servico_atualizacao_estudo.py); [dez testes](tests/test_atualizacao_qt.py); pacote/helper fictícios na UI. |
| G07 | I | Cadastro/consulta/exportação e cópia locais | SQLite, CSV/Excel e fallback de indisponibilidade testados sem rede. O Drive confirma arquivo local, não conclusão de envio remoto. |

Os 30 IDs acima preservam o inventário original; ele continua em [MAPA_FUNCOES.txt](../prototipos/reforma/MAPA_FUNCOES.txt) com os registros de cada entrega. Estados antigos não devem ser lidos como a situação atual.

## Limites planejados para as etapas seguintes

As quatro integrações marcadas S usam simulação para manter os dados fictícios separados da sua conta. Antes da publicação, a entrada de produção deverá usar os clientes/adaptadores reais e retirar os controles de simulação. Ainda é preciso validar:

- Conexão autorizada em projeto separado, versões simultâneas e PC/PWA; nenhuma senha/chave pessoal foi solicitada nesta revisão.
- Drive real, restauro e fechamento do novo aplicativo em teste controlado; configuração/sessão não fazem parte do backup SQLite.
- Entrada e pacote Qt reais. `executar.py` e `GestaoDaFeira.spec` ainda pertencem à versão funcional Tk; `executar_reforma.py` ainda não implementa `--verificar-pacote`/`--confirmar-atualizacao`. O helper legado passar em teste de pastas não comprova reinício/recibo Qt ou atualização 1.7.1 → 2.0.
- Migração/preservação de configurações e sessão, protocolo do pacote, recursos/fontes/licenças e recuperação após falha de atualização.
- Medições equivalentes de abertura, navegação, consultas, memória e pacote; não foi iniciado um novo benchmark nesta revisão.
- Interação no Windows, tela cheia/janelas menores, DPI 100/125/150%, teclado, foco, leitores de tela e textos/ajudas em todos os temas.

`suspender_coleta` é uma proteção específica para ciclos Tcl/Tk. Sua ausência literal no Qt não foi tratada como função perdida; a revisão deve garantir ciclo de vida correto de QObject/QThread, sem importar a interface antiga.

## Evidências e reprodução

A regressão existente e a coleta direcionada são resultados diferentes. Linux: **107/107 testes Qt**, **200 da aplicação aprovados e dois ignorados por exigirem Windows**, **31/31 dos protótipos**. As **seis checagens direcionadas não ficaram conformes**, com retorno 1 esperado do verificador. [JSONs locais](resultados/linux-revisao). **Windows:** regressão **107/107 Qt, 202/202 da aplicação e 31/31 dos protótipos**, sem falhas/erros/ignorados nessas três suítes. A coleta direcionada reproduziu **seis casos não conformes**, iguais aos observados no Linux. [Evidências da execução 40623364256](resultados/windows-40623364256), base `2c71975`. A resolução da VM foi restaurada.

A verificação específica da revisão retorna 1, por isso essa execução fica reprovada nessa etapa. Nenhum executável foi gerado. As reproduções usam Qt offscreen no Windows nativo; a interação com o gerenciador de janelas, foco/perda de foco reais e DPI permanecem verificações manuais.

Passar nos cenários já cobertos não comprova os seis casos novos.

```powershell
.\.venv-estudo\Scripts\python.exe reforma_desktop/avaliacao/revisar_etapa4.py --saida revisao-etapa4.json --exigir-conformidade
```

O script cria e remove seu próprio banco fictício. O script não recebe um caminho de banco. Com `--exigir-conformidade`, **o retorno esperado nesta revisão é 1**, pois há lacunas. Sem essa opção, 0 significa apenas que coletou os resultados, não aprovação. O JSON separa `casos_conformes` de `aprovacao_etapa4`, que permanece falsa até revisão do inventário completo.

O workflow registra essa coleta separadamente em `REVISAO_ETAPA4.json`. A verificação de revisão bloqueia o avanço enquanto os casos não estiverem conformes, mesmo que as três suítes existentes estejam aprovadas. Isso não é falha de build de um executável: nenhum executável ou release é gerado aqui.

## Próxima atividade

Fechar R01–R06 em entregas pequenas, com testes de regressão próprios: diagnóstico seguro; validação das datas e caminhos que dependem delas; proteção de encerramento dos trabalhadores; retomada na virada do dia; teclado sem abertura duplicada. Depois, repetir esta coleta e conferir novamente o inventário/revisão conjunta.

**Não encerrar a Etapa 4 nem iniciar a Etapa 5 com essas lacunas abertas.** A aprovação estética anterior e a confirmação do ensaio foram preservadas; não autorizam migrar o banco pessoal ou publicar a 2.0 antes das validações previstas.
