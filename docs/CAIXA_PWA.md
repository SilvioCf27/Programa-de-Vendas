# Dinheiro disponível no PWA

O resultado financeiro do período compara vendas, taxas e despesas. Ele pode
ser negativo mesmo quando há dinheiro guardado antes do início do cadastro.
O quadro **Disponível em caixa e conta** acompanha esse dinheiro separadamente.
Ele não depende do filtro de fechamento, mês ou pagamento aplicado abaixo.

## Habilitar uma vez

No mesmo projeto Supabase usado pelo PWA, abra SQL Editor > New query, cole o
conteúdo completo de [007_caixa.sql](../supabase/migrations/007_caixa.sql) e clique
em Run. Execute após as migrações 001 a 006 já utilizadas. O roteiro pode ser
executado novamente e não importa, apaga nem modifica vendas ou despesas.
Não exige informar senhas ou chaves no programa. Depois reabra o PWA.

Sem essa migração, o novo quadro avisa que o caixa ainda não está habilitado.
Vendas, finanças, filtros e sincronização existentes continuam funcionando.

## Começar

Em Finanças, abra **Informar saldo, movimentar ou conferir**. Selecione
**Saldo inicial (fim do dia)** e informe a data, dinheiro físico e saldo
disponível em conta. Some as contas bancárias se usar mais de uma. Não inclua
limite de crédito, valores de cartão ainda a receber ou reservas indisponíveis.
Zero é aceito. A descrição permite explicar a origem da contagem.

A posição representa o fim do dia escolhido: entradas e saídas dessa data já
estão nos valores informados. O acompanhamento começa no dia seguinte.
Se usar os valores de hoje, finalize os movimentos do dia antes de contar.
Não informe o saldo atual como se fosse o de ontem, pois isso duplicaria as
entradas/saídas de hoje. Saldo inicial não é receita nem lucro.

## O que altera o disponível

| Registro depois da posição inicial, até hoje | Tratamento |
|---|---|
| Venda em dinheiro | Soma ao dinheiro físico |
| Venda em Pix | Soma ao saldo em conta |
| Despesa em dinheiro/Pix | Desconta do respectivo saldo pela data cadastrada |
| Venda no cartão | Aguarda confirmação do recebimento líquido como Entrada |
| Compra no crédito, parcela ou vencimento | Não retira dinheiro automaticamente |
| Pagamento efetivo de fatura | Saída na conta usada, sem outra despesa |
| Taxa do cartão | Já fica descontada ao registrar o recebimento líquido |
| Despesa em Outro | Informe a saída confirmada na conta usada; há um aviso |
| Transferência entre dinheiro e conta | Muda a distribuição; preserva o total |

Não cadastre manualmente outra entrada para vendas em dinheiro/Pix nem outra
saída para despesas desses meios: elas já entram no cálculo automaticamente.
Para cartão, some os depósitos líquidos efetivamente recebidos e registre uma
entrada, identificando o intervalo. Não registre novamente esse recebimento
como venda. Empréstimos recebidos podem ser entradas identificadas, sem virar
venda; o pagamento efetivo sai da conta usada.

## Conferir ou corrigir

**Conferir saldos reais** guarda a contagem e mostra dinheiro/conta informados
menos os valores calculados para o fim daquela data. Isso não redefine o saldo
inicial nem esconde uma diferença. A comparação usa o cadastro atual de vendas
e despesas: uma correção retroativa pode alterar a diferença calculada.

Primeiro procure lançamentos omitidos ou repetidos. Quando houver um ajuste
necessário, registre Entrada ou Saída com motivo claro. Para corrigir uma
operação manual errada, cancele-a no histórico e registre a correta. O registro
cancelado permanece exportável. O saldo inicial só pode ser cancelado se não
existirem outros movimentos ativos; com histórico em uso, faça um ajuste
explícito em vez de reescrever a posição inicial silenciosamente.

## Segurança, cópia e limites desta entrega

Os registros ficam no Supabase, restritos ao proprietário autenticado. Escritas
passam por uma função validada, com recibo de operação, bloqueio contra duas
aberturas e versão no cancelamento. Uma resposta perdida é retomada pelo mesmo
recibo com **Atualizar caixa**; não crie uma nova operação para tentar compensar.
O pedido pendente fica no armazenamento local do navegador, separado por usuário,
até ser confirmado; isso permite retomar após fechar/reabrir a página. Não
contém senha ou chave. A prévia e os saldos são limpos ao sair da conta.
Sem internet, o programa não recebe novos movimentos e não presume saldo atual.

**Exportar histórico de caixa (JSON)** inclui movimentos ativos/cancelados e as
vendas/despesas usadas como base. Guarde esse arquivo como cópia de conferência.
Não há restauração automática desse JSON nesta versão. A exportação financeira
já existente mantém seu escopo; exporte o caixa pelo botão próprio.

Esta implementação é do PWA. O desktop mantém seu funcionamento, e continua
sincronizando vendas/despesas, mas ainda não consulta a nova tabela de caixa.
O backup SQLite no Drive não inclui esses novos registros até a atualização
correspondente do desktop. Eles ficam no Supabase e na exportação própria.
Não há leitura de conta bancária ou recebimento automático de Mercado Pago.

## Verificação

Testes com dados fictícios cobrem corte ao fim do dia, centavos, dinheiro/Pix,
cartão recebido, pagamento de fatura sem duplicar despesa, transferências,
conferência sem redefinição, cancelamento, permissões, recibos, falha de resposta,
SQL ausente, desconexão, logout e snapshot com mais de mil vendas.
O Supabase do usuário precisa receber o SQL; não foi acessado pelos testes.

Validação desta entrega: 100 testes de regras/dados aprovados e 39 cenários de
navegador aprovados; os dois cenários de caixa também foram repetidos após
reforçar a retomada de envio ao reabrir a página. Build web aprovado.
