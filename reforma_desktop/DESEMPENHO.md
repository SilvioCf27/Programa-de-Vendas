# Etapa 5 — Fluidez do desktop integrado

**Resultado: medições e duas otimizações concluídas no estudo, com regressão aprovada no Linux e no Windows.** A etapa foi autorizada após as seis correções da revisão. O objetivo é medir os aplicativos ligados ao núcleo real e remover custos comprovados, mantendo dados corretos. A versão 1.7.1, o banco pessoal e a PWA permanecem preservados. O layout aprovado não foi alterado.

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

### Linux — medição concluída

Python 3.13.5, SQLite 3.50.4, Qt 6.10.2, display virtual para Tk e Qt offscreen. Referência `18592c2`, implementação otimizada `7cccfb1`. São **24 processos** no antes/depois, três por ferramenta/volume em cada rodada; dez ciclos de retorno por processo. Todos os pares mantiveram hashes/totais e a alteração controlada foi reconhecida. [JSONs completos](resultados/desempenho-linux).

Valores em ms: mediana das três observações; retornos usam a mediana das medianas dos dez ciclos de cada processo. Sem intervalos de confiança; amostra pequena e cache do SO preservado. Os valores individuais permanecem nos JSONs.

| Cenário Qt | 224 antes | 224 depois | 5.000 antes | 5.000 depois |
| --- | ---: | ---: | ---: | ---: |
| Abertura | 297,59 | 306,74 | 475,65 | 479,07 |
| Primeira Análises | 130,73 | 136,46 | 188,52 | 169,33 |
| Primeira Finanças | 81,89 | 85,67 | 112,31 | 119,89 |
| Retorno Análises | 12,04 | 12,56 | 13,84 | 14,80 |
| Retorno Finanças | 11,85 | 12,47 | 13,58 | 13,85 |
| Aplicar Mês | 32,28 | 29,46 | 176,77 | 161,42 |
| Aplicar Todas | 44,15 | 38,47 | 319,34 | 217,52 |
| Repetir Todas | 37,38 | 28,89 | 331,13 | 161,64 |
| Atualizar após mudança | 41,09 | 31,91 | 340,45 | 165,12 |

Com 5.000 vendas, Repetir Todas caiu de 331,13 para 161,64 ms (51,2%) e atualizar após mudança de 340,45 para 165,12 ms (51,5%). Aplicar Todas pela primeira vez caiu de 319,34 para 217,52 ms: nessa passagem ainda é necessário formatar os novos registros. Os retornos não fizeram leitura de vendas nas duas revisões. A reconsulta completa passou de duas leituras para uma, sem dispensar consulta após mudança.

Abertura ficou próxima: 475,65 → 479,08 ms com 5.000 vendas; não atribuímos melhoria a esse caminho. Primeira Finanças variou 112,31 → 119,89 ms. Os retornos variaram poucos ms; sem evidência de ganho geral nesses caminhos. A primeira Análises continua mais cara que retornar, pois sua criação/cálculo é adiada até o uso. Tk já prepara Análises ao atualizar Vendas; não comparar esse primeiro clique sem considerar seu trabalho prévio.

RSS Qt inicial com 5.000: 93,57 → 93,14 MiB; após todas as cargas: 119,98 → 122,91 MiB. O cache de apresentação tem um custo final de cerca de 3 MiB nesta carga. Crescimento nos dez ciclos aquecidos: 0,039 → 0,043 MiB; esse ensaio curto não comprova ausência de vazamento. O pico do SO não foi disponibilizado pelo coletor Linux.

Na rodada atual, Tk completo abriu em 827,85/980,74 ms e Qt em 306,74/479,08 ms (224/5.000). Tk com 5.000 levou 8.431,93 ms em Todas e 8.355,17 ms em repetir. Isso reproduz o gargalo já medido das larguras no produto estável; não é uma comparação isolada dos toolkits, pois a interface/tabela e a estratégia de criação são diferentes. Nenhuma otimização foi aplicada à versão funcional Tk.

### Windows — coleta completa

[Execução 40630217026](https://github.com/SilvioCf27/Programa-de-Vendas/actions/runs/40630217026): [evidências](resultados/desempenho-windows-40630217026), código anterior `18592c2` e atual `7cccfb1`. Windows Server 2025 x64, Python 3.13.16, SQLite 3.50.4, Qt 6.10.2, janela nativa 1536 × 960. Resolução da VM restaurada ao terminar. **24 processos** antes/depois, sem excluir primeiras amostras. Dados, totais, recortes financeiros e invalidação conferidos. Mesma agregação da tabela Linux, em ms.

| Cenário Qt | 224 antes | 224 depois | 5.000 antes | 5.000 depois |
| --- | ---: | ---: | ---: | ---: |
| Abertura | 731,32 | 935,30 | 931,31 | 920,61 |
| Primeira Análises | 216,37 | 238,72 | 259,06 | 255,35 |
| Primeira Finanças | 137,63 | 144,01 | 177,39 | 174,03 |
| Retorno Análises | 25,05 | 27,16 | 25,59 | 24,28 |
| Retorno Finanças | 26,02 | 28,20 | 26,42 | 25,00 |
| Aplicar Mês | 57,42 | 57,77 | 215,42 | 211,28 |
| Finanças Ano | 59,24 | 66,75 | 100,71 | 100,86 |
| Aplicar Todas | 76,46 | 77,04 | 405,77 | 322,63 |
| Repetir Todas | 65,33 | 55,20 | 425,34 | 211,10 |
| Atualizar após mudança | 69,64 | 61,99 | 434,50 | 215,77 |
| Análises após mudança | 39,85 | 40,79 | 237,64 | 234,34 |

Com 5.000 registros, repetir caiu 425,34 → 211,10 ms (**50,4%**) e atualização após mudança 434,50 → 215,77 ms (**50,3%**). Aplicar Todas caiu 405,77 → 322,63 ms (**20,5%**). Com 224, repetir caiu 65,33 → 55,20 ms; aplicar Todas ficou próximo de 77 ms. A operação realmente continua consultando o banco, com uma leitura em vez de duas. Os 30 retornos por processo não fizeram leitura de vendas nem reconstrução da consulta.

O RSS inicial Qt com 5.000 ficou em 109,13 → 109,16 MiB; o final, 135,07 → 139,06 MiB; pico do SO, 137,02 → 140,65 MiB. O custo final observado foi cerca de **4 MiB**. Crescimento nos dez ciclos aquecidos: 0,039 → 0,016 MiB; isso não prova ausência de vazamento. O cache é limitado aos registros da consulta atual, por teste de remoção/recorte.

A versão Tk permaneceu intacta e oferece um controle de variação da VM: na rodada atual, com 5.000 vendas, abriu em 2.363,49 ms, repetiu Todas em 1.177,02 ms, retornou a Análises/Finanças em 322,78/761,50 ms, RSS inicial/final 65,99/78,07 MiB. Qt usa mais memória. Com 224, Aplicar Mês foi 49,61 ms no Tk e 57,77 ms no Qt; a migração não torna toda operação individual mais rápida. São produtos com estratégias e apresentação diferentes, não benchmark puro dos toolkits.

Na leitura isolada de todas as 5.000 vendas, a mediana das medianas de dez leituras foi 34.44 ms no Tk e 42.94 ms no Qt. Ambos chamam o mesmo núcleo; a principal economia visada foi eliminar leitura duplicada e formatação, sem reescrever o SQL.

#### Contraprova da abertura com 224 — concluída

A mediana inicial variou de 731,32 para 935,30 ms (+27,9%). Não foi descartada como ruído nem tomada como regressão comprovada. As três amostras foram 1.443,25/731,32/721,73 ms antes e 1.002,55/935,30/715,86 ms depois. Com 5.000, ficou 931,31 → 920,61 ms. A coleta completa executou primeiro o bloco anterior e depois o atual; os processos alternavam Tk/Qt dentro de cada bloco.

A [contraprova específica](avaliacao/medir_abertura.py) executou sete pares de processos novos, alternando **as revisões** em cada par e separando fases e CPU. [Execução 40631254061 e JSONs](resultados/abertura-windows-40631254061), referência `18592c2`, atual `c758072` (os mesmos arquivos de aplicação de `7cccfb1`; a mudança foi somente no instrumento). A resolução foi restaurada e todos os pares mostraram os mesmos registros/dimensões.

| Fase da abertura, 224 vendas | Antes | Depois |
| --- | ---: | ---: |
| Total, mediana | 700,16 ms | 684,50 ms |
| CPU do processo, mediana | 640,63 ms | 609,38 ms |
| Importação gráfica | 120,60 ms | 122,06 ms |
| Preparar interface | 38,63 ms | 35,97 ms |
| Construir janela/consulta | 434,07 ms | 426,28 ms |
| Exibir e processar eventos | 101,26 ms | 103,16 ms |
| RSS inicial | 107,94 MiB | 108,06 MiB |

As medianas das fases são independentes e não devem ser somadas para reconstruir a mediana total. Abertura total variou 675,59–1.508,85 ms antes e 681,93–775,30 ms depois; as primeiras amostras foram mantidas. O aumento de 27,9% da coleta em blocos **não se repetiu** no ensaio alternado. Não há evidência de regressão sistemática causada pela alteração; também não anunciamos ganho de abertura com base em 15,66 ms. A origem exata da variação da primeira VM não foi isolada. A contraprova reduz o viés de ordem e documenta os custos de cada fase; não garante tempos fixos no PC do usuário.

## Regressão e critérios

- Linux: **127/127 Qt**, **200 da versão estável aprovados e dois nativos ignorados**, **31/31 protótipos**; seis checagens R01–R06 conformes.
- Windows: **127/127 Qt, 202/202 estável, 31/31 protótipos**, sem falhas/erros/ignorados; seis checagens conformes. [Execução 40630216953](resultados/windows-40630216953), código `7cccfb1`; resolução restaurada.
- O critério de correção é inegociável: consultas e resumos devem refletir a fixture e sua mudança. O ganho deve aparecer no caminho visado; retornos sem alteração não devem refazer consultas nem duplicar timers. Esses critérios passaram nas coletas.
- Abertura não foi alvo da otimização. A contraprova alternada não repetiu o aumento observado com 224. As duas coletas e seus ranges permanecem no relatório; não há promessa de latência fixa ou ganho de abertura.



## Conclusão da etapa e próxima atividade

Os caminhos visados tiveram ganhos consistentes nos dois sistemas; os testes preservaram valores, semana independente, invalidação e exportação completa. A navegação reutiliza telas, sem reconstruir consultas/timers sem mudança. Optamos por manter a criação de Análises/Finanças sob demanda e o custo explícito da primeira visita; pré-carregar apenas deslocaria esse trabalho para a abertura. Não há motivo medido para trocar bibliotecas ou acrescentar animações nesta etapa.

A próxima atividade é a **Etapa 6 original: revisar a equivalência e preparar a validação de produção**. Começar pela matriz de 30 funções e pelas quatro integrações simuladas, definindo o teste controlado dos adaptadores reais e a preservação de configurações/sessão. Continuam necessárias interação Windows, escalas reais, acessibilidade, pacote Qt e atualização/recuperação 1.7.1 → 2.0. A publicação depende dessas verificações e aprovação; esta entrega não muda o executável estável.

## Limitações

Ensaios de curta duração em máquinas de teste não garantem ausência de vazamento, desempenho do PC do usuário, latência autenticada de Supabase/Drive ou comportamento após dias de uso. DPI real, leitores de tela, integrações reais e pacote/atualização continuam pendentes. A Etapa 6 original deve validar esses pontos e a equivalência antes da publicação aprovada da 2.0. Nenhum executável é gerado nesta etapa.
