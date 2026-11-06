# Pesquisa e filtro de pagamento nas finanças Qt

A pedido do usuário, a busca por descrição, data brasileira/ISO, dia da semana, meio, categoria e valor do lançamento foi adicionada à lista financeira. Ela atua somente na lista e respeita o recorte Todos/Despesas/Taxas/Parcelas, sem alterar resumo ou semanas. A seleção da tabela é limpa ao mudar a busca, como em qualquer novo preenchimento, evitando exclusão de linhas ocultas.

O seletor **Despesas por pagamento** integra a consulta aplicada: Todos, Dinheiro, Pix, Cartão de crédito e Outro. Limita despesas, saldo, falta e semanas. Vendas e taxas permanecem completas. Um aviso explícito indica que o saldo filtrado não representa todas as despesas. Alterar o seletor não altera resultados até Consultar; atualização de nuvem usa o filtro aplicado. Limpar volta a Todos e limpa a busca.

A ordem é pela data da compra/despesa conhecida; a fatura/pagamento continua definindo o período financeiro. A coluna inicial mostra a compra quando disponível, a data informada de uma despesa à vista, a venda correspondente a uma taxa ou “Não informada” para uma compra antiga no cartão sem data original. Estas ficam ao final, sem inventar uma compra nem migrar datas persistidas. Cadastro recente não muda a cronologia.

Nenhuma tabela ou regra de parcelamento/fechamento foi alterada. As modificações ficam no adaptador/tela Qt e na projeção local de pesquisa, preservando o núcleo funcional, o SQLite e a sincronização. A busca equivalente e o filtro já têm implementação própria na PWA.

[Captura Linux com dados fictícios](imagens/financas-busca.png). A captura do estudo não equivale ao executável instalado. Não há nova versão Windows publicada nesta entrega: mudanças de código precisam do fluxo de validação/empacotamento antes de chegar ao executável. Não foi alterada a versão 2.0.0, a tag ou a release existente.

## Verificação local

Regressão Qt Linux: 188 testes executados, 186 aprovados e dois testes nativos de DPAPI/Windows ignorados, sem falhas ou erros. [Relatório](resultados/financas-busca-linux/qt.json). Python 3.12.14, SQLite 3.53.1 e Qt 6.10.2. Os 25 testes financeiros foram repetidos na revisão final (todos aprovados), incluindo filtro de pagamento pendente versus aplicado, resumo completo de taxas/vendas, busca sem alterar totais, coluna de compra e Limpar. Dois testes de projeção sem interface cobrem datas/ordem/legado e busca. Nenhuma chamada a Supabase, Drive ou dados pessoais.

As alterações da PWA têm 70 testes de regras/dados e 31 cenários de navegador aprovados. O push da branch de estudo aciona os workflows Windows e de pacote candidato; iniciar esses workflows não equivale a aprovar seus resultados nem a publicar um novo executável.
