# Trabalhando no código

A estrutura mantém a interface separada dos cálculos e do acesso ao banco:

```text
ProgramFeira/
  main.py                 montagem da janela e ações principais
  interface/              telas, tema, ícones e fontes
  database/               consultas SQLite, localização e backups
  assets/                 banco inicial vazio, ícone e fontes
  financeiro.py           despesas, taxas, parcelas e saldo
  comparacao.py            períodos e comparação entre datas
  resumos.py               indicadores das vendas
  exportacao.py            CSV e Excel
  backup_drive.py          cópias para a pasta sincronizada
  nuvem.py                 autenticação e chamadas ao Supabase
  migracao_nuvem.py         transferência inicial com conferência
  sincronizacao.py         comparação de alterações e retomada de envios
  automacao_nuvem.py        agendamento, intervalos e preferência local
  preferencias.py          tema salvo no computador
tests/                    testes e gerador de dados fictícios
tools/                    geração e verificação do executável
docs/                     guias de uso e desenvolvimento
web/                      PWA em desenvolvimento, testes JS e navegador
supabase/migrations/      estrutura e autorização do banco online
```

`executar.py` é a entrada do pacote portátil. `GestaoDaFeira.spec` define os arquivos incluídos pelo PyInstaller. O banco distribuído é `ProgramFeira/assets/banco_inicial.db`: ele contém a estrutura de vendas, sem registros. As tabelas financeiras são preparadas na pasta local do usuário na primeira abertura.

## Testes

Na raiz do projeto:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Os testes criam bancos temporários com exemplos inventados por `tests/dados_ficticios.py`. O banco distribuído deve permanecer vazio. Não use uma cópia das suas vendas como massa de teste.

Os testes gráficos precisam de uma sessão com Tkinter. Sem ela, são marcados como não executados. O GitHub Actions também executa os testes no Windows e verifica o próprio executável antes de disponibilizar o pacote.

Para desenvolver sem abrir seus dados de uso, configure `PROGRAMFEIRA_DATA_DIR` apontando para uma pasta separada. O programa respeita essa variável tanto pelo código quanto pelo executável.

## Dados fora do Git

Bancos de uso, backups, planilhas, exportações, logs e preferências são ignorados pelo `.gitignore`. A única exceção para SQLite é o banco inicial vazio. Antes de publicar uma mudança, confira `git status` e execute os testes.

Apagar um arquivo do commit atual não o remove do histórico do Git. Se dados pessoais já foram publicados, a limpeza precisa considerar commits antigos, tags, Releases e artefatos do Actions. Um clone antigo também pode manter cópias. Não envie dados reais em relatórios de testes ou mensagens de erro públicas.

## Gerar uma versão

No Windows com Python 3.13 x64, execute `gerar_executavel.cmd`. O resultado fica em `dist/`. As instruções de distribuição e atualização estão em [EXECUTAVEL.md](EXECUTAVEL.md).

A sessão persistente do desktop usa `sessao_windows.py` e a DPAPI no escopo do
usuário (sem `LOCAL_MACHINE`), via `ctypes`, sem dependência adicional. O arquivo
contém apenas um blob protegido, vinculado ao projeto; nunca a senha ou o token
de acesso. A renovação grava o novo refresh token antes de consultar os dados.
O teste de DPAPI real é executado somente no Windows; nos demais sistemas são
testados o formato, as falhas e a integração com o provedor substituído.


## Revisão da versão 1.2

Os testes incluem atualização com dados e vínculo existentes, ensaio de restauração
com tabelas financeiras, resposta perdida e retomada de uma resolução de conflito,
mudança de versão entre revisão e envio, download CSV/Excel real no navegador e
agrupamento de fechamentos na virada do ano. O teste de recuperação compara conteúdo
e estrutura de todas as tabelas, sem abrir SQLite na unidade virtual do Drive.

A revisão de conflitos não usa data/hora como desempate: carrega uma fotografia,
confere novamente o conteúdo local e as versões remotas e usa o protocolo de lote
já existente. As escolhas entram na fila durável antes do envio. Nenhuma migração
SQL nova é necessária. Cadastros independentes com a mesma chave natural permanecem
bloqueados para revisão manual.

A exportação web usa `write-excel-file` 4.1.1, carregado sob demanda. Os testes leem
o ZIP/XML do Excel para conferir abas, números, datas e ausência de fórmulas
injetadas. Os gráficos têm valores textuais e não introduzem biblioteca gráfica.
`diagnostico.py` registra somente posições da pilha, sem mensagens, argumentos,
variáveis locais ou trechos de código.

A primeira consulta de auditoria npm retornou HTTP 503. Após a recuperação do
serviço, a checagem apontou o aviso GHSA-px8p-9vwx-vf98 em fflate 0.8.2. A versão
foi atualizada para 0.8.3, inclusive na árvore usada pela exportação. A nova
execução de `npm audit --omit=dev` retornou zero avisos conhecidos nas dependências
de produção. Isso complementa os testes; não substitui a revisão das regras de
acesso ou o acompanhamento de novas correções.

## Abertura e acabamento visual

Os contornos e ícones mantêm em memória a cobertura dos desenhos, separada das
cores. Assim, aplicar uma paleta não recalcula os mesmos cantos e traços para
cada cor. Os caches têm limite; as imagens do Tk pertencem à janela que as usa.
Não há animações nem um temporizador para redesenhar a interface.

Para medir a primeira exibição e uma nova consulta, com sessão gráfica disponível:

```sh
python tools/medir_abertura.py --registros 224
python tools/medir_abertura.py --registros 5000
```

O comando cria e remove seu próprio banco temporário. Os tempos incluem a
montagem da interface e a primeira atualização gráfica, mas não a inicialização
do interpretador, a rede ou a extração de um executável.

Na medição local de 22/10/2026 (Linux, Python 3.12, Tk 9), sem profiler, a abertura
com 224 registros caiu de 1,59 s para 0,71 s após reutilizar os desenhos. Com
5.000 registros, caiu de 1,89 s para 1,09 s. A nova consulta levou cerca de
0,02 s e 0,30 s, respectivamente. São medições deste ambiente; o tempo do
executável no Windows depende também do computador e do antivírus.
