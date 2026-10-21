# Gestão da Feira

Um aplicativo para anotar as vendas das feiras, acompanhar os resultados e organizar as contas. Feito em Python, com Tkinter e SQLite.

## Usar no Windows

Baixe o arquivo **GestaoDaFeira-Windows-x64.zip** em [Releases](https://github.com/SilvioCf27/Programa-de-Vendas/releases/latest), extraia a pasta inteira e abra **GestaoDaFeira.exe**. A pasta `_internal` precisa ficar junto dele. Não é necessário instalar Python.

O programa começa vazio para quem está usando pela primeira vez. Se você já usa o Gestão da Feira, ele abre o banco local existente. Atualizar o programa não apaga suas vendas.

## O que dá para fazer

- Cadastrar, editar e excluir vendas por data, separando dinheiro, Pix e cartão.
- Filtrar por ano, mês, dia da semana ou fechamento de **10 a 09**.
- Comparar períodos e exportar vendas para CSV ou Excel.
- Registrar taxas, despesas e parcelas, acompanhando quanto falta para cobrir as contas.
- Criar backups e salvar cópias em uma pasta do Google Drive.

A aba **Vendas** mostra valores brutos. A aba **Finanças** desconta as taxas e despesas que você informar. Os botões **?** explicam os cálculos na própria tela.

## Onde estão os dados

No Windows, o banco fica em `%LOCALAPPDATA%\ProgramFeira\vendas.db`, fora da pasta do programa. A configuração do Drive e o tema também ficam nessa pasta. O repositório só contém um banco inicial vazio; vendas, planilhas, relatórios e backups pessoais não devem ser enviados ao GitHub.

Os testes criam dados fictícios em pastas temporárias. Não usam o banco pessoal e não preenchem o banco distribuído com o aplicativo.

## Executar pelo código

Instale Python 3.11 com Tcl/Tk. Na pasta do projeto:

```sh
python -m pip install -r requirements.txt
python -m ProgramFeira.main
```

No Windows também é possível usar `py` no lugar de `python`. No Linux, pode ser necessário instalar `python3-tk`. O pacote openpyxl é usado apenas na exportação Excel.

Para atualizar o código, feche o programa e execute `git pull --ff-only`. Um executável já baixado não muda com esse comando: para atualizá-lo, baixe a nova versão em Releases.

## Guias

- [Vendas, finanças e backups](docs/USO.md)
- [Executável: instalar, atualizar e gerar](docs/EXECUTAVEL.md)
- [Estrutura do projeto e testes](docs/DESENVOLVIMENTO.md)

## Versão para celular — em desenvolvimento

A primeira etapa da PWA está em `web/`, com login pessoal e vendas online. O acesso ainda precisa ser configurado nas contas gratuitas do Supabase e Cloudflare Pages. Não há sincronização com o desktop nesta etapa, nem importação dos seus dados. O executável atual continua funcionando normalmente.

O guia de configuração e os limites desta etapa estão em [CELULAR.md](docs/CELULAR.md).
