# Refinamento orientado pelo Read.txt completo

O [documento enviado pelo usuário](../../docs/REFINAMENTO_VISUAL_DESKTOP.txt) orientou esta revisão. A fonte de identidade são as três imagens conceituais de Vendas, Análises e Finanças enviadas ao repositório; as regras continuam no código real. As [capturas atualizadas](NOTURNO.md) vêm da demo executada.

## Inspeção e escopo preservado

O aplicativo funcional está em `ProgramFeira/main.py`, com Tkinter, SQLite e os painéis de Análises/Finanças existentes. Fontes e temas são carregados pelos módulos de interface atuais. A revisão visual navegável é `noturno_demo.py`, em PySide6, com estado fictício em memória e recursos locais. Esses processos e suas responsabilidades continuam separados.

O documento fala em três telas implementadas e em usar a biblioteca atual. Nesta frente isso significa refinar a demo PySide6 existente, seguindo o plano e as revisões anteriores; não iniciar uma migração silenciosa do programa funcional. Os cinco temas de produção — Noite, Claro, Grafite, Areia e Aurora — permanecem no código estável. A demo apresenta somente a direção Noturno aprovada. **A equivalência dos cinco temas na eventual nova interface não está concluída.**

Nenhum arquivo de `ProgramFeira`, PWA, requisitos de produção ou banco foi alterado nesta rodada. Login, nuvem, backup, fechamento, exportação e formulários reais não foram substituídos por desenhos. Os avisos de prévia da demo continuam explícitos.

## Aplicação das orientações

| Seção do Read.txt | Entrega na revisão |
| --- | --- |
| Identidade compartilhada | Paleta e QSS em módulo próprio, tokens de tipografia e espaçamento; Inter local, Lucide consistente, estados dos controles; retirada do acesso duplicado a configurações e do texto repetido de tema na lateral |
| Seis indicadores | Preservados valores, ajudas, notas e barras de participação; notas sem truncar o texto sobre dias zerados |
| Semana atual | Três regiões mantidas; pagamentos em grade de ícone, nome e valor alinhado; foto decorativa e transição preservadas; semana continua independente dos filtros |
| Comparação anterior | Intervalo, valor, dias, média, diferença monetária em destaque e percentual calculado com base válida; base zero tem mensagem explícita, sem percentual inventado |
| Participação em Vendas/Análises | Uma renderização compartilhada, anel proporcional e colunas alinhadas de nomes, percentuais e valores; estado sem vendas explícito |
| Histórico/filtros | IDs, datas e valores mantidos, ações com margem; dias em controles marcados com texto e estado; campos pendentes continuam distintos da consulta aplicada |
| Gráfico semanal | Escala vertical monetária, referências discretas, barras com gradiente, rótulos dos intervalos e valores, zero sem barra de altura fictícia, tooltip de consulta |
| Resumo de Análises | Total, semanas, dias e média em blocos compactos, sem repetir os seis indicadores de Vendas |
| Tabela semanal | Altura relacionada à quantidade de linhas, limitada a seis linhas antes de rolagem; colunas e indicação de recorte completo/parcial preservadas |
| Comparador A/B | Grupos de seletores com cores distintas, valores e diferença em destaque; consulta independente e validação de intervalo mantidas |
| Detalhes do período | Quatro acessos em grade, com ícones e descrições específicas; nenhuma fileira adicional de abas |
| Consulta/indicadores de Finanças | Mesmos quatro tipos e indicadores; apenas acabamento compartilhado ajustado |
| Valores secundários | Três resultados visíveis com ícones e separadores compactos |
| Lançamentos e acessos financeiros | Datas de compra/fatura separadas, categorias, parcelas, valores, seleção, paginação e ações da demo preservados; botões por linha afastados da borda |
| Janela menor | Cabeçalho e grupos completos se empilham quando falta largura; rolagem mantém o acesso ao conteúdo |

Os percentuais adicionados à apresentação da demo derivam dos valores fictícios já consultados. Não alteram os cálculos do programa estável. Não houve acréscimo de filtros, reclassificação de compras, mudança de datas ou criação de dados para preencher áreas vazias. Ordenação e formulários reais não foram implementados como parte desta rodada de acabamento.

## Arquivos e componentes

- `noturno_demo.py`: refina os componentes existentes e as três telas; grade semanal de pagamentos, apresentação de comparação, resumo, gráfico e detalhes.
- `tema_noturno.py`: centraliza cores, variações de superfície, QSS e referências de tipografia/espaçamento da demo; não altera os temas do aplicativo funcional.
- `apresentacao_noturno.py`: formatação percentual com Decimal e mensagens para ausência de base.
- `LinhaResponsiva`: componente compartilhado que muda a orientação de grupos sem descartar controles ou reiniciar consultas.
- `Grafico`: mantém a renderização real em Qt e compartilha legenda/alinhamento entre as telas.
- `acesso`, `titulo_secao`, `texto`, `tile`: componentes reutilizados, com medidas, texto e estados refinados.
- `test_noturno.py`: verificações de regressão e dos novos estados de apresentação.
- `validar_escala_noturno.py` e `ESCALAS_NOTURNO.json`: ensaio de renderização em processos separados com fatores Qt.
- `imagens/noturno-*.png`: capturas novas das três áreas e de Vendas em janela menor.
- Documentação: este relatório, plano, galeria e documento original em TXT.

## Validação

- **19 testes da revisão passaram**: consultas, centavos, isolamento, períodos, zero/futuro, paginação, seleção, exclusão/cancelamento, independência A/B/Finanças, percentuais, tabela compacta, consulta pendente e redimensionamento até 1.000 × 700.
- **4 testes dos estudos anteriores passaram novamente**, preservando a comparação entre ferramentas.
- **27 cenários renderizados passaram**: três áreas × três tamanhos lógicos × fatores Qt 1, 1,25 e 1,5. O ensaio verifica que a largura externa não corta a página e executa a pintura. Não é uma verificação exaustiva de cada rótulo, interação ou leitor de tela.
- Houve regressão de largura em Análises durante o refinamento; ela foi corrigida com grupos responsivos e ajuste dos seletores. Nenhuma falha permanece na bateria executada.
- As capturas foram inspecionadas no Linux. Imagens do chat não são necessárias para a revisão: a galeria está no GitHub.
- Os testes de produção e de pacote Windows não foram repetidos: não houve alteração funcional ou empacotamento nesta entrega.

## Limites e próxima revisão

Os fatores de escala Qt foram simulados **no Linux**, não em Windows real. Seguem pendentes Windows/DPI 100/125/150%, conferência completa de foco/teclado e acessibilidade, comparação com o monitor do usuário e os demais temas na nova interface. Não declaramos os critérios finais do documento concluídos para o aplicativo de produção.

A demo continua sem login, banco, Drive ou sincronização; cadastros, edição, exportações, temas e configurações ainda são prévias identificadas. Seus comportamentos reais permanecem no aplicativo estável e exigem integração e testes próprios depois da aprovação visual. Não há nova release, tag ou atualização do executável.

Para avaliar, atualize a cópia `reforma/estudo-interface` e execute `noturno_demo.py`, como no [guia do VS Code](GUIA_VSCODE.md). O próximo passo é revisar as três telas no seu Windows e indicar diferenças remanescentes em relação às referências antes de integrar a interface às regras reais.
