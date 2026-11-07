# Aplicar um plano de correções financeiras

A PWA permite aplicar um arquivo JSON de correções previamente revisado. Não é importação de CSV, restauração de backup nem acesso remoto para terceiros. Continua usando o login, RLS e o protocolo transacional existentes. Selecionar um arquivo não modifica registros.

## Fluxo

1. Em Finanças, abra **Aplicar correções de conferência**, selecione o plano e clique em **Conferir plano**.
2. A aplicação busca um snapshot novo e confere IDs, versões e todos os campos esperados dos registros. A prévia mostra as exclusões, atualizações/validações e valores anteriores/posteriores. O histórico fora do filtro visível também pode ser afetado, conforme o plano.
3. Baixe a **cópia financeira antes das correções** e guarde o arquivo. Ela é uma exportação JSON do snapshot fresco; sua serialização é reaberta e comparada antes do download. Não é um backup completo do SQLite, de vendas ou de configurações, nem há restauração automática desse formato. O navegador não comprova que o usuário guardou o download: por isso há uma confirmação explícita de que a cópia foi salva.
4. Marque que guardou a cópia e conferiu a prévia. Ao clicar em Aplicar, há nova leitura, nova conferência e confirmação final. Cancelar não envia o lote.
5. O envio reutiliza o lote/recibo persistido antes da requisição. Se a resposta se perder, Atualizar retoma o mesmo lote, sem novas exclusões. Se um registro mudou, a versão faz a transação recusar o lote; é preciso reconferir os dados e gerar novo plano.

## Restrições

Somente despesas da tabela financeira, com ações editar/excluir. Não permite inserir, trocar IDs, alterar vendas, ajustes anuais, login ou configurações. Todos os membros atuais dos grupos envolvidos precisam estar no plano, inclusive linhas preservadas, que são validadas/atualizadas na mesma transação para conferir suas versões. O resultado deve manter os grupos restantes com parcelas completas e metadados coerentes. Datas/valores/tipos/meios/categorias e limites são validados; não há execução de SQL ou código contido no arquivo. Arquivos são limitados a 512 KiB e 500 operações.

A proteção de acesso ao proprietário é a já existente no servidor. O arquivo não concede permissão e não contém credenciais. A conta usada precisa ter exatamente os registros esperados; outra conta, mudança de conteúdo/versão ou tentativa de reaplicar o mesmo plano é recusada. Logout remove a prévia e o arquivo selecionado. O arquivo com dados reais da conferência não faz parte do repositório público; planos de teste usam apenas dados fictícios.

## Verificação

79 testes de regras/dados aprovados. Regressão completa de 34 cenários de navegador aprovada; três testes dirigidos de correções também aprovados, incluindo mais um cenário de resposta perdida (35 cenários distintos verificados). Testes cobrem cópia obrigatória, prévia sem gravação, cancelamento, sucesso, registro não envolvido preservado, grupo incompleto, versão/conteúdo alterado, tabela indevida, IDs repetidos, recusa de reaplicação e retomada por recibo. Build web aprovado.

Na primeira rodada, a classe CSS compartilhada tornava ambíguo o seletor do teste de exportação; os painéis foram separados. O teste de cancelar e confirmar precisava aguardar a resolução do primeiro diálogo, para não instalar dois manipuladores sobre a mesma confirmação; ajustado e repetido. Nenhuma dessas rodadas fez alterações em conta real. APIs simuladas e PostgreSQL de teste; o agente não acessou nem alterou o banco do usuário.

[Prévia com dados fictícios](imagens/correcoes-financeiras.png).

Cache de interface v12. Sem mudança de SQL, desktop ou release Windows.
