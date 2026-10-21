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

No Windows com Python 3.11 x64, execute `gerar_executavel.cmd`. O resultado fica em `dist/`. As instruções de distribuição e atualização estão em [EXECUTAVEL.md](EXECUTAVEL.md).
