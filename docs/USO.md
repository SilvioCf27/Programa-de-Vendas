# Usando o Gestão da Feira

## Vendas e filtros

Cada data tem um registro, com valores de dinheiro, Pix e cartão. O total é a soma dos três. Dias zerados também contam como dias de feira.

Use **Nova venda** para cadastrar. Para corrigir um registro, selecione a linha e clique em **Editar venda**. A exclusão pede confirmação e cria um backup antes de alterar o banco.

Os filtros só mudam a lista depois de clicar em **Aplicar filtros**. Enquanto houver uma mudança pendente, a tela avisa. **Limpar filtros** volta a mostrar tudo. Os relatórios exportados seguem a última seleção aplicada.

Um mês normal vai do primeiro ao último dia. No fechamento, o mês escolhido é o de início: **Na regra inicial, outubro considera 10/10 a 09/11**. Uma nova regra pode ser cadastrada em Finanças com vigência futura, preservando períodos encerrados. A aba Análises permite comparar períodos sem mudar o filtro de Vendas.

## Taxas e despesas

Vendas continuam com os valores brutos. Cadastre as taxas separadamente em **Finanças**. Em Taxas da maquininha, escolha uma semana e preencha o desconto de cada dia. Totais anuais ficam no histórico opcional, para valores antigos consolidados. Use a classificação **Estimada** quando o valor não for confirmado.

Uma taxa anual não é dividida entre os meses. Ela só é descontada quando a consulta inclui todo o intervalo informado. Em recortes menores, o programa avisa que o saldo é provisório. Também não permite descontar a mesma taxa como ajuste anual e lançamento diário.

As despesas podem ser pessoais ou da feira. Para dinheiro e Pix, use a data do pagamento. Para cartão de crédito, use a data em que a compra será paga na fatura. Ao cadastrar parcelas, informe o valor de **cada parcela**, a quantidade e o primeiro pagamento. Editar ou excluir altera somente a parcela selecionada.

Não lance o pagamento da fatura novamente se suas compras já estão cadastradas. A categoria **Compromisso inicial** serve para a parte da fatura que ainda não foi registrada.

A meta é a soma das despesas do período. **Falta cobrir** mostra o que as vendas, descontadas as taxas informadas, ainda precisam alcançar. **Saldo após despesas** mostra a diferença. Como pode incluir contas pessoais, esse saldo não é o lucro contábil da feira nem o saldo do banco.

A consulta de Finanças é independente de Vendas. Ela pode ser semanal, mensal, anual ou por fechamento. Os totais semanais incluem apenas os dias dentro do período consultado. As exportações atuais levam os registros de Vendas; não incluem as despesas.

## Backup no Google Drive

Instale e conecte o **Google Drive para computador**. No programa, abra **Configurações → Backup no Google Drive**, escolha uma pasta sincronizada, salve e use **Fazer cópia agora** para testar.

Ao fechar normalmente, o programa cria uma cópia local verificada e a envia para a pasta escolhida. Mantém o arquivo `gestao-da-feira-ultimo.db` e as sete versões datadas mais recentes. A subpasta se chama `Gestao-da-Feira-Backups`. As cópias incluem vendas, taxas, despesas e parcelas.

Confira pelo navegador se os arquivos chegaram ao Drive. O aplicativo confirma a gravação na pasta; o envio à nuvem depende do Google Drive. Desativar esse recurso não apaga cópias antigas. Falta de energia ou encerramento forçado podem impedir a cópia de saída.

Se houver erro, veja a etapa e os caminhos na mensagem. Confira o espaço no disco local, no cache do Drive e na conta Google. Um teste em uma pasta comum, fora do Drive, ajuda a identificar se a falha está na unidade virtual. O programa prepara o SQLite localmente e confere os arquivos copiados por SHA-256.

## Recuperar os dados

Baixe uma cópia `.db` do Drive, ou escolha um backup local, e use **Configurações → Restaurar backup**. O programa verifica o arquivo e preserva uma cópia do banco atual antes da troca. Feche outras instâncias do aplicativo durante a restauração.

Em outro computador, será necessário configurar novamente o Drive e o tema. O banco ativo fica em `%LOCALAPPDATA%\ProgramFeira` no Windows. No Linux fica em `~/.local/share/ProgramFeira`; no macOS, em `~/Library/Application Support/ProgramFeira`. `PROGRAMFEIRA_DATA_DIR` permite escolher outra pasta.

## Conferir uma atualização

Antes de atualizar, crie um backup. Depois de abrir a nova versão:

1. Compare a quantidade de registros e os totais com a versão anterior.
2. Aplique um filtro conhecido e confira o período mostrado.
3. Exporte um CSV ou Excel e abra o arquivo.
4. Confira os lançamentos da aba Finanças.
5. Faça uma cópia no Drive, feche e reabra o aplicativo.

Não é preciso inserir vendas fictícias no seu banco para fazer essa conferência.

## Usar junto com o celular

Depois de configurar a nuvem e validar o vínculo, abra **Configurações → Conexão com a
nuvem** e entre na sua conta uma vez. No Windows, a sessão fica protegida pela
sua conta do sistema e é recuperada nas próximas aberturas; a senha não é salva.
**Desconectar** remove essa sessão salva do computador. A opção automática consulta a cada minuto e agenda
um envio logo após salvar ou excluir no PC. Ela aguarda o fechamento de formulários de edição. Filtros ainda não
aplicados são preservados e não interrompem a sincronização. O rodapé mostra alterações aguardando envio,
a última atualização ou uma pausa por conflito.

O programa precisa estar aberto e autenticado. Sem conexão, os registros ficam
no banco local e serão enviados quando a conexão retornar. O botão **Sincronizar
agora** continua disponível; desmarque a opção automática se preferir usá-lo.
Confira o status antes de fechar, pois não há um envio final garantido na saída.
Veja a configuração completa em [CELULAR.md](CELULAR.md).


## Conferir pelo celular

A versão web tem as abas Vendas, Finanças e Análises. Em Análises, a comparação
A/B é independente dos filtros das outras abas. A diferença usa B menos A; dias
zerados entram na quantidade e na média. Valores dessa aba são brutos.

Com o aplicativo visível e conectado, a área atual consulta a nuvem a cada minuto.
A consulta aguarda formulários abertos e preserva filtros que ainda não foram
aplicados. Após alterar no computador, aguarde o envio e a próxima consulta no
celular ou use o botão de atualizar. Não é necessário sair e entrar na conta.

## Conferir recuperação, conflitos e evolução

- **Configurações → Verificar integridade do backup…** faz um ensaio em pasta temporária,
  sem substituir os dados em uso. Veja [RECUPERACAO.md](RECUPERACAO.md).
- **Configurações → Conexão com a nuvem → Conferir conflitos…** mostra os registros que
  foram alterados nos dois lados. Escolha PC ou Nuvem para cada um e use Aplicar
  escolhas. Um registro excluído é mostrado explicitamente. O programa cria backup
  e confere se as versões ainda são as mesmas antes de aplicar. Cancelar não altera
  nada. Cadastros independentes na mesma data/ano exigem revisão manual dos cadastros;
  não são unidos automaticamente.
- Em **Análises**, Evolução das vendas agrupa por mês ou fechamento usando os
  filtros aplicados em Vendas. Mostra até 12 períodos consecutivos, com total bruto
  e quantidade de dias. Períodos sem registros ficam identificados; não contam como
  dias de feira. Na web, o gráfico segue a seleção aplicada em Análises.
- No celular, **Vendas → Exportar CSV / Exportar Excel** gera os registros e o resumo
  da seleção aplicada. Alterações de filtros ainda não aplicadas não entram no arquivo.
  O Excel tem abas Vendas e Resumo, com datas e números próprios para cálculos.
  Os arquivos ficam nos downloads ou no local escolhido pelo navegador. Não incluem
  despesas nem ajustes de taxas e não substituem o backup SQLite.

## Relatar um problema

Informe a versão (Configurações → Sobre esta versão), a ação feita, o resultado esperado e
uma captura da mensagem. Erros inesperados da interface e das operações em segundo
plano geram `logs/erros.jsonl` na pasta de dados, quando houver permissão para escrita.
Esse registro tem somente versão, tipo de erro e posições do código: não contém
mensagens do servidor, valores financeiros, senha ou tokens. O histórico é limitado
a dois arquivos de aproximadamente 1 MB. Não publique seu banco ou exportações para
relatar um problema. Erros de inicialização continuam no `logs/inicializacao.log`.

As funções antes agrupadas em Dados ficam na engrenagem ao lado do nome do programa.
Ao passar o mouse sobre **?**, aparece uma explicação breve. **Verificar integridade
do backup** confere uma cópia sem aplicar os dados; **Restaurar backup** substitui
os dados atuais pelos da cópia escolhida, preservando antes uma cópia do estado atual.

As regras de datas, primeira fatura, parcelas, taxas semanais e mudança de fechamento estão no [guia de finanças](FINANCAS.md).
