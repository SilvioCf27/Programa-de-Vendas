# Primeira versão para celular

A versão web fica em `web/`. Ela pode ser instalada na tela inicial do celular como PWA. O programa de Windows continua funcionando com seu banco local.

Estão disponíveis login pessoal, cadastro, edição, exclusão e consulta de vendas, além da aba Finanças. Os filtros de vendas incluem mês, ano e fechamento de 10 a 09. Valores zerados contam como dias de feira. Finanças mostra valores após taxas, despesas e saldo, com lançamentos, parcelas e ajustes anuais. Análises permite consultar pagamentos, dias da semana e comparar datas, meses, fechamentos e intervalos. CSV e Excel também podem ser exportados na aba Vendas do celular.

**A sincronização pode ser automática:** depois da migração e do vínculo inicial, ative a opção em **Configurações → Conexão com a nuvem** e entre na sua conta. O desktop aberto consulta a cada minuto; **Sincronizar agora** continua disponível. Nenhum dado pessoal acompanha o código ou é importado automaticamente. Configure o projeto e valide o vínculo antes de usar as duas versões.

## Serviços escolhidos

- **Supabase:** conta de acesso e banco PostgreSQL.
- **Cloudflare Pages:** hospedagem dos arquivos da interface.

Use as opções **Free**, sem ativar serviços pagos. Os fornecedores podem mudar cotas e condições; confira os limites exibidos na sua conta antes de publicar. Projetos gratuitos podem ter restrições de uso ou pausa por inatividade. Esta configuração não contrata nada e não exige cadastrar cartão no aplicativo.

O endereço gratuito `pages.dev` é suficiente. Não é necessário comprar um domínio ou manter um servidor Python ligado. O backup atual do desktop no Drive continua funcionando, mas não faz backup automático do banco Supabase; precisaremos preparar a recuperação dos dados online antes do uso definitivo.

## Criar o acesso no Supabase

1. Crie uma conta e um projeto no plano gratuito em https://supabase.com . Guarde a senha do banco apenas com você.
2. Em **Authentication**, desative a criação pública de usuários: a opção costuma se chamar **Allow new users to sign up**. A interface não tem cadastro, mas essa configuração também precisa ser desativada no serviço.
3. Crie sua conta de acesso em **Authentication → Users → Add user**, usando e-mail e senha. Confirme o usuário pelo painel, se essa opção aparecer. O aplicativo usa esse login; a senha não entra no código.
4. Abra **SQL Editor** e execute o conteúdo de [`supabase/migrations/001_vendas.sql`](../supabase/migrations/001_vendas.sql).
5. Copie o UUID da sua conta, mostrado em Authentication → Users. No SQL Editor, execute o comando abaixo, substituindo `SEU_UUID` pelo UUID. Não use seu e-mail nesse campo.

```sql
insert into private.app_config(singleton, owner_id)
values (true, 'SEU_UUID'::uuid)
on conflict(singleton) do update set owner_id = excluded.owner_id;
```

Sem esse último comando, ninguém tem acesso às vendas. A proteção fica no banco, não apenas na tela. Usuários anônimos e outras contas não podem ler ou alterar os registros. O proprietário é configurado pelo painel administrativo, nunca pelo aplicativo.

Em **Project Settings → API / API Keys**, localize a **Project URL** e a chave **publishable**, ou a antiga **anon key**. Essas duas informações são públicas por definição; a proteção dos dados depende das políticas de acesso aplicadas pela migração SQL.

**Nunca use a `service_role`, uma chave `sb_secret_...`, a senha do banco ou seu token pessoal do Supabase no frontend.** O build recusa chaves secretas conhecidas. Não envie senhas ou chaves secretas pelo chat.

## Testar no computador

Instale Node.js 24. Na pasta do repositório:

```sh
cd web
npm ci
```

Copie `.env.example` para `.env.local` e preencha:

```dotenv
VITE_SUPABASE_URL=https://SEU-PROJETO.supabase.co
VITE_SUPABASE_ANON_KEY=SUA_CHAVE_PUBLICA
```

O arquivo `.env.local` é ignorado pelo Git. Execute `npm run dev` e abra o endereço mostrado no terminal. Para esta primeira conferência, use lançamentos fictícios. Sem configuração, a página mostra que o acesso ainda está sendo preparado e mantém o login desativado.

## Publicar no Cloudflare Pages

1. Crie uma conta gratuita em https://pages.cloudflare.com e conecte seu repositório do GitHub a um projeto Pages.
2. Configure **Root directory** como `web`, **Build command** como `npm run build` e **Build output directory** como `dist`.
3. Nas variáveis de ambiente, defina `NODE_VERSION=24`, `EXIGIR_CONFIG_WEB=1`, `VITE_SUPABASE_URL` e `VITE_SUPABASE_ANON_KEY`. As duas últimas devem ser as informações públicas do projeto. Não configure senhas ou chaves administrativas.
4. Publique e copie o endereço HTTPS `pages.dev` fornecido. No Supabase, configure esse endereço como **Site URL** em Authentication → URL Configuration.
5. Abra o endereço no celular e entre com sua conta.

Se o serviço pedir ativação de cobrança, pare antes de confirmar e confira se escolheu o plano gratuito. Não há publicação automática configurada neste repositório: o workflow do GitHub apenas testa e compila a versão de revisão.

No Android, abra pelo Chrome e procure **Instalar aplicativo** ou **Adicionar à tela inicial**. No iPhone, abra pelo Safari, toque em Compartilhar e escolha **Adicionar à Tela de Início**. O nome e a posição dessas opções variam conforme a versão do navegador.

## O que acontece sem internet

A interface pode abrir pelo cache, mas consultar e gravar vendas exige conexão. Não existe fila de alterações off-line. O cache da PWA guarda apenas arquivos da interface; respostas de login e dados financeiros não são armazenados pelo service worker. A sessão de login permanece no navegador até você sair ou ela expirar.

Edições e exclusões verificam a versão do registro. Se ele mudou em outro acesso, a operação é recusada para evitar sobrescrever a alteração. Novas consultas buscam os dados online. O site também consulta novamente ao voltar para a janela, desde que não haja formulário aberto. Use **Atualizar** para conferir imediatamente. O SQLite do computador é atualizado pelo botão **Sincronizar agora** do desktop.

## Verificações do código

Dentro de `web/`:

```sh
npm test
npm run build
npm exec playwright install chromium
npm run test:browser
```

Os testes SQL usam PostgreSQL em WebAssembly, sem acessar um projeto real. Eles verificam acesso anônimo, outra conta, proprietário, valores monetários, duplicidades e edição concorrente. Os testes de navegador simulam as respostas do serviço e usam apenas dados fictícios. Eles não comprovam a configuração de um projeto Supabase real: essa conferência será feita depois de criá-lo na sua conta.

## Preparar as tabelas financeiras

Depois de configurar o acesso e testar as vendas, execute uma única vez
[`supabase/migrations/002_financeiro.sql`](../supabase/migrations/002_financeiro.sql)
no SQL Editor do mesmo projeto Supabase. A migração depende da `001_vendas.sql`.
Ela é transacional: se algum comando falhar, a criação não fica pela metade.
Não repita a migração depois de uma execução bem-sucedida.

O script cria lançamentos de despesas e taxas diárias, além de ajustes anuais
confirmados ou estimados. Valores são inteiros em centavos. Parcelas preservam
grupo, número, quantidade e data de vencimento: cada parcela corresponde a um
lançamento, como no desktop. O valor de cada linha é calculado pelo programa a partir do total da
compra informado no formulário. Não há geração automática de parcelas pela API nesta etapa.

As tabelas têm RLS e permitem acesso apenas ao proprietário já configurado.
Alterações incrementam a versão; a futura integração deverá informar a versão
anterior ao editar ou excluir, assim como o cadastro web de vendas já faz.
Reservas privadas de datas impedem taxas anuais e diárias sobrepostas. A chave
única dessas reservas também protege gravações simultâneas; uma colisão cancela
a operação inteira, inclusive qualquer mudança anterior nas reservas.
A tabela privada não pode ser consultada ou alterada pelo aplicativo.

Para conferir a instalação no SQL Editor:

```sql
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in ('financeiro_lancamentos', 'financeiro_taxas_anuais')
order by tablename;
```

Devem aparecer duas linhas com `rowsecurity = true`.

**Isso prepara somente o banco online.** Não altera as vendas existentes, não
transfere o SQLite, não conecta o desktop e não cria telas financeiras no celular.
Continue usando o desktop para os dados reais até validarmos a migração.
Não é necessário reinstalar o executável nesta etapa.

## Conferir a conta pelo desktop

Com o código atualizado, abra **Configurações → Conexão com a nuvem…**. Preencha a
Project URL e a mesma chave pública Publishable/anon configuradas no Cloudflare.
Use o e-mail e a senha do usuário do aplicativo, criado em Authentication → Users,
e clique em **Verificar acesso**. Não use a senha administrativa do banco.

A conferência faz login e consulta a autorização do proprietário no Supabase.
Somente depois do sucesso, URL e chave pública ficam em `nuvem.json`, na pasta
local dos dados, fora do repositório. A senha não é gravada em arquivo e o campo
é limpo ao iniciar a tentativa. No Windows, a credencial renovável da sessão é
protegida pela DPAPI da conta atual, em `sessao-nuvem.dpapi`. A senha e o token de
acesso não são persistidos. Esse arquivo fica na pasta local dos dados, fora do
repositório e dos backups SQLite/Drive. Ele não deve ser publicado nem transferido
para outro computador: não é um backup dos dados.

Nas próximas aberturas, o desktop recupera a sessão e, com a opção automática
ativa, renova o acesso e consulta a nuvem em segundo plano. **Desconectar** remove
a sessão salva deste PC, sem encerrar sessões em outros dispositivos. Se a sessão
for revogada ou não puder ser recuperada, entre novamente. Em sistemas sem DPAPI,
o login continua sendo necessário a cada abertura; não há gravação em texto aberto.
Falhas de internet não impedem o uso local. O backup no Drive segue independente.

Esta opção está no código-fonte atualizado e no executável v1.1.0. O pacote antigo
v1.0.1 não a inclui. Para testar pelo VS Code, atualize a cópia do repositório com
`git pull` e execute `python executar.py` na pasta principal.

## Transferência inicial do desktop

Antes de usar os dados reais na web:

1. No Supabase, execute [`003_migracao_desktop.sql`](../supabase/migrations/003_migracao_desktop.sql)
   no SQL Editor do mesmo projeto. As migrações 001 e 002 devem estar instaladas.
   Esse script apenas instala uma função; não transfere registros. Pode ser
   reaplicado para atualizar a função, sem recriar tabelas.
2. Atualize e abra o desktop. Em **Configurações → Conexão com a nuvem…**, verifique o acesso.
3. Clique em **Conferir migração**. O programa cria um snapshot SQLite verificado,
   valida todas as linhas e compara os registros com a nuvem, sem gravar nela.
4. Confira as quantidades e o total bruto apresentados. O relatório JSON completo
   fica na pasta `migracoes-nuvem`, junto aos dados locais. Ele registra contagens,
   vendas por ano, dias zerados, totais por meio de recebimento, despesas, taxas,
   identificação SHA-256 dos dados e do backup e o resultado da conferência.
5. Só depois clique em **Transferir dados conferidos** e confira a confirmação.
   Não edite dados em outro computador, celular ou instância durante o envio.
6. Aguarde **Transferência concluída e validada registro por registro**. O relatório
   recebe as contagens inseridas e o resumo da nuvem para comparação. Abra o site e
   use **Atualizar** para conferir as vendas. A aba Finanças consulta os mesmos registros financeiros transferidos.

O banco SQLite é preservado. Valores de dinheiro, Pix e cartão são convertidos
para centavos sem arredondamento; datas antigas nos formatos conhecidos são
normalizadas, e duplicidades após conversão interrompem a operação. Dias zerados
são mantidos. Parcelas preservam seus vencimentos e grupos, e ajustes anuais
mantêm a classificação Confirmada/Estimada. Descrições e observações não são
reescritas. Valores inválidos ou taxas sobrepostas interrompem a migração.

O banco online compara cada campo dos registros existentes e bloqueia valores
divergentes ou registros extras. Registros idênticos são preservados. As vendas
são identificadas pela data, ajustes anuais pelo ano e lançamentos por UUID
estável, derivado da conta e do identificador local. A transferência só insere o
que falta, em uma única transação. Ela nunca atualiza nem exclui registros remotos.
Qualquer erro SQL desfaz a operação inteira. Permissões e RLS continuam em vigor.

Antes do envio, o backup é verificado novamente e alterações no SQLite após a
conferência bloqueiam a transferência. Durante o envio, uma transação local sem
alterações impede outras instâncias de gravar, e o servidor bloqueia gravações
concorrentes durante a comparação e a inserção. Leituras remotas continuam.

Se a conexão cair, não presuma que nada foi enviado: o servidor pode ter concluído
antes da perda da resposta. O relatório fica como resultado a confirmar, sem
repetição automática. Faça uma nova conferência. Registros já iguais não serão
inseridos novamente. Se houver divergência, pare e examine a indicação da tabela
e do registro, sem excluir ou substituir dados para contornar o bloqueio.

**Transferência inicial não é sincronização.** Depois dela, configure o vínculo
na seção seguinte. Não use a migração para sincronizar edições ou exclusões.
Quando o vínculo existe, os botões de migração ficam desativados no desktop.

As verificações automáticas usam somente bancos e dados fictícios. Não acessam
sua conta Supabase. A conferência na conta real é realizada por você no programa.

## Sincronizar alterações entre PC e celular

1. Instale [`004_sincronizacao.sql`](../supabase/migrations/004_sincronizacao.sql)
   no SQL Editor. A estrutura financeira anterior deve estar pronta. Esse script
   pode ser reaplicado e não modifica vendas ou despesas por conta própria.
2. No desktop atualizado, abra **Configurações → Conexão com a nuvem…**, verifique o acesso
   e clique em **Sincronizar agora**. No primeiro vínculo, os dados devem coincidir
   com a migração concluída. Se já houver diferenças, o programa para, pois ainda
   não tem uma base anterior para distinguir edições de exclusões com segurança.
3. Aguarde a confirmação. A partir daí, depois de cadastrar, editar ou excluir em
   qualquer dispositivo, aguarde a consulta automática ou clique em **Sincronizar agora** no desktop. São enviados
   e recebidos vendas, despesas, taxas e parcelas. A aba Finanças no site permite consultar e editar os mesmos registros financeiros.

O desktop mantém o SQLite como banco de trabalho e continua funcionando sem
internet. Com a opção automática ativa, consulta a nuvem a cada minuto e troca
as alterações quando não há edição em andamento. Precisa estar aberto e
autenticado. No Windows, a sessão protegida é recuperada automaticamente nas
próximas aberturas; não é preciso abrir a janela de conexão novamente.
Não há um envio final garantido ao fechar: confira o status antes de sair. Um botão desabilitado durante o
processo evita iniciar duas sincronizações na mesma janela. Conclua ou cancele
qualquer formulário de venda antes de sincronizar.

O primeiro vínculo associa cada registro local ao seu UUID remoto. Depois disso,
mudanças de data continuam sendo edições da mesma venda. O programa compara a
última base sincronizada, o conteúdo atual do SQLite e o conteúdo online. Mudanças
em registros diferentes são combinadas; mudanças iguais convergem sem duplicar.
Exclusões também são propagadas. Se o mesmo registro foi alterado de formas
incompatíveis, ou excluído de um lado e editado do outro, a sincronização para e
indica o registro. Não usa o relógio dos dispositivos para escolher qual valor
sobrescrever. Confira as duas versões antes de resolver um conflito.

O servidor verifica as versões novamente, dentro de uma transação. Uma alteração
feita pelo celular depois da leitura inicial impede o lote desatualizado. Dados
financeiros continuam sujeitos às regras de valores, parcelas e cobertura de taxas.

Cada lote fica registrado no SQLite antes do envio, sem senha ou token. O servidor
guarda apenas seu identificador e a assinatura do conteúdo. Se a resposta se
perder, o mesmo lote é reconhecido na próxima tentativa e não é aplicado outra
vez. Edições locais feitas após a interrupção são comparadas antes de receber a
nuvem; conflitos permanecem protegidos. Não apague as tabelas `nuvem_sync_*` para
contornar um erro. O vínculo também bloqueia a troca acidental de conta ou projeto
nesse mesmo banco.

Antes de sincronizar, o programa cria um backup SQLite verificado. O recebimento
é aplicado junto com as referências de sincronização em uma transação local e
validado novamente. Uma falha nessa etapa preserva os valores locais; se o envio
online já tiver terminado, a retomada o reconhecerá. O backup no Drive continua
sendo feito pelo desktop. Dados novos da web só entram nessa cópia depois de
serem recebidos no PC e enviados pelo Drive; o banco Supabase ainda precisa de
uma política própria de recuperação.

Para validar o fluxo, use uma data livre com uma venda fictícia: cadastre no PC,
sincronize e confira no site; edite no site, sincronize e confira no PC; exclua o
teste e sincronize novamente. Confira também se os totais voltaram ao valor
anterior. Faça esse teste antes de usar os dois dispositivos no dia a dia.

## Finanças no celular

A aba **Finanças** tem consulta própria por semana, mês, ano ou fechamento,
independente do filtro de vendas. Semana começa na segunda e termina no domingo.
No fechamento, o mês da data de referência corresponde ao dia 10 desse mês até
09 do próximo. A consulta inicial usa o fechamento atual.

Os cartões mostram vendas brutas, taxas descontadas, valor após taxas, despesas,
saldo e quanto falta para cobrir os gastos. O ponto de interrogação abre uma
explicação por toque ou teclado. Saldo inclui somente o que foi cadastrado,
inclusive despesas pessoais e compromissos futuros: não é lucro contábil.

A regra dos ajustes anuais é a mesma do desktop. O valor só é descontado quando
sua cobertura inteira cabe no filtro. Um recorte parcial recebe aviso de saldo
provisório, sem ratear ou inventar taxas. Ajustes estimados continuam identificados.
A lista de ajustes mostra todos os anos, mesmo quando o resumo usa outro período.

Para despesas parceladas, informe a data da compra, o **valor total da compra**
e a quantidade, usando Cartão de crédito. Os vencimentos seguintes são mensais;
quando o dia não existe no mês, usa o último dia disponível e retorna ao dia
original nos meses seguintes. O lote é gravado numa única transação. Editar uma linha abre a compra completa e recalcula todas as parcelas. Excluir continua removendo somente a parcela selecionada.
Não cadastre novamente uma despesa já incluída no compromisso inicial da fatura.

Taxas diárias e ajustes anuais não podem cobrir o mesmo dia. Duplicidades,
sobreposições e alterações concorrentes são recusadas no servidor. As operações
usam a função `sincronizar_desktop` do SQL 004, já instalada; esta atualização da
interface não exige outro script SQL.

Antes de enviar uma alteração financeira, o navegador registra o lote pendente
no `sessionStorage`, separado por usuário, sem senha ou token. Enquanto a sessão
da aba existir, é possível confirmar o mesmo envio depois de uma queda de rede ou
recarregamento, sem repeti-lo. Na confirmação incerta, campos ficam bloqueados:
use **Confirmar envio**, ou feche o formulário e use **Atualizar finanças**.
Não há cadastro off-line: esse registro serve para retomar um envio iniciado com
conexão. A sessão da aba pode ser perdida ao fechar o navegador; confira a lista
online antes de recriar manualmente uma despesa após uma interrupção.

O service worker continua sem armazenar respostas financeiras. Sair da conta
limpa a tela; uma operação pendente só é retomada pela mesma conta. Depois de
alterar no celular, use **Sincronizar agora** no PC para receber os dados. O envio
no desktop também pode ser automático, conforme a seção abaixo.

## Sincronização automática no desktop

Atualize o código, abra **Configurações → Conexão com a nuvem** e use **Verificar acesso**.
Depois do vínculo inicial, a opção **Sincronizar automaticamente a cada minuto**
fica ativa por padrão. Depois de salvar ou excluir um registro no PC, agenda
um envio em cerca de dois segundos quando não há edição aberta. Desmarque para continuar no modo manual; essa preferência
fica em `sincronizacao.json`, junto aos dados locais, sem senha ou token.

A consulta de rede ocorre em segundo plano. O programa aguarda formulários de
venda, despesas ou taxas. Filtros ainda não aplicados não bloqueiam a rede e
são preservados enquanto os resultados da seleção já aplicada são atualizados. Se um editor for aberto
durante a consulta, o recebimento é adiado e os campos digitados são preservados.
Quando há dados a trocar, as ações de edição ficam temporariamente desabilitadas
para concluir a transação. A janela continua respondendo e não abre um aviso a
cada consulta. O status da nuvem fica no rodapé; clique nele para abrir os detalhes.

Se nada mudou, a consulta não cria outro backup. Antes de trocar dados, mantém o
backup verificado e as mesmas regras de versões, conflitos e retomada. Uma falha
de internet agenda novas tentativas em 1, 2, 4 e até 5 minutos. O botão manual
permite tentar antes. Conflitos, dados inválidos ou acesso revogado pausam a
automação. Confira o registro indicado antes de tentar sincronizar manualmente;
uma sincronização manual bem-sucedida ou um novo login retoma o agendamento.

Alterações locais são identificadas no rodapé como aguardando envio; isso evita
confundir uma sincronização anterior com um cadastro que ainda não saiu do PC.
Restaurar um backup pausa a automação até uma conferência e sincronização manual.

A sessão é renovada automaticamente. No Windows, cada credencial renovada é
salva com a proteção da conta atual antes da próxima consulta, para permitir a
reconexão mesmo após fechar o programa. Falhas ao salvar são informadas nos
detalhes da conexão. Se a rede falhar depois da renovação, a nova sessão também
permanece na memória para a próxima tentativa. Desconectar cancela o agendamento
e remove a sessão salva. O rodapé mostra a hora da última conferência, com segundos,
mesmo quando não havia alterações a receber.

A automação não funciona com o PC desligado ou o programa fechado. O celular
continua salvando online; o PC recebe essas alterações depois de abrir o programa
(no Windows, recuperando a sessão salva). Ao encerrar durante um envio, pode haver um lote pendente,
retomado com segurança no próximo acesso. Não depende de outro SQL nem de novos
serviços pagos. O executável v1.1.0 contém essas funções; o pacote antigo v1.0.1 não.


## Análises e comparação no celular

A aba **Análises** tem uma consulta própria: não altera os filtros de Vendas ou
Finanças. Escolha Mês, Ano, Fechamento ou Todas as vendas e use **Consultar análises**.
A data de referência identifica o mês/ano. Fechamento de outubro significa
10/10 a 09/11, independentemente do dia escolhido dentro de outubro.

São mostrados total bruto, quantidade de dias de feira, média incluindo os dias
zerados, participação das formas de pagamento e resultados por dia da semana.
As tabelas mais largas podem ser deslizadas na horizontal. Os valores não descontam
taxas nem despesas; esse resultado está na aba Finanças.

Em **Comparar A e B**, use **Comparar por**. Para Mês e Fechamento, selecione
o mês e o ano nos seletores lado a lado, como no desktop. Para Data ou Intervalo,
informe as datas; no intervalo, os dois limites são incluídos. Depois pressione
**Comparar períodos**. A diferença é B menos A e o percentual usa A como base.
Quando um período não tem registros ou A tem total zero, não é exibido percentual.
O resumo do período também compara automaticamente mês/ano/fechamento com o
período anterior. Os dois lados são calculados a partir da mesma consulta dos dados.

## Atualização da tela web

A área visível (Vendas, Finanças ou Análises) é consultada automaticamente a cada
minuto. Voltar ao aplicativo ou recuperar a conexão também solicita uma consulta.
Não depende de configurar Supabase Realtime ou instalar outro SQL.

Com um formulário aberto ou uma gravação em andamento, a consulta aguarda. Filtros
alterados e ainda não aplicados ficam intactos: os resultados seguem a seleção
já aplicada. Comparações A/B já consultadas também são atualizadas. O status perto
das abas informa a hora da conferência ou uma falha de conexão. Os botões de
atualizar continuam disponíveis. Não há consultas periódicas da tela oculta ou
sem internet, nem gravações offline. Ao sair da conta, o agendamento e os resultados
são limpos.

Isso não é uma atualização instantânea por notificações: se salvar no PC, aguarde
primeiro o envio do desktop e depois a consulta da web (até cerca de um minuto,
mais o tempo de rede). A sincronização do desktop continua independente da tela web.


## Exportar e acompanhar evolução

Em Vendas, use **Exportar CSV** ou **Exportar Excel**. O arquivo usa os registros
já exibidos pela consulta aplicada e traz um resumo, incluindo dias zerados.
O download é gerado no aparelho; não envia seus dados para outro serviço.
Não inclui despesas nem taxas. Para recuperar todo o programa, mantenha o backup
SQLite. A biblioteca Excel é carregada no primeiro uso; esse carregamento precisa
de internet se ainda não estiver em cache.

Em Análises, **Evolução das vendas** mostra até 12 meses ou fechamentos consecutivos
da seleção aplicada. Selecione Ano ou Todas as vendas para comparar a evolução.
A barra é proporcional ao total bruto, e os valores e quantidades também estão
escritos. Um período sem registros não é tratado como um dia de feira zerado.
A revisão de conflitos está disponível no desktop em Conexão com a nuvem.

## Atualização financeira 1.6.1

Datas explícitas, filtros adaptativos e taxas semanais usam as tabelas existentes. Para configurar novas vigências do fechamento, execute apenas [005_fechamentos.sql](../supabase/migrations/005_fechamentos.sql) no mesmo projeto e atualize o desktop. O protocolo financeiro das versões anteriores continua compatível. Veja [FINANCAS.md](FINANCAS.md).
