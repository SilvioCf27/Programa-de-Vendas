# Revisão conjunta da Etapa 4

**Resultado atual — 28/10/2026: as seis lacunas R01–R06 foram corrigidas no estudo e a revisão foi repetida.** O usuário autorizou as correções após a confirmação do ensaio. O layout aprovado e os critérios da coleta foram preservados.

A matriz dos **30 itens** passa a **26 I e quatro S**, sem os seis P anteriores. Isso permite preparar as medições da Etapa 5 quando a rodada final estiver confirmada; integrações reais, interação manual, DPI, pacote e atualização continuam nas validações previstas. Não houve mudança dos cálculos, esquema, versão 1.7.1, banco pessoal, contas ou PWA.

## Correções aplicadas

| Caso | Correção e resultado esperado na repetição |
| --- | --- |
| R01 | [DataValidada e data_iso](campos_financeiros.py) impedem usar o último valor válido após uma edição incompleta. [Salvar venda](aplicacao.py) permanece aberto com aviso até completar/confirmar a data, inclusive com clique ou Enter. |
| R02 | [SeletorPeriodo](painel_analises.py) valida as datas de Data/Intervalo antes de consultar. O resultado aplicado é preservado/atualizado quando há nova seleção incompleta; campos ocultos não bloqueiam Mês/Fechamento. |
| R03 | Dois atalhos com foco restrito à tabela chamam a edição pelo ID da página visível uma vez. Duplo clique e os demais controles mantêm seu comportamento. |
| R04 | [diagnostico_qt.py](diagnostico_qt.py) reutiliza o registro técnico seguro para entrada, callbacks e trabalhadores. Logs contêm somente data, versão, tipo e posições; sem mensagens, valores ou credenciais. Falhar ao registrar não mascara o erro original. |
| R05 | O fechamento verifica operações de configurações e threads filhas, além de nuvem/atualizador. As conclusões aguardam o término nativo antes de liberar a UI. Depois de concluir o trabalho, fechar volta a funcionar. |
| R06 | O dia é confirmado após sucesso. Falhas de armazenamento têm aviso/diagnóstico e nova tentativa no próximo disparo. O aviso é removido ao recuperar, preservando mensagens mais recentes. |

[Quinze novos testes de regressão](tests/test_correcao_revisao_qt.py) cobrem os seis casos e seus caminhos relacionados. A entrada Qt continua isolada; os logs são persistentes somente quando usar uma pasta fixa de estudo. Com banco temporário, eles são descartados junto dos testes ao fechar.

## Histórico — lacunas reproduzidas em 27/10/2026

O usuário confirmou o teste do ensaio do atualizador. A revisão seguinte percorreu os 30 itens e encontrou os seis casos abaixo. As observações e evidências anteriores ficam preservadas para comparação; as correções estão descritas acima.


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
- **P**: implementação parcial com lacuna aberta; nenhuma permanece entre R01–R06 na repetição atual.
- **S**: mecanismos exercitados no estudo com transporte/processos simulados; integração real ainda pendente.

Resultado atual: **26 I e 4 S**. Em 27/10 eram 20 I, 6 P e 4 S; os seis P foram corrigidos em 28/10. DPI, acessibilidade, desempenho comparável e empacotamento são verificações adicionais aplicáveis ao conjunto, nas etapas previstas.

| ID | Estado | Acesso no estudo | Código e evidência principal |
| --- | --- | --- | --- |
| V01 | I | Nova venda; editar/excluir na linha; cancelar formulário | [aplicacao.py](aplicacao.py), `FormularioVenda.gravar/data_iso`; [testes Vendas](tests/test_vendas_qt.py) e [correções](tests/test_correcao_revisao_qt.py); R01 corrigido. |
| V02 | I | Recusa de cadastro repetido e correção posterior | [vendas.py](vendas.py), `ServicoVendas.salvar`; núcleo `banco.py`; testes de duplicidade, edição e backup. |
| V03 | I | Tabela, ordenação, busca, rolagem e ações por linha | [aplicacao.py](aplicacao.py), `ordenar/preencher_tabela`; `noturno_demo.Tabela` preserva duplo clique; atalhos Qt por página/foco corrigem R03. |
| V04 | I | Filtros de Vendas, Aplicar e Limpar | `sincronizar/consulta_campos/aplicar/limpar`; testes de consulta pendente e período. |
| V05 | I | Seis blocos superiores e comparação anterior | `ServicoVendas.consultar` e `Janela.exibir_resultado`; `resumos.py`, sem instanciar estado fictício da demo. |
| V06 | I | Semana atual independente e detalhes | `semanas.semana_atual`, `detalhes_semana/verificar_dia`; domingo/segunda, virada e recuperação após falha transitória testados; R06 corrigido. |
| V07 | I | Configurações → período inicial | [configuracoes.py](configuracoes.py), `salvar_periodo`; `preferencias.py`; persistência e reabertura testadas. |
| V08 | I | Exportar relatório → CSV/Excel | `exportar_consulta`, `exportacao.py`; consulta aplicada inteira, sem recorte pela busca/página; não há menu duplicado. |
| V09 | I | Selecionar página, excluir selecionados e paginação | `Tabela`, `ServicoVendas.excluir`; backup e transação do lote com conferência de todos os registros. |
| A01 | I | Análises → resultado por semana | [analises.py](analises.py), `analisar`; `agrupar_semanas`; [testes Análises](tests/test_analises_qt.py) de recortes, zeros e snapshot completo. |
| A02 | I | Comparar A/B com seletores independentes | [painel_analises.py](painel_analises.py), `SeletorPeriodo.periodo/PainelAnalises.comparar`; tipos e limites testados; R02 corrigido: entrada parcial e atualização do resultado aplicado cobertas. |
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
| G02 | I | Configurações, versão base e caminho selecionável | `configuracoes.py/painel_atualizacao.py`; [diagnostico_qt.py](diagnostico_qt.py) conecta o [registro seguro](../ProgramFeira/diagnostico.py) em entrada/callbacks/workers: R04 corrigido. |
| G03 | I | Backup, verificar/restaurar, Drive e cópia ao fechar | [configuracoes.py](configuracoes.py), [operacoes_backup.py](operacoes_backup.py); [testes Recuperação](tests/test_recuperacao_qt.py); guarda global de encerramento e término de threads corrigem R05. |
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

## Histórico de evidências — revisão anterior

A regressão existente e a coleta direcionada são resultados diferentes. Linux: **107/107 testes Qt**, **200 da aplicação aprovados e dois ignorados por exigirem Windows**, **31/31 dos protótipos**. As **seis checagens direcionadas não ficaram conformes**, com retorno 1 esperado do verificador. [JSONs locais](resultados/linux-revisao). **Windows:** regressão **107/107 Qt, 202/202 da aplicação e 31/31 dos protótipos**, sem falhas/erros/ignorados nessas três suítes. A coleta direcionada reproduziu **seis casos não conformes**, iguais aos observados no Linux. [Evidências da execução 40623364256](resultados/windows-40623364256), base `2c71975`. A resolução da VM foi restaurada.

A verificação específica da revisão retorna 1, por isso essa execução fica reprovada nessa etapa. Nenhum executável foi gerado. As reproduções usam Qt offscreen no Windows nativo; a interação com o gerenciador de janelas, foco/perda de foco reais e DPI permanecem verificações manuais.

Passar nos cenários já cobertos não comprova os seis casos novos.

```powershell
.\.venv-estudo\Scripts\python.exe reforma_desktop/avaliacao/revisar_etapa4.py --saida revisao-etapa4.json --exigir-conformidade
```

O script cria e remove seu próprio banco fictício. O script não recebe um caminho de banco. Com `--exigir-conformidade`, **o retorno da rodada anterior era 1; após as correções, o esperado é 0**, com os seis casos conformes. Sem essa opção, 0 significa apenas que coletou os resultados, não aprovação. O JSON separa `casos_conformes` de `aprovacao_etapa4`, que permanece falsa até revisão do inventário completo.

O workflow continua registrando essa coleta separadamente em `REVISAO_ETAPA4.json`. A verificação de revisão bloqueia o avanço enquanto os casos não estiverem conformes, mesmo que as três suítes existentes estejam aprovadas. Isso não é falha de build de um executável: nenhum executável ou release é gerado aqui.

## Repetição após as correções — 28/10/2026

Os resultados finais Linux/Windows desta repetição serão registrados após a rodada completa. O roteiro original [revisar_etapa4.py](avaliacao/revisar_etapa4.py) continua com os mesmos seis critérios; ele não foi enfraquecido para aceitar os defeitos.

`casos_conformes=true` significa que as seis checagens passaram. `aprovacao_etapa4=false` é mantido por desenho do coletor: ele não concede aprovação geral do inventário, de release ou da migração pessoal. A revisão técnica documentada, o gate e as aprovações do plano têm escopos distintos.

Os testes de clique/Enter desta entrega também verificam a normalização na perda de foco, além das chamadas diretas da coleta original. Inspeção interativa no Windows, escalas e leitor de tela continuam pendentes; não foram substituídos pelos testes offscreen.

## Próxima atividade

Após confirmar a regressão e o gate R01–R06, iniciar a **Etapa 5**, com medições equivalentes de abertura, navegação, consultas e memória. Manter as quatro integrações S isoladas até a validação real prevista e preservar os critérios de pacote/atualização/aprovação antes da 2.0. Nenhuma publicação ou migração pessoal foi autorizada por esta coleta.
