# Histórico de vendas no PWA

Aproximação funcional do desktop, mantendo a direção visual aprovada. Implementa busca local por data brasileira/ISO, dia da semana e valor de pagamento/total; filtro de um ou mais dias da semana aplicado junto com o período; e páginas de 12 registros, do mais recente para o mais antigo.

## Escopos

- Período e dias da semana limitam os indicadores e a exportação. Sem dias marcados, todos são considerados. Os arquivos CSV/Excel identificam os dias aplicados.
- Busca e página limitam apenas a lista. Os resumos e a exportação abrangem todos os registros da consulta aplicada, como no desktop. A ajuda explica essa diferença.
- Semana atual, Análises e Finanças continuam independentes.
- Atualizar preserva a busca, a página existente e a seleção já aplicada, sem adotar campos ainda em edição. Mudar a busca ou aplicar uma seleção diferente volta à primeira página.
- Edição/exclusão conservam o ID e a versão do registro exibido. A paginação é ajustada quando a última página deixa de existir. Logout limpa a busca, marcações e registros.

A paginação limita os cartões renderizados, sem mudar o carregamento paginado existente na API. Não houve mudança no SQL, Supabase, autenticação ou desktop. Não há seleção múltipla/exclusão em lote nesta entrega.

## Verificação

Os testes usam somente exemplos fictícios e API simulada. Os novos casos cobrem dias de segunda a domingo, UTC, dias zerados, busca, ordem, limites das páginas, resumo/exportação, filtros em preparação, logout e edição/exclusão na última página. A regressão existente verifica largura de 320, 390 e 1280px, concorrência e regras financeiras. O teste de captura inicialmente usou um seletor que também encontrava outras áreas ocultas; ele foi restringido à área Vendas antes de repetir a verificação.

Interação com dados reais e no aparelho do usuário continua sendo uma conferência posterior à publicação. A falha de atualização automática Windows permanece separada e pendente de diagnóstico.

Resultado: 67/67 testes de regras/dados e 30/30 cenários de navegador aprovados, sem ignorados. Build de revisão sem credenciais reais aprovado. Cache de interface v8. Capturas com exemplos fictícios: [filtro por dia](imagens/historico-pwa/filtro-dias.png) e [última página do histórico](imagens/historico-pwa/historico-pagina.png).
