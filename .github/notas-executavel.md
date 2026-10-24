A versão **1.6.2** reforça a segurança do backup e da restauração.

- Recusa backups com triggers, views ou tabelas virtuais não usados pelo aplicativo. Um teste reproduzia perda de histórico após restaurar um banco adulterado; esse arquivo agora é recusado antes da substituição.
- Recusa pastas redirecionadas por links/junctions e verifica novamente o destino antes de publicar ou remover versões.
- Copia backups externos para uma pasta temporária local antes de abrir SQLite, preservando a compatibilidade com unidades virtuais do Drive.
- Usa leitura defensiva, limites de tamanho e tempo e bloqueio de anexação e extensões na análise de backups.
- Ajusta a finalização de objetos da interface no runtime atualizado, evitando bloqueio durante tarefas de backup e sincronização.
- O relatório do executável registra a versão SQLite e a aprovação da recusa de backup adulterado.

**Não exige SQL novo.** As funções de fatura automática da versão anterior continuam disponíveis; o SQL 006 só precisa ser instalado por quem ainda não o instalou para essas funções.

[Relatório técnico e limites](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.6.2/docs/SEGURANCA.md) · [Verificação Supabase somente leitura](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.6.2/supabase/auditoria_somente_leitura.sql)

Estas proteções reduzem riscos conhecidos de arquivo e caminho. Não são um antivírus, não garantem que o PC esteja limpo e não impedem um vírus com as mesmas permissões de acessar o Drive diretamente. Os backups continuam sem criptografia ou assinatura autenticada. Proteja as contas e mantenha também uma cópia desconectada.

Baixe **GestaoDaFeira-Windows-x64.zip**, extraia a pasta inteira e abra **GestaoDaFeira.exe**, mantendo `_internal` junto dele. Feche a versão anterior antes de atualizar. Não substitua seu banco pelo banco inicial do pacote.

Depois de atualizar, use Fazer cópia agora e confira o arquivo no Drive pelo navegador. O programa confirma a cópia local, e o envio remoto depende do cliente Google Drive.

`VALIDACAO_WINDOWS.json` e `SHA256.txt` acompanham o download. O pacote público começa vazio, não contém dados pessoais e não possui assinatura digital.
