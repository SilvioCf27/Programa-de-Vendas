# Finanças: datas, faturas e taxas

## Atualizar a conta já configurada

1. Atualize o desktop e o PWA. No navegador, atualize a página; se a PWA instalada
   ainda mostrar a tela antiga, feche as janelas do aplicativo e abra novamente.
2. Para habilitar **Configurar fechamento**, abra o SQL Editor do mesmo projeto
   Supabase e execute apenas [005_fechamentos.sql](../supabase/migrations/005_fechamentos.sql).
   O arquivo também acompanha o executável como `SQL_005_FECHAMENTOS.sql`.
3. Não é necessário executar novamente as migrações 001 a 004, migrar as vendas
   outra vez ou refazer a conexão. A migração 005 é reaplicável e não modifica
   vendas, despesas, parcelas ou taxas existentes.
4. O dia 09 continua sendo a regra inicial. Só use **Configurar fechamento** se
   quiser cadastrar uma mudança futura. Faça essa mudança com as duas versões
   atualizadas, para que mostrem os mesmos períodos.

Sem a migração nova, o registro de despesas e taxas, os filtros adaptativos e a
sincronização financeira existente continuam disponíveis com a regra inicial.

## Qual data informar

- **Dinheiro, Pix e outros pagamentos:** a data em que a despesa deve entrar nas contas.
- **Cartão de crédito:** a primeira fatura em que a compra será cobrada, identificada
  pelo fechamento. Ela é diferente da data da compra e do prazo limite para pagar.

Os campos Dia, Mês e Ano mostram a data selecionada antes de salvar. Mudar o meio
de pagamento, a categoria ou a quantidade de parcelas não desloca a data.
Se você informou a data da compra, use **Calcular primeira fatura**. Essa ação é
explícita: não modifica silenciosamente uma data já preenchida.

Com fechamento no dia 09, uma compra de 08/09 entra na fatura de 09/09; uma compra
de 09/09 entra na fatura de 09/10. Em três parcelas a partir de 09/10, os
lançamentos serão 09/10, 09/11 e 09/12. O valor informado é **de cada parcela**.
O prazo limite de pagamento, como dia 14, não muda a identificação dessa fatura.

Datas antigas não são corrigidas automaticamente: a data da compra original
não estava armazenada para permitir essa dedução com segurança. Confira os
lançamentos que suspeitar estarem incorretos e edite somente os necessários.
Editar ou excluir uma parcela continua afetando apenas aquela parcela.

## Escolher o período

- **Semana:** escolha mês, ano e uma semana identificada pelo intervalo completo,
  de segunda a domingo. Uma semana pode começar no mês anterior ou terminar no seguinte.
- **Mês:** escolha mês e ano; o recorte é o mês civil completo.
- **Ano:** aparece apenas o ano.
- **Fechamento:** escolha mês e ano; o recorte segue a regra histórica. Confira as
  datas exibidas. A regra inicial é de 10 ao dia 09 seguinte.

Alterar os campos não aplica a consulta até clicar em **Consultar**. Atualizações
em segundo plano preservam os filtros que ainda estão sendo preparados.

## Taxas da maquininha

São os descontos cobrados sobre suas vendas no cartão, informados **em reais**.
Não são despesas feitas com seu cartão de compras e não são uma porcentagem aplicada
pelo programa.

Escolha a semana e preencha os dias em que houve desconto. Você pode registrar
sexta e domingo juntos, ou qualquer outro dia. Cada taxa fica na data da venda,
mesmo se a semana cruzar um mês ou fechamento. O lote é salvo por inteiro ou recusado
por inteiro. A tela permite atualizar taxas já cadastradas, sem duplicar a data.
Campo vazio mantém o registro anterior; use **Excluir** no lançamento para removê-lo.

Os totais históricos anuais existentes continuam identificados como confirmados
ou estimados. Dias cobertos por eles ficam bloqueados na tela semanal, para evitar
descontar a mesma taxa duas vezes. Um total histórico não é dividido por meses ou
semanas: um recorte que não cobre o intervalo inteiro continua marcado como provisório.

## Mudar o dia de fechamento

A nova regra só pode valer a partir de uma fatura de um mês futuro. O histórico
compartilhado é consultado pelo desktop e pelo PWA; não é uma preferência de cor
salva separadamente em cada aparelho.

Exemplo: mudar de dia 09 para dia 14 a partir da fatura de novembro:

- Setembro continua de 10/09 a 09/10.
- O período ainda aberto de outubro passa a 10/10 a 14/11.
- Novembro fica de 15/11 a 14/12.

Isso evita lacunas e sobreposição, preservando os períodos encerrados. O período
em andamento pode ficar mais curto ou mais longo; a tela mostra uma prévia antes
de salvar. Um dia inexistente no mês, como 31 em fevereiro, usa o último dia.

A mudança ajusta consultas e o cálculo da primeira fatura. Ela não muda valores,
não transfere parcelas antigas para outras datas e não edita seus registros.
Confira os vencimentos futuros se o banco também os alterar. O desktop guarda uma
cópia da regra no banco local, com backup antes de atualizar; sem internet, continua
usando a última regra recebida. Para cadastrar uma mudança, conecte a conta.
