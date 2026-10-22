# Recuperar seus dados

## Conferir uma cópia antes de precisar dela

No computador, abra **Configurações → Verificar integridade do backup…** e selecione uma cópia
`.db`, inclusive a salva na pasta do Google Drive. Aguarde o Drive terminar de
sincronizar o arquivo antes de escolher.

O programa copia o arquivo para uma pasta temporária e restaura essa cópia. Confere
integridade, estrutura e conteúdo de todas as tabelas, inclusive vendas, despesas,
parcelas, taxas e vínculo de sincronização. Também confere a preservação do banco
anterior ao ensaio. Seu banco em uso não é substituído. Se o arquivo estiver
incompleto, inválido ou mudar durante a leitura, o teste é interrompido.

Um teste aprovado confirma aquela cópia, naquele momento. Confira também pelo
navegador se a cópia mais recente chegou ao Drive: a entrega depende do cliente
do Google Drive e da conexão. CSV e Excel são relatórios, não backups completos.

## Se trocar de computador ou perder o banco local

1. Baixe a versão atual do Gestão da Feira e extraia a pasta inteira.
2. Pelo Drive no navegador, baixe a cópia `.db` mais recente para uma pasta local.
   Preserve outra cópia antes de começar. Se não houver cópia utilizável, mas os
   dados estiverem na web, não tente refazer a migração sobre eles: peça orientação
   para recuperar a partir da nuvem.
3. No programa, use **Configurações → Verificar integridade do backup…**. Confira as quantidades
   informadas e, após aprovação, use **Configurações → Restaurar backup…**.
4. Abra Vendas e Finanças e confira as últimas datas, totais e despesas.
5. Em **Configurações → Conexão com a nuvem**, configure o mesmo projeto e a mesma conta.
   Faça login e use **Sincronizar agora** para comparar com os dados online. Não
   use Conferir migração/Transferir dados novamente em uma base já vinculada.
6. Se houver conflito, confira as duas versões antes de escolher. Depois da
   sincronização concluída, confira a web e configure novamente o backup no Drive.

O backup SQLite não inclui a senha, a sessão protegida do Windows ou as configurações
locais do Drive. Uma sessão protegida de outro computador não deve ser copiada:
faça login novamente. A restauração pausa a sincronização automática até a revisão
manual; isso evita enviar dados antigos sem conferir.

## Atualizar o programa ou voltar à versão anterior

Crie e teste um backup antes de atualizar. Feche todas as instâncias, extraia o
novo pacote em outra pasta e abra o novo executável. Ele usa os mesmos dados em
`%LOCALAPPDATA%\ProgramFeira`, sem substituir seu banco pelo banco inicial vazio.
Não abra duas versões ao mesmo tempo para editar.

Se uma atualização apresentar problema, interrompa as edições e preserve um backup
do estado atual. Envie a versão exibida em **Configurações → Sobre esta versão…**, a ação
realizada e a mensagem do erro. Não restaure um backup antigo só para trocar de
executável: ele pode apagar vendas e despesas mais recentes. A reversão deve
considerar a compatibilidade da estrutura do banco.
