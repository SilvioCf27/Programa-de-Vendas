# Atualizar o aplicativo Windows

## Primeira vez

O atualizador existe a partir da versão **1.7.0**. Baixe essa versão em
[Releases](https://github.com/SilvioCf27/Programa-de-Vendas/releases/latest),
extraia a pasta inteira e abra `GestaoDaFeira.exe`. Versões anteriores precisam
receber esse primeiro pacote manualmente.

Guarde o aplicativo em uma pasta local própria, por exemplo,
`C:\Users\SeuNome\Aplicativos\GestaoDaFeira`, com permissão de escrita.
Mantenha `_internal` junto ao executável. Evite executar dentro do ZIP, do
repositório, do Drive, de pastas compartilhadas ou de diretórios protegidos como
`Program Files`. Não é necessário abrir como administrador. Os atalhos para
esse executável continuam funcionando depois da atualização.

## Nas próximas versões

1. Abra **Configurações → Atualizações → Verificar atualizações**.
2. Se houver uma versão nova, escolha **Baixar e instalar** e confirme.
3. Aguarde a conferência do pacote, o backup e o reinício do programa.

O programa também consulta a publicação ao abrir, em segundo plano. Essa opção
pode ser desativada na mesma janela. Não instala silenciosamente, não exige
login no GitHub e não envia vendas, configurações, credenciais ou backups. A
conexão informa ao GitHub o IP e a versão do aplicativo, como um download normal.
Sem internet, continue usando a versão instalada e tente depois. A consulta é
feita uma vez por abertura, após a tela aparecer; não consulta a cada minuto.

Só entram **releases estáveis** do repositório oficial
`SilvioCf27/Programa-de-Vendas`, não cada commit. Alterações da PWA continuam
sendo publicadas pelo Cloudflare. Quem executa o código Python deve atualizar
pelo Git; o atualizador não modifica o repositório nem instala Python.

## O que acontece durante a troca

O ZIP e o SHA-256 vêm da mesma publicação oficial, por HTTPS. O programa recusa
domínios externos, versões anteriores, publicações incompletas, tamanho excessivo
e caminhos perigosos no ZIP. Depois de conferir o hash, extrai a candidata em
uma pasta separada e executa `--verificar-pacote` com um banco temporário.
O código dessa verificação é o do pacote publicado: a confiança na conta e na
publicação GitHub continua necessária.

Antes de reiniciar, cria um backup SQLite local verificado. Se o backup no Drive
está configurado, também cria essa cópia. Falha no backup interrompe a instalação;
o envio remoto ainda depende do cliente Google Drive. Formulários abertos e
sincronizações em andamento impedem iniciar a atualização. Feche todas as
outras instâncias do programa.

Um auxiliar PowerShell local, sem perfil ou comandos baixados do servidor,
aguarda o aplicativo fechar, renomeia a pasta anterior e coloca a nova no mesmo
caminho. Não instala serviços nem muda a política permanente do PowerShell. Se
a política da empresa bloquear o auxiliar, o programa não fecha para atualizar.

A nova versão confirma sua abertura depois de criar a interface e carregar os
dados iniciais. Se ela falhar ou não confirmar em um minuto, o auxiliar tenta
recolocar e abrir a anterior. Isso verifica a abertura; não garante que todos
os recursos da versão estejam livres de bugs. A publicação também exige testes
de troca e recuperação no Windows, além de um ensaio com dois binários reais.

## Dados e recuperação

Vendas, despesas, taxas, parcelas e configurações continuam em
`%LOCALAPPDATA%\ProgramFeira` ou no caminho personalizado já configurado. O
atualizador recusa instalações misturadas com a pasta de dados e não troca seu
banco pelo banco inicial vazio do pacote.

A pasta anterior fica ao lado da atual, com o sufixo `.anterior-...`. Os detalhes
da operação ficam em `.feira-atualizacao-...\resultado.txt`, também ao lado da
pasta do aplicativo. Depois de conferir a nova versão, você pode remover as
pastas antigas para liberar espaço. Não remova sua pasta de dados ou seus backups.

Se houver falta de energia, bloqueio de arquivos ou permissão negada no meio da
troca, confira essas pastas antes de mover qualquer coisa. A versão anterior e
o backup local permitem recuperação manual. A cópia do banco tem
`antes-atualizacao` no nome. O auxiliar recupera **arquivos do programa**, não
restaura automaticamente dados nem desfaz migrações do banco; uma restauração
do banco deve ser feita conscientemente, para não perder registros novos.

O pacote ainda não possui assinatura digital de editor. SHA-256 detecta
corrupção, mas não protege contra comprometimento da própria conta/release
GitHub. Proteja essa conta com 2FA. Essas verificações não isolam um computador
já infectado nem substituem antivírus, cópia desconectada e testes de regressão.

## Conferência após atualizar

Confira a versão em **Configurações → Sobre esta versão**, seus totais, uma
despesa parcelada e a sincronização. Não é preciso pedir uma nova auditoria de
todo o código a cada atualização: os testes repetem os cenários conhecidos na
publicação. Relate diferenças inesperadas ou erros encontrados no uso diário.

`VALIDACAO_ATUALIZADOR.json` acompanha a release com o resultado do ensaio no
Windows. O teste não usa a conta Supabase nem o Drive de ninguém.
