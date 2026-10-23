A versão **1.4.1** melhora o registro financeiro no desktop e no PWA.

- Datas de despesas com campos explícitos de dia, mês e ano e confirmação visual.
- Cálculo opcional da primeira fatura pela compra, com prévia das parcelas. Compras no próprio dia de fechamento entram na próxima fatura.
- Filtros adaptativos: semana completa, mês e ano, somente ano ou fechamento.
- Taxas da maquininha por semana, preservando a data de cada venda e sem duplicar registros.
- Histórico anual de taxas preservado como opção para totais antigos.
- Fechamento configurável por vigência futura e compartilhado com o PWA, preservando períodos já encerrados.

**Para habilitar a configuração compartilhada do fechamento**, execute apenas `005_fechamentos.sql` no SQL Editor do projeto Supabase já configurado. O script acompanha o ZIP como `SQL_005_FECHAMENTOS.sql` e não altera vendas, despesas ou taxas. O dia 09 continua sendo a regra inicial; as demais melhorias funcionam com a estrutura atual.

[Guia de atualização e finanças](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.4.1/docs/FINANCAS.md) · [SQL 005](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.4.1/supabase/migrations/005_fechamentos.sql)

Baixe **GestaoDaFeira-Windows-x64.zip**, extraia a pasta inteira e abra **GestaoDaFeira.exe**. Mantenha `_internal` junto dele. Não requer instalar Python ou VS Code.

Para atualizar, feche o programa e extraia o pacote em uma pasta separada. Dados, conexão e configurações existentes são preservados. Não substitua seu banco pelo banco inicial do pacote e não refaça a migração das vendas.

`VALIDACAO_WINDOWS.json` registra a verificação do executável no Windows. `SHA256.txt` permite conferir o download. O pacote começa vazio para novos usuários e não inclui os dados usados nos testes. O executável não tem assinatura digital.
