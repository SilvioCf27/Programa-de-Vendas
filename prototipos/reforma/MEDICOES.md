# Medições e limites do estudo

Os números abaixo são de processos novos, em Linux com display virtual. Não são medições do seu computador Windows. Foram usadas três repetições para cada volume; a tabela mostra a mediana. Os JSONs ao lado mantêm os resultados individuais.

Ambiente da base: **Linux x86_64**, Python **3.13.5**, Tk **8.6.16**, SQLite **3.46.1**. Banco e lançamentos fictícios em pasta temporária. Nenhuma conta ou rede configurada.

## Programa atual

| Cenário | 224 vendas / 75 lançamentos | 5.000 vendas / 1.667 lançamentos |
|---|---:|---:|
| Abertura até primeira exibição | 743.1 ms | 873.8 ms |
| Primeira entrada em Análises | 78.0 ms | 80.2 ms |
| Primeira entrada em Finanças | 101.6 ms | 135.9 ms |
| Retorno a Finanças | 88.4 ms | 125.7 ms |
| Aplicar Todas as vendas | 413.3 ms | 8185.5 ms |
| Repetir a mesma consulta de todas as vendas | 408.6 ms | 8435.6 ms |

### Gargalo observado neste ensaio

O dimensionamento das colunas domina a atualização de todas as vendas. A consulta ao banco e o preenchimento dos registros são muito menores. Valores abaixo são medianas das três repetições do cenário Aplicar Todas as vendas. Os tempos instrumentados podem estar aninhados; não devem ser somados como etapas independentes.

| Parte instrumentada | 224 vendas | 5.000 vendas |
|---|---:|---:|
| leitura_vendas | 3.8 ms | 60.2 ms |
| insercao_linhas | 1.8 ms | 36.8 ms |
| reconstrucao_analises | 5.3 ms | 92.0 ms |
| preparar_exportacao | 0.6 ms | 13.5 ms |
| dimensionamento_colunas | 373.2 ms | 7876.5 ms |

Isso confirma o custo desse caminho no ambiente do ensaio. Não prova que todo o lag do PC tenha a mesma causa. A medição não inclui rede real, Google Drive ou sincronização autenticada. A entrada em Análises já aproveita dados reconstruídos previamente por Vendas; um clique rápido não significa que sua preparação não teve custo.

**Direção para a etapa de otimização:** evitar medir novamente cada célula quando dados e larguras não mudaram; avaliar larguras proporcionais e medição limitada. Também separar atualização de dados da reconstrução de telas invisíveis. Nenhuma dessas mudanças foi aplicada ao programa estável nesta entrega.

## Protótipos isolados

Mesmos 12 lançamentos, mesmo modelo fictício, área de 1.440 × 960 e referência de 96 DPI. As métricas de abertura e RSS são coletadas antes dos testes de navegação e antes da captura. A inicialização do próprio processo Python fica fora do tempo.

| Protótipo | Primeira exibição (mediana) | RSS antes dos testes (mediana) |
|---|---:|---:|
| Tkinter | 101.2 ms | 24.4 MiB |
| PySide6 | 175.3 ms | 64.4 MiB |

Não comparar esses tempos com o programa completo como se fossem uma aceleração da migração: os protótipos não executam toda a lógica, validações, backups ou sincronização. O tamanho de um novo executável ainda não foi medido. O consumo residente não é o tamanho instalado nem a memória máxima.

## Pendências antes de decidir a migração

- Medir e verificar o comportamento no Windows, com fonte e escala reais.
- Conferir escalas de 100%, 125% e 150%, sem inferir o resultado a partir do display virtual.
- Ensaiar empacotamento de PySide6 e seus plugins, condições de distribuição e atualização a partir do executável estável.
- Validar desempenho de uma tela conectada à lógica real, em banco fictício, caso a proposta PySide6 seja escolhida.
- Avaliar os cinco temas, estados de erro, teclado e acessibilidade na implementação. Nesta prévia há apenas um tema.

Observação de ambiente: SQLite 3.46.1 pertence ao Python usado para este ensaio local de leitura/montagem. Não substitui o runtime Windows publicado (SQLite 3.50.4), não validou restaurações externas e não autoriza reduzir os limites de segurança. As demos de interface não usam SQLite.

## Como reproduzir

Com uma sessão gráfica e Python com as dependências de desenvolvimento da aplicação:
```sh
python prototipos/reforma/medir_base.py
```
Com as dependências do estudo e sessão gráfica:
```sh
python prototipos/reforma/medir_prototipos.py
python -m unittest discover -s prototipos/reforma -p test_estudo.py -v
```

Os scripts de medição escrevem somente resultados do estudo e usam pastas temporárias para os bancos fictícios. O programa estável não foi otimizado nem substituído para obter esses números.
