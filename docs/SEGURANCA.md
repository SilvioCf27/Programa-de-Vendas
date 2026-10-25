# Segurança e limites do backup

Revisão do código em 24/10/2026. Este documento descreve o programa; não publica
configurações particulares das contas de quem o utiliza.

Desde a versão **1.7.0**, o desktop pode consultar e instalar releases oficiais.
Isso acrescenta uma dependência de confiança na publicação GitHub: o pacote
é código executável. O download usa HTTPS, lista restrita de domínios, limites,
SHA-256 e teste isolado antes da troca. Hash e teste não substituem assinatura
digital nem protegem contra uma conta GitHub comprometida. O auxiliar local
PowerShell só troca arquivos do aplicativo após o fechamento; não instala
serviço e não envia dados. Veja [ATUALIZACOES.md](ATUALIZACOES.md) para o fluxo,
o backup anterior, a recuperação e seus limites.

## Onde ficam as permissões

O Cloudflare hospeda a interface da PWA. O Supabase autentica a conta e aplica
as regras do banco. A PWA não tem uma credencial Google Drive nem uma operação
para enviar arquivos arbitrários para ele ou alterar a pasta de backup do PC.
As regras do Supabase precisam estar instaladas corretamente para proteger os dados.

No computador, o programa escreve arquivos SQLite na pasta escolhida. O Google
Drive para computador sincroniza esses arquivos usando a conta conectada nele.
A restrição da pasta no programa não limita as permissões gerais do cliente do
Drive: outro processo executando como a mesma pessoa no Windows pode acessar
pastas sincronizadas sem passar pelo Gestão da Feira.

Quem obtiver a senha do aplicativo poderá tentar alterar dados financeiros; uma
alteração autorizada e sincronizada pode acabar também nos backups. Isso não é
uma autorização para enviar executáveis ao Drive pelo programa. Proteja também
a conta do aplicativo com uma senha exclusiva.

## Correções da versão 1.6.2

Foram reproduzidos dois problemas com bancos fictícios, sem acessar contas reais:

1. Um arquivo SQLite contendo um trigger era aceito na restauração. O trigger
   demonstrado apagava o histórico quando uma nova venda era inserida. Não foi
   demonstrada execução de comandos do sistema operacional. A restauração e o
   ensaio agora recusam triggers, views e tabelas virtuais, que não fazem parte
   do esquema do aplicativo. Backups com esses objetos também não são publicados
   na pasta do Drive. As tabelas normais financeiras e de sincronização são preservadas.
2. A subpasta de backup podia ser um link para outro diretório. Isso exigia a
   capacidade prévia de alterar o sistema de arquivos local. Agora links simbólicos
   e junctions são recusados, com nova conferência antes de publicar ou remover
   versões. O Windows é testado com uma junction real. Isso não constitui um
   isolamento contra um processo malicioso com as mesmas permissões: continuam
   existindo condições de corrida possíveis no sistema de arquivos.

Arquivos selecionados para restauração são copiados para uma pasta temporária
local antes de serem abertos por SQLite. Assim não são executadas operações
SQLite na unidade virtual do Drive. A cópia é comparada com a origem e arquivos
com auxiliares de banco aberto são recusados.

A análise usa somente leitura, `trusted_schema=OFF`, bloqueio de anexação de outros
bancos e funções de extensão/arquivo. Existem limites de tamanho (256 MiB),
conteúdo por campo e tempo das consultas de análise. Eles reduzem a exposição a
arquivos inesperados, mas não substituem atualizações do SQLite ou um antivírus.
Um arquivo inválido é recusado antes de substituir o banco em uso.

A atualização do runtime revelou também coleta de variáveis Tk em uma thread de
sincronização. O descarte de ciclos da interface passou a ocorrer na thread
gráfica ao terminar as tarefas; operações de backup e nuvem sobrepostas são
coordenadas para evitar esse travamento. Os testes cobrem a retomada da coleta
e a preservação dos controles após a conclusão.

## O que os testes comprovam

Os testes verificam preservação do banco após recusa, bloqueio dos dois problemas,
views e tabelas virtuais, anexação e extensões, cancelamento de análise custosa,
limite de arquivo, arquivo executável renomeado, restauração sem abrir SQLite no
Drive virtual e troca de pasta durante a cópia. O empacotamento Windows usa Python 3.13 e exige SQLite 3.50.2 ou mais recente
para analisar backups. Esse piso não comprova ausência de vulnerabilidades futuras.
O pacote Windows é verificado separadamente e registra a versão SQLite em `VALIDACAO_WINDOWS.json`.

`npm audit`, incluindo dependências de desenvolvimento, e `pip-audit` para as
requirements do aplicativo/empacotamento não indicaram vulnerabilidades conhecidas
na consulta de 24/10/2026. A resolução Python foi feita em Linux; dependências
condicionais de outra plataforma e o sistema operacional não são cobertos por
esse resultado. Ausência de avisos nessas bases não comprova ausência de falhas.

Os testes SQL também cobrem acesso anônimo e outra conta, isolamento dos dados,
versões, reenvio sem duplicidade e rollback de lotes. Eles utilizam PostgreSQL em
WebAssembly e dados fictícios, não uma sessão administrativa de produção.

## O que não está garantido

- O aplicativo não é antivírus nem verifica se um PC está livre de malware.
- Um vírus com acesso à conta do Windows pode acessar dados, arquivos do Drive,
  sessões e backups, independentemente dessas verificações. O programa não
  impede exclusão ou ransomware no próprio computador/cliente sincronizador.
- SHA-256 verifica a integridade da cópia durante o transporte. Não comprova
  quem criou o arquivo. Um banco com números adulterados e esquema normal pode
  continuar sendo estruturalmente válido. Não existe assinatura autenticada dos backups.
- Os arquivos `.db` não têm criptografia própria. Criptografia bem implementada
  pode proteger o conteúdo de uma cópia roubada, se a chave permanecer segura;
  não impede infecção, exclusão de arquivos nem roubo de dados antes da criptografia.
- Não se abrem arquivos executáveis da pasta de backup automaticamente. Isso não
  impede alguém que já tenha permissão no Drive de enviar arquivos por outros meios.
- A compatibilidade é testada com uma unidade virtual simulada. O cliente real
  do Drive, permissões remotas, varredura de malware pelo Google, políticas da
  organização e a conclusão do upload não são inspecionados pelo aplicativo.

## Verificar a conta e o projeto

Use pasta restrita sem convidados, confira pessoas com acesso e permissões herdadas,
dispositivos conectados e aplicativos autorizados. Ative dois fatores nas contas
Google, GitHub, Cloudflare e Supabase; guarde os códigos de recuperação em local
seguro e separado. No Supabase, a proteção da conta administrativa é diferente
do login do aplicativo, que continua usando e-mail e senha sem segundo fator próprio.

Proteja as contas que publicam o código: uma conta GitHub/Cloudflare comprometida
pode permitir a troca da página ou dos arquivos distribuídos. A conta administrativa
Supabase pode alterar políticas e dados. Se o acesso ao painel usa um provedor
externo, confira também a proteção desse provedor.

Para conferir a configuração real do banco, execute
[auditoria_somente_leitura.sql](../supabase/auditoria_somente_leitura.sql) no SQL
Editor e examine todos os resultados. O script não modifica dados e não mostra
vendas, despesas, senhas, tokens ou chaves. Tabelas públicas de dados devem ter RLS
ativo; anon não deve ter acesso aos dados ou RPCs. A tabela privada `app_config`
é protegida pela revogação de acesso ao esquema/tabela: RLS falso nela, isoladamente,
não demonstra acesso público.

A revisão deste ambiente não teve uma sessão autenticada nos painéis das contas.
A consulta pública aos cabeçalhos do site publicado foi bloqueada pela rede do
ambiente, portanto os cabeçalhos esperados no código não foram confirmados em produção.

Para recuperação após um comprometimento do PC, mantenha também uma cópia periódica
em um dispositivo desconectado. As sete versões e a cópia mais recente no Drive
ajudam a recuperar erros, mas ficam expostas ao alcance de uma conta/dispositivo
comprometido. Confirme no navegador que o upload terminou.
