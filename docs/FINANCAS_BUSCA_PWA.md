# Pesquisa e conferência de despesas — PWA

Implementação de 06/11/2026 a pedido do usuário: busca na lista financeira, data da compra em destaque e consulta por meio de pagamento. O saldo e as despesas semanais usam apenas as despesas do meio aplicado; vendas e taxas permanecem completas. Aviso explícito impede interpretar o saldo filtrado como saldo global. A busca altera somente os lançamentos visíveis.

A ordem anterior era por fatura/pagamento, não pela data de cadastro. A nova projeção ordena pela compra/despesa conhecida e mantém a fatura separada. Registros antigos do cartão sem data original aparecem ao final, sem data inventada. Não foram modificados dados, datas persistidas, parcelamentos, SQL, autenticação ou sincronização.

Validação: 70 testes de regras/dados e 31 cenários de navegador aprovados. A regressão inclui larguras 320, 390 e 1280px. O cenário novo confere data de compra versus fatura, cadastro artificialmente posterior que não muda a ordem, pesquisa por descrição/dia/datas/valor, totais intactos durante pesquisa, aplicação do meio, preservação de filtro pendente, taxas/vendas integrais e limpeza no logout. Serviços simulados; não houve acesso ao banco do usuário nem conferência de uma fatura bancária real.

- [Pesquisa e lançamentos](imagens/financas-busca/financas-compra-busca.png)
- [Meio de pagamento](imagens/financas-busca/financas-meio.png)

A melhoria equivalente do desktop tem código e evidências separados na branch de estudo. Atualizar o PWA não troca o executável Windows.
