# Avaliação técnica — Etapas 1 e 3

Esta pasta contém ensaios, não uma nova interface funcional. Não importa o aplicativo para gravar dados, não usa contas nem acessa o banco pessoal. O plano principal continua em [docs/PLANO_REFORMA_DESKTOP.txt](../../../docs/PLANO_REFORMA_DESKTOP.txt).

O relatório e a recomendação estão em [DECISAO_TECNICA.md](DECISAO_TECNICA.md). A decisão de migrar depende da aprovação explícita do usuário.

## Cenários equivalentes

`ensaio_gui.py` usa um único gerador determinístico e as mesmas consultas SQLite para as duas ferramentas:

- 224 ou 5.000 vendas fictícias, uma por data; despesas a cada três dias.
- Vendas, agregação semanal em Análises e lista de Finanças.
- Mesmos valores, cabeçalhos, fonte e volume; SHA-256 e total da consulta conferidos entre cada par de processos.
- Tabelas paginadas em 50 registros nos fluxos normais. Um cenário separado preenche todos os registros.
- Primeira exibição, consulta mensal, retorno a todas as vendas, primeira visita e navegação por telas já construídas, abertura/fechamento de detalhe e 40 ciclos de uso por processo.
- Cinco processos novos por ferramenta/volume, alternando a ordem. O cache do sistema operacional não é apagado: não é um ensaio de inicialização fria do PC.
- Tk usa `ttk.Treeview`; Qt usa `QTableView` e modelo. São APIs idiomáticas para a mesma operação, não interfaces pixel a pixel idênticas.
- O quadro de 1.280 × 800 é solicitado às duas ferramentas; a dimensão efetiva é registrada, pois o Windows pode limitar a janela ao monitor. A VM final é preparada em Full HD e restaurada ao fim.

Os cenários são de leitura/apresentação. Não implementam compra parcelada, edição, exclusão, autenticação ou sincronização como parte de outra interface. Esses comportamentos continuam no aplicativo estável e nos seus testes. O esquema do SQLite temporário é exclusivamente do ensaio; não é uma proposta de migração do banco real.

### Como interpretar os tempos

Abertura interna inclui importação da ferramenta e criação/exibição dos controles; exclui criação do banco e inicialização do interpretador. `processo_total_ms` inclui todos os ciclos e não é tempo de abertura.

`consulta_*` mede a consulta/agregação compartilhada, sem forçar pintura. Atualização e navegação incluem entrega de eventos e pintura pendente. Tempos podem conter diferenças do backend gráfico/VM. O relatório usa medianas por processo e a mediana das cinco repetições. `p95_ms` está registrado por cenário/processo, não é um intervalo de confiança.

Tk executa `update`; Qt executa `processEvents` e processa eventos de destruição adiados, reproduzindo a liberação que ocorreria no loop normal. Diálogos vivos ao fim devem ser zero nas duas ferramentas. Isso evita atribuir ao Qt memória de janelas cuja destruição ainda não foi processada pelo ensaio.

### Memória

RSS é coletado após exibição, depois da carga completa e ao final. Há amostragem a cada 10 ms e, quando disponível, pico do processo fornecido pelo SO. O pico do SO inclui a preparação do processo; os dados são iguais nas duas ferramentas. Registra-se RSS a cada cinco ciclos e crescimento após a carga, sem afirmar que toda diferença é vazamento ou que um ensaio curto prova estabilidade por dias.

### Escalas, temas e acessibilidade

`verificar_escalas.py` exercita fatores de aplicação 1/1,25/1,5, sem modificar o DPI do monitor. Tk recebe escala de fonte e tamanho físico; Qt recebe fator de dispositivo. Dimensões Tk estão em pixels de janela e Qt em unidades lógicas; precisam dessa distinção ao comparar fatores maiores que 1.

As cinco paletas existentes são lidas como literais do código, sem executar módulos de produção ou mudar seus valores. As mesmas paletas são renderizadas no cenário técnico e seus pares centrais de contraste são calculados. Isso testa viabilidade, não conclui a adaptação dos cinco temas da nova interface.

O ensaio injeta a tecla Down e verifica seleção/foco. No Windows, uma consulta UI Automation coleta nomes e tipos de elementos da própria janela; o loop continua atendendo mensagens durante a consulta. A saída é gravada em arquivo para não bloquear a coleta pelo limite do pipe. Não equivale a uma sessão com NVDA/JAWS, alto contraste ou teste de todas as ações por teclado.

### Empacotamento

`empacotar_ensaio.py` gera somente `EnsaioTk` e `EnsaioQt`, em diretório indicado pelo avaliador, com PyInstaller em modo pasta. Cada variante exclui a outra ferramenta e carrega o mesmo conjunto de recursos. O Qt inclui o renderizador SVG utilizado pela identidade aprovada.

Os dois binários são executados com PATH restrito e variáveis do venv removidas. O próprio processo confirma `frozen=True`, dados/totais e seleção. Isso prova o funcionamento do pacote de ensaio naquele runner; não é uma máquina física nova sem Python, nem teste da atualização do aplicativo real. Não há release ou pacote aceito pelo atualizador do Gestão da Feira.

## Reproduzir no Windows

Use a cópia de estudo e um ambiente separado, sem substituir seu programa:

```powershell
py -3.13 -m venv .venv-avaliacao
.\.venv-avaliacao\Scripts\python.exe -m pip install -r prototipos/reforma/avaliacao/requirements.txt
.\.venv-avaliacao\Scripts\python.exe prototipos/reforma/avaliacao/executar_comparacao.py --uia --saida D:\Feira2026\resultado-comparacao.json
.\.venv-avaliacao\Scripts\python.exe prototipos/reforma/avaliacao/verificar_escalas.py D:\Feira2026\resultados-escalas
.\.venv-avaliacao\Scripts\python.exe prototipos/reforma/avaliacao/empacotar_ensaio.py --saida D:\Feira2026\pacotes-estudo
```

O helper `tela_windows.py` é usado somente na VM efêmera de CI, com restauração. Não é necessário executá-lo no computador do usuário. Não muda o DPI real: ajusta a resolução da VM para o ensaio de janela.

`verificar_suites.py` roda os testes existentes com `PROGRAMFEIRA_DATA_DIR` apontando para pasta temporária. A suíte de produção requer SQLite compatível com o mínimo de segurança dos backups; não reduza esse mínimo para fazer um teste passar.

## Evidências e isolamento da versão estável

O workflow `avaliacao-interface-windows.yml` executa apenas na frente de estudo. Relatórios são preservados em um ramo com ID da execução para permitir leitura via Git quando a API estiver indisponível. Não há tag, release, alteração da PWA ou publicação de novo executável estável.

Somente JSONs e documentação dos resultados finais são incorporados aqui; os binários, bancos e pastas de build ficam fora do repositório. A comparação técnica não autoriza a Etapa 4.
