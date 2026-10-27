# Recomendação técnica da reforma desktop

**Decisão posterior ao relatório:** em 27/10/2026 o usuário aprovou explicitamente PySide6 e o início da Etapa 4. Veja a seção 19 do [plano](../../../docs/PLANO_REFORMA_DESKTOP.txt) e a [primeira integração](../../../reforma_desktop/README.md). Os resultados e a recomendação abaixo documentam a avaliação anterior à aprovação.

**Recomendo adotar PySide6 para a futura interface, mantendo Python e as regras existentes. A escolha aguarda aprovação explícita do usuário. A Etapa 4 não começou.**

A aprovação visual das três telas principais e quatro janelas secundárias está registrada na seção 18 do [plano original em andamento](../../../docs/PLANO_REFORMA_DESKTOP.txt). O desktop funcional 1.7.1, sua entrada, banco, sincronização, backups, atualizador e PWA permanecem preservados. Os executáveis desta avaliação são ensaios separados, não uma release.

## Evidência e método

Ensaio final Windows: [execução 40542460952](https://github.com/SilvioCf27/Programa-de-Vendas/actions/runs/40542460952), commit `45370d217270732859da88b05ceec52f0cacb14f`. Windows Server 2025 10.0.26100 x64, Python 3.13.16, SQLite 3.50.4, Tcl/Tk 8.6.15 e PySide6 Essentials 6.10.2. A VM foi ajustada de 1.024 × 768 para 1.920 × 1.080 e restaurada ao final. Não é o computador do usuário.

Foram 20 processos: cinco repetições por ferramenta e volume, em ordem alternada, com 224 e 5.000 vendas fictícias. Mesmo gerador, SQL, valores, fonte Segoe UI, janela efetiva de 1.280 × 800, paginação de 50 registros e agregação semanal. Cada par conferiu SHA-256 e total; nenhum dado pessoal foi acessado. Cada processo executou 40 ciclos de consulta, navegação pelas três áreas e abertura/fechamento de detalhe. O cenário de tabela completa é separado da navegação paginada.

Tk usa Treeview; Qt usa TableView com modelo. São operações equivalentes com APIs próprias, sem reconstruir duas vezes a aplicação funcional. O custo das consultas é separado da atualização/pintura. O tempo de abertura inclui importação da ferramenta e primeira exibição, mas exclui início do interpretador e preparação dos dados. O cache do SO não foi limpo. Medianas abaixo são a mediana das cinco medições ou das medianas de cada processo, conforme o cenário. JSONs guardam máximos e p95 por processo; não há estimativa de intervalo de confiança.

## Desempenho no Windows

| Critério | Tkinter | PySide6 |
| --- | ---: | ---: |
| Abertura, 224 registros | 163,8 ms | 233,6 ms |
| Abertura, 5.000 registros | 162,3 ms | 226,6 ms |
| Aplicar mês, 224 registros | 36,2 ms | 13,8 ms |
| Navegar para Análises, 224 registros | 39,4 ms | 15,6 ms |
| Navegar para Finanças, 224 registros | 33,7 ms | 13,2 ms |
| Primeira visita a Análises, 5.000 registros | 59,6 ms | 17,8 ms |
| Primeira visita a Finanças, 5.000 registros | 52,5 ms | 15,4 ms |
| Abrir/fechar detalhe, 5.000 registros | 60,1 ms | 55,2 ms |
| Aplicar mês, 5.000 registros | 35,7 ms | 13,6 ms |
| Navegar para Análises, 5.000 registros | 39,4 ms | 15,1 ms |
| Navegar para Finanças, 5.000 registros | 33,8 ms | 12,9 ms |
| Preencher tabela completa, 5.000 registros | 75,1 ms | 30,3 ms |
| SQL compartilhado: todas, 5.000 registros | 6,62 ms | 5,83 ms |

Tk abriu mais rápido; Qt respondeu melhor às operações gráficas deste cenário. Não há motivo para atribuir ao toolkit a pequena diferença de SQL. A primeira abertura teve valores extremos: 160,2–1.476,8 ms no Tk e 228,9–624,8 ms no Qt com 224 registros. Foram mantidos nos resultados, e não escondidos pela mediana. Essas medições não prometem abertura nem navegação do produto completo nessa velocidade.

A maior demora observada entre callbacks do indicador de atendimento da interface, com 5.000 registros, variou de 52,8–84,3 ms no Tk e 63,7–74,3 ms no Qt. Esse indicador inclui efeitos do agendamento e do bombeamento de eventos do ensaio: não é tempo de cada clique nem comprovação de ausência de travamentos no uso real.

## Memória e duração do ensaio

| Critério | Tkinter | PySide6 |
| --- | ---: | ---: |
| RSS inicial, 224 registros | 39,42 MiB | 67,61 MiB |
| Pico do SO, 224 registros | 41,71 MiB | 72,56 MiB |
| RSS inicial, 5.000 registros | 41,42 MiB | 69,67 MiB |
| Pico do SO, 5.000 registros | 51,38 MiB | 76,91 MiB |
| Crescimento após carga / 40 ciclos, 224 registros | 0,04 MiB | 0,73 MiB |
| Crescimento após carga / 40 ciclos, 5.000 registros | 0,04 MiB | 0,60 MiB |

Os dois terminaram com zero diálogos vivos. Qt exige mais memória. O teste curto não prova ausência de vazamentos em uso prolongado. Também houve coleta amostrada a cada 10 ms; pico do SO não é tamanho instalado.

Contraprova Linux x86_64, Python 3.13.5, SQLite 3.50.4, display virtual: com 5.000 registros, abertura 78,6/122,6 ms, RSS inicial 28,85/63,25 MiB e tabela completa 49,0/17,4 ms (Tk/Qt). Navegação teve diferenças menores que no Windows. Crescimento Qt nos 40 ciclos ficou em 3,89 MiB nesse backend, contra 0,02 MiB Tk; não foi omitido nem interpretado automaticamente como vazamento. Não misturamos resultados dos dois sistemas numa média.

## Escalas, legibilidade e acessibilidade

As duas ferramentas passaram os ensaios de fatores de aplicação 100%, 125% e 150%, incluindo foco/seleção via tecla Down. São seis execuções, com cinco paletas em cada uma. Tk usa pixels de janela e Qt unidades lógicas: dimensões brutas em fatores maiores não são diretamente comparáveis. A altura é limitada pela área útil da VM quando necessário. Isso **não substitui mudar o DPI real do Windows**, testar múltiplos monitores ou verificar todos os formulários.

Claro, Escuro, Grafite, Areia e Aurora foram renderizados no cenário técnico a partir dos mesmos literais de paleta. Nos pares medidos (texto, texto secundário e seleção), o menor contraste foi 4,76:1. É verificação parcial de viabilidade; não é certificação WCAG, nem cinco temas finais implementados no protótipo Qt.

Na consulta Windows UI Automation, Tk expôs oito elementos Pane sem nomes neste ensaio; Qt expôs 137 elementos, incluindo botões nomeados, tabela e itens. QAccessible também identificou a tabela Qt pelo nome. Essa evidência favorece Qt para uma base acessível, mas não conclui conformidade nem prova impossibilidade de melhorar Tk. Não houve sessão com NVDA/JAWS, alto contraste ou auditoria de toda a sequência de Tab. As demos já têm ensaios parciais de Tab/Escape.

As correções pontuais desta rodada trataram leitura UTF-8 de testes no Windows, largura da paginação e conteúdo estreito da Semana atual. A checagem dos protótipos iniciais passou a exigir pelo menos cinco linhas completas visíveis nas duas ferramentas, em vez de rejeitar a tabela Tk de 296 px por um limite arbitrário de 300 px. Não houve novo redesenho nem mudança dos dados.

## Empacotamento e distribuição

PyInstaller 6.16.0, modo pasta, mesmos recursos decorativos, fontes e ícones. Qt inclui Svg, usado pela identidade aprovada; a outra ferramenta é excluída de cada pacote.

| Pacote Windows de estudo | Tkinter | PySide6 |
| --- | ---: | ---: |
| Tamanho instalado | 31,0 MiB | 104,5 MiB |
| ZIP | 14,3 MiB | 41,8 MiB |
| Arquivos | 1.034 | 244 |
| Autoteste do executável | Aprovado | Aprovado |

Ambos confirmaram execução congelada (`frozen=True`), SQLite 3.50.4, dados e seleção com PATH restrito e sem variáveis do venv. O runner ainda possui Python instalado; não equivale a máquina nova sem dependências. Esses tamanhos são dos ensaios, não do futuro Gestão da Feira completo.

Os valores estão abaixo dos limites atuais do atualizador (ZIP 250 MiB, extração 600 MiB e 5.000 arquivos). **Não foram instalados pelo atualizador**: têm nomes EnsaioTk/EnsaioQt, sem a estrutura de release do produto. A futura release exige ensaio real de atualização, recuperação, sessão, configurações e dados, na etapa de validação já prevista. Não se publicou novo executável estável.

PySide6 pode ser usado sem licença comercial pela opção LGPL, cumprindo os termos aplicáveis. Foram preservados os textos oficiais e registrado o exame de distribuição em [licencas/LEIA-ME.md](licencas/LEIA-ME.md). Avisos completos, versões/fontes, licenças dos componentes incluídos e substituição compatível de bibliotecas dinâmicas precisam ser conferidos antes de distribuir o produto reformado. O projeto não recebeu uma nova licença nesta rodada. Tk/Tcl reduzem esse trabalho e o peso de dependências.

## Manutenção e integração

Tkinter tem menor risco de transição: já sustenta o produto, não exige trocar o loop gráfico e deixa um pacote menor. Os controles ttk podem receber estilos modernos; o aplicativo atual já usa imagens de contorno com controles nativos. Não é correto atribuir o limite visual a uma impossibilidade do Tkinter.

PySide6 oferece modelo/visão para tabelas, estilização, SVG e uma ponte de acessibilidade que se mostrou mais rica no Windows. Esses recursos combinam melhor com a identidade aprovada e com a manutenção de listas densas, seleção e paginação. O custo é adaptar a interface, gerenciar propriedade/destruição dos objetos, integrar o loop de eventos e manter dependências maiores.

A inspeção identifica regras aproveitáveis em `financeiro.py`, `fechamento.py`, persistência, backups e sincronização. `main.py` e `interface/painel_*` têm acoplamentos gráficos que exigirão adaptação cuidadosa. O Agendador recebe um relógio com `after/after_cancel`; uma futura integração Qt deve adaptar essa fronteira, preservando o protocolo e as regras. Filas, threads e devolução de resultados à interface também precisam de equivalência. **Nenhuma dessas adaptações foi iniciada.**

O gargalo já medido no programa atual é dimensionar colunas a cada atualização, não uma incapacidade geral do Tkinter: com 5.000 vendas, esse caminho consumiu cerca de 7,88 s no ensaio Linux anterior. Pode ser otimizado em qualquer escolha. O [levantamento e perfil da base](../MEDICOES.md) distingue leitura, inserção, preparação de análises, exportação e colunas; tempos aninhados não devem ser somados. Não usamos esse perfil para anunciar uma aceleração Qt do programa completo.

## Testes, limites e estado do plano

- **Windows nativo na VM:** 202/202 testes da aplicação e 31/31 dos estudos aprovados, sem falhas, erros ou ignorados. Os dois pacotes passaram. Todas as 20 comparações concluíram com os mesmos dados/totais e sem diálogos retidos.
- **Linux com SQLite compatível:** 202 executados, 200 aprovados e dois ignorados por dependerem de PowerShell/DPAPI do Windows. A suíte de estudos também passou nos 31 casos locais.
- A primeira tentativa Linux usava SQLite 3.46.1 e falhou nas verificações de backup por não atender ao mínimo de segurança. O runtime de teste foi atualizado para SQLite 3.50.4, sem reduzir a proteção nem editar o código estável. Os resultados finais estão separados dessa tentativa inválida.
- Rodadas preliminares do medidor foram descartadas por não processar destruições Qt adiadas ou por bloquear a saída da consulta UIA em pipe. O ensaio final corrigiu o ciclo de vida e usa arquivos para a coleta UIA. Isso evita tratar falhas do instrumento como defeitos do toolkit.
- Não houve sessão autenticada real, latência de Supabase/Drive, restauração pessoal, teste contínuo por dias, hardware do usuário, leitor de tela completo ou DPI real de monitor. Também não há medição equivalente do produto completo em Qt, pois isso exigiria iniciar a migração ainda não autorizada.

A Etapa 1 tem inventário e base controlada documentados, com lacunas ambientais explícitas: espera real de rede e cobertura manual completa de todos os estados continuam sem medição. Não são pré-requisitos para comparar o custo dos renderizadores; precisam continuar rastreáveis nas verificações da implementação. As Etapas 2/2A têm a revisão estética desta entrega concluída. A Etapa 3 tem agora comparação e recomendação entregues; **continua aberta para aprovação explícita da ferramenta**, sem declarar concluídos os testes manuais pendentes. Etapas 4–7 permanecem na ordem original.

## Decisão proposta e próxima atividade

**PySide6 é a recomendação para esta reforma**, pelo modelo de tabelas, manutenção da identidade aprovada e base de acessibilidade observada. O custo adicional de aproximadamente 28 MiB de RSS inicial e 73,5 MiB instalados no ensaio é aceitável para o desktop pretendido; não é uma decisão baseada em abrir mais rápido. Se a prioridade dominante fosse menor consumo e menor alteração de código, Tkinter seria a escolha conservadora e viável.

A próxima atividade é o usuário aprovar explicitamente a escolha tecnológica, encerrando esse ponto da Etapa 3. Somente depois poderá começar a Etapa 4 original: navegação/Vendas, Análises, Finanças e configurações/formulários, por partes e com equivalência funcional. Nenhuma aprovação visual foi interpretada como essa autorização.

## Arquivos verificáveis

- [Método, scripts e reprodução](README.md)
- [Comparação Windows completa](resultados/windows-40542460952/COMPARACAO_WINDOWS.json)
- [Empacotamento Windows](resultados/windows-40542460952/EMPACOTAMENTO.json)
- [Escalas e paletas Windows](resultados/windows-40542460952/ESCALAS_PALETAS.json)
- [Suíte da aplicação no Windows](resultados/windows-40542460952/TESTES_PRODUCAO.json) e [dos estudos](resultados/windows-40542460952/TESTES_DEMO.json)
- [Origem da execução](resultados/windows-40542460952/ORIGEM.json) e [resolução/restauração da VM](resultados/windows-40542460952/TELA_WINDOWS.json)
- [Comparação Linux](resultados/linux/COMPARACAO_LINUX.json) e [suíte com SQLite compatível](resultados/linux/TESTES_PRODUCAO.json)
