A versão **1.6.0** calcula automaticamente as faturas pela data da compra no desktop e no PWA.

- No cartão, informe a **data da compra**. Com fechamento no dia 09, uma compra de 09/10 entra na fatura de 09/11 e no filtro de fechamento de outubro.
- Compra e fatura são guardadas separadamente. O prazo de pagamento, como dia 14, não muda esse período.
- Editar só o nome ou a categoria preserva faturas e centavos já registrados. Não há conversão repetida da data para o mês seguinte.
- Registros antigos mantêm a primeira fatura existente. Para informar a compra original, escolha Data da compra no formulário e preencha a data.
- Parcelas seguem o fechamento histórico de cada mês, incluindo fevereiro, anos bissextos e alterações futuras de fechamento.
- Reduzir a compra a uma parcela remove o grupo do parcelamento, permitindo sincronizar normalmente.

**Atualização do Supabase:** execute [006_datas_compras.sql](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.6.0/supabase/migrations/006_datas_compras.sql) no SQL Editor do projeto já configurado. O arquivo acompanha o ZIP como `SQL_006_DATAS_COMPRAS.sql`. Não reclassifica registros antigos e não exige migrar as vendas novamente. Atualize o PC e o PWA juntos.

O aplicativo pode consultar dados antigos antes do SQL, mas não descarta a data de uma compra nova para enviá-la pelo formato anterior. Se houver lote pendente, instale o SQL e use Atualizar/Confirmar envio no PWA ou Sincronizar agora no desktop.

[Guia de finanças](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.6.0/docs/FINANCAS.md)

Baixe **GestaoDaFeira-Windows-x64.zip**, extraia a pasta inteira e abra **GestaoDaFeira.exe**. Mantenha `_internal` junto dele. Não requer instalar Python ou VS Code.

Feche o programa antes de atualizar. Dados e configurações continuam na pasta existente; não substitua seu banco pelo banco inicial do pacote. O pacote público começa vazio e não contém dados pessoais.

`VALIDACAO_WINDOWS.json` registra a verificação do executável no Windows e `SHA256.txt` confere o download. O executável não possui assinatura digital.
