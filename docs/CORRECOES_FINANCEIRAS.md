# Aplicar um plano de correções financeiras

A PWA permite aplicar um arquivo JSON de correções previamente revisado. Não é importação de CSV, restauração de backup nem acesso remoto para terceiros. Continua usando o login, RLS e o protocolo transacional existentes. Selecionar um arquivo não modifica registros.

## Fluxo

1. Em Finanças, abra **Aplicar correções de conferência**, selecione o plano e clique em **Conferir plano**.
2. A aplicação busca um snapshot novo e confere IDs, versões e todos os campos esperados dos registros. A prévia mostra as exclusões, atualizações/validações e valores anteriores/posteriores. O histórico fora do filtro visível também pode ser afetado, conforme o plano.
3. Baixe a **cópia financeira antes das correções** e guarde o arquivo. Ela é uma exportação JSON do snapshot fresco; sua serialização é reaberta e comparada antes do download. Não é um backup completo do SQLite, de vendas ou de configurações, nem há restauração automática desse formato. O navegador não comprova que o usuário guardou o download: por isso há uma confirmação explícita de que a cópia foi salva.
4. Marque que guardou a cópia e conferiu a prévia. Ao clicar em Aplicar, há nova leitura, nova conferência e confirmação final. Cancelar não envia o lote.
5. O envio reutiliza o lote/recibo persistido antes da requisição. Se a resposta se perder, Atualizar retoma o mesmo lote, sem novas exclusões. Se um registro mudou, a versão faz a transação recusar o lote; é preciso reconferir os dados e gerar novo plano.

## Restrições

Somente despesas da tabela financeira. O formato 1 mantém as ações editar/excluir. O formato 2 admite completar parcelas faltantes em grupos já existentes, com ID novo e ausência verificada, quando o grupo final fica completo. Não permite inserções livres, troca de IDs existentes nem alteração de vendas, ajustes anuais, login ou configurações. Todos os membros atuais dos grupos envolvidos precisam estar no plano, inclusive linhas preservadas, que são validadas/atualizadas na mesma transação para conferir suas versões. O resultado deve manter os grupos restantes com parcelas completas e metadados coerentes. Datas/valores/tipos/meios/categorias e limites são validados; não há execução de SQL ou código contido no arquivo. Arquivos são limitados a 512 KiB e 500 operações.

A proteção de acesso ao proprietário é a já existente no servidor. O arquivo não concede permissão e não contém credenciais. A conta usada precisa ter exatamente os registros esperados; outra conta, mudança de conteúdo/versão ou tentativa de reaplicar o mesmo plano é recusada. Logout remove a prévia e o arquivo selecionado. O arquivo com dados reais da conferência não faz parte do repositório público; planos de teste usam apenas dados fictícios.

## Verificação

79 testes de regras/dados aprovados. Regressão completa de 34 cenários de navegador aprovada; três testes dirigidos de correções também aprovados, incluindo mais um cenário de resposta perdida (35 cenários distintos verificados). Testes cobrem cópia obrigatória, prévia sem gravação, cancelamento, sucesso, registro não envolvido preservado, grupo incompleto, versão/conteúdo alterado, tabela indevida, IDs repetidos, recusa de reaplicação e retomada por recibo. Build web aprovado.

Na primeira rodada, a classe CSS compartilhada tornava ambíguo o seletor do teste de exportação; os painéis foram separados. O teste de cancelar e confirmar precisava aguardar a resolução do primeiro diálogo, para não instalar dois manipuladores sobre a mesma confirmação; ajustado e repetido. Nenhuma dessas rodadas fez alterações em conta real. APIs simuladas e PostgreSQL de teste; o agente não acessou nem alterou o banco do usuário.

[Prévia com dados fictícios](imagens/correcoes-financeiras.png).

Cache de interface v12. Sem mudança de SQL, desktop ou release Windows.


## Formato 2: completar parcelas faltantes

O formato 2 usa uma verificação explícita de ausência para o ID da parcela a incluir (`versao: null`, `campos: null`). Se esse ID já existir, o plano é recusado. A inserção precisa pertencer a um grupo existente e totalmente coberto pelo lote. O plano declara data de compra, total em centavos e quantidade; o resultado é comparado com `lancamentoFormulario`, o mesmo cálculo usado no cadastro, incluindo todas as datas de fatura e o rateio de centavos. Grupos incompletos, parcelas repetidas, soma/datas diferentes ou regra de fechamento incompatível são recusados.

As regras de fechamento são consultadas novamente antes da prévia e antes de aplicar. A primeira fatura considera a data de compra e as vigências cadastradas; não é deduzida de um registro de parcela intermediária. Os planos de formato 1 continuam compatíveis. A prévia e a confirmação distinguem exclusões, atualizações/validações e inclusões de parcelas. Não há alteração de SQL ou de regras financeiras.

Validação desta extensão: 83 testes de regras/dados e 36 cenários de navegador aprovados; a última revisão dos testes usa somente datas e valores fictícios. Os casos novos cobrem inclusão em grupo existente, total exato, ID já ocupado, ausência de conferência de faturas, primeira fatura inválida, mudança futura de fechamento, aplicação e recusa de reaplicação. Build aprovado. Planos e arquivos reais recebidos para conferência permanecem fora do repositório público.

Cache da interface v13. Nenhuma atualização de executável Windows nesta entrega.

## Formato 3: conciliação com documentos

Permite incluir despesas à vista do cartão identificadas em uma referência de
fatura. O plano contém o intervalo de fechamento, o total em centavos e os
movimentos associados aos IDs do cadastro. Movimentos agrupados, como pedágios,
somam para um registro; não criam gastos duplicados. A referência é fornecida
pelo usuário: não é assinatura digital nem acesso ao banco.

Em uma conciliação completa, todos os gastos de cartão no intervalo precisam
corresponder aos movimentos e ao total declarado. Uma referência parcial
confere apenas os itens apresentados e não certifica o total do período.
Inclusões precisam ser despesas à vista do cartão cobertas pela referência.
Pix e dinheiro existentes não podem ser editados por este formato. A
reclassificação de cartão para Outro preserva o valor. Totais de compras
expressamente confirmados podem ser declarados em `totais_preservados` e são
conferidos antes e depois. As verificações de versão, grupo completo, cópia,
confirmação e envio transacional continuam obrigatórias.

Este formato admite os valores efetivamente faturados, que podem diferir do
rateio estimado pelo cadastro. As datas de compra e o cronograma devem ser
revisados no plano; uma fatura isolada não comprova todos os pagamentos antigos.
Não há alteração de SQL, executável ou dados de conta real pelo agente.

Verificação local do formato 3: 89 testes de regras/dados e 37 cenários de
navegador aprovados, incluindo cópia antes de aplicar, inclusão documentada,
preservação de Pix e recusa de reaplicação. Build aprovado. Os testes usam
referências fictícias. Cache da interface v14. A aplicação em conta real e
uma publicação permanecem etapas separadas da validação local.
