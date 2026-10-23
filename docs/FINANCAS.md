# Finanças: datas, faturas e taxas

## Atualizar a conta já configurada

1. Atualize o desktop e o PWA. Se a PWA instalada ainda mostrar a tela antiga,
   feche todas as janelas do aplicativo e abra novamente.
2. No SQL Editor do projeto Supabase já configurado, execute
   [006_datas_compras.sql](../supabase/migrations/006_datas_compras.sql).
   O arquivo acompanha o executável como `SQL_006_DATAS_COMPRAS.sql`.
   Ele acrescenta a data original da compra e as operações atualizadas, sem mudar
   valores, datas de faturas ou parcelas existentes. É reaplicável.
3. Não refaça a migração das vendas. Não execute novamente 001 a 004.
   Se ainda não instalou o SQL 005 para configurar fechamentos, instale-o também;
   quem já o instalou não precisa repeti-lo.
4. Use as versões atualizadas no PC e no celular. Versões antigas ainda consultam
   o formato anterior, mas não conhecem a data original. Uma escrita antiga nessa
   compra pode remover essa informação, sem alterar a data de fatura por isso.

Sem o SQL 006, consultas antigas continuam disponíveis. Uma compra nova com data
original não é enviada com perda de informação: o aplicativo pede a atualização.
Se já houver um envio pendente, instale o SQL e use Atualizar / Confirmar envio
no PWA, ou Sincronizar agora no desktop, para retomar o mesmo lote.

## Qual data informar

- **Dinheiro, Pix e outros pagamentos:** a data em que a despesa deve entrar nas contas.
- **Cartão de crédito:** a **data da compra**. O programa calcula a primeira fatura
  pelo fechamento vigente e guarda as duas datas separadamente.

A data escolhida permanece visível no formulário. Selecionar crédito calcula a
prévia das faturas, sem substituir a data digitada. Não há botão de conversão.
Compra em 08/10, com fechamento no dia 09, entra na fatura de 09/10. Compra em
09/10 entra na fatura de 09/11: aparece no filtro **Fechamento → Outubro**,
que cobre 10/10 a 09/11. O prazo limite para pagar, como dia 14, é outra informação
e não determina o período do programa.

Em uma compra de 09/09, três parcelas ficam nas faturas de 09/10, 09/11 e 09/12.
Os próximos fechamentos seguem a regra histórica de cada mês, inclusive em
fevereiro, anos bissextos e mudanças futuras de dia. Uma compra antiga começa
na fatura calculada pela data da compra, e não na data em que foi cadastrada.

## Editar sem deslocar o histórico

Editar qualquer parcela abre a **compra inteira**, inclusive parcelas fora do
filtro atual. O total vem da soma das parcelas. Se a compra original estiver
armazenada, ela aparece no formulário. Mudar somente descrição ou categoria
preserva as faturas e os centavos já cadastrados. Mesmo que a regra de fechamento
tenha mudado depois, editar o nome não move uma compra para outro mês.

Registros antigos não tinham a data da compra. Nesses casos o formulário mostra
**Primeira fatura já cadastrada** (no desktop, **Primeira fatura antiga**).
Ela é mantida ao editar. Para informar a data original, escolha **Data da compra**:
o campo é limpo para você preenchê-lo conscientemente. Só então o calendário é
calculado pela compra. Não deduzimos a compra a partir da fatura, pois isso
poderia adiantar ou adiar despesas incorretamente.

## Total e parcelas

Informe sempre o **valor total da compra**. R$ 100,00 em três vezes gera
R$ 33,33, R$ 33,33 e R$ 33,34; a soma fica exata e não são acrescentados juros.
Não altere o total real só para forçar um centavo em uma parcela: o banco pode
distribuir o arredondamento em outra ordem.

Alterar o total redistribui as parcelas. Alterar a quantidade redistribui o mesmo
total; não simula juros de renegociação. A confirmação avisa antes de remover
parcelas quando a quantidade diminui. As parcelas mantidas conservam suas
identificações; uma compra reduzida a uma parcela deixa de ter grupo de parcelamento.

Os valores antigos não são divididos novamente ao atualizar o programa.
Confira o total antes de editar uma compra que foi cadastrada com a regra anterior.
Excluir continua removendo só a parcela selecionada. Se faltarem parcelas ou o
grupo estiver inconsistente, a edição é bloqueada para evitar recriar cobranças
removidas. Confira o histórico ou restaure uma cópia adequada antes de editar.

## Escolher o período

As consultas usam a data da fatura para crédito e a data de pagamento para os
outros meios. Isso também vale para Despesas por semana. A data original da
compra aparece separadamente no lançamento, para conferência.

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
