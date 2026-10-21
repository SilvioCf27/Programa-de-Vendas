# Primeira versão para celular

A versão web fica em `web/`. Ela pode ser instalada na tela inicial do celular como PWA. O programa de Windows continua funcionando com seu banco local.

Nesta etapa estão prontos o login de uma única conta, cadastro, edição, exclusão e consulta de vendas. Os filtros incluem mês, ano e fechamento de 10 a 09. Valores zerados contam como dias de feira. A tela mostra valores brutos; taxas, despesas, parcelas, comparação e exportação ainda serão levadas para a versão web.

**Ainda não há sincronização com o desktop.** Não faça lançamentos reais nas duas versões esperando que sejam combinados. Primeiro vamos configurar e testar o acesso online; depois preparar a migração dos dados e a integração do computador. Nenhum dado pessoal acompanha o código ou é importado automaticamente.

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

Edições e exclusões verificam a versão do registro. Se ele mudou em outro acesso, a operação é recusada para evitar sobrescrever a alteração. Novas consultas buscam os dados online; nesta etapa use **Atualizar** para conferir alterações de outro navegador. Isso ainda não é sincronização do SQLite do computador.

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
lançamento, como no desktop. O valor gravado é o de cada parcela, não o total da
compra. Não há geração automática de parcelas pela API nesta etapa.

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
