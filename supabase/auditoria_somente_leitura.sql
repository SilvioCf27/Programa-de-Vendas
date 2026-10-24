-- Auditoria de configuração: não mostra vendas, despesas, senhas, tokens ou chaves.
-- Execute no SQL Editor do seu projeto e confira todos os conjuntos de resultados.
-- A transação é somente leitura; não instala funções nem muda permissões.
begin transaction read only;

-- Tabelas públicas de dados: RLS e FORCE RLS devem estar ativos.
select n.nspname as esquema, c.relname as tabela,
       c.relrowsecurity as rls, c.relforcerowsecurity as force_rls,
       has_table_privilege('anon', c.oid, 'SELECT') as anon_pode_consultar,
       has_table_privilege('anon', c.oid, 'INSERT') as anon_pode_inserir,
       has_table_privilege('anon', c.oid, 'UPDATE') as anon_pode_editar,
       has_table_privilege('anon', c.oid, 'DELETE') as anon_pode_excluir
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relname in
  ('vendas','financeiro_lancamentos','financeiro_taxas_anuais','nuvem_operacoes')
order by c.relname;

-- Políticas devem restringir os dados à conta autorizada e ao seu auth.uid().
select schemaname, tablename, policyname, roles, cmd, qual, with_check
from pg_policies where schemaname='public' and tablename in
  ('vendas','financeiro_lancamentos','financeiro_taxas_anuais','nuvem_operacoes')
order by tablename,cmd;

-- Funciona com versões antigas também: função ausente aparece como instalada=false.
with esperadas(assinatura) as (values
 ('public.usuario_autorizado()'),
 ('public.migrar_desktop(jsonb,boolean)'),
 ('public.sincronizar_desktop(jsonb,uuid)'),
 ('public.consultar_fechamentos()'),
 ('public.salvar_fechamento(integer,date,integer)'),
 ('public.migrar_desktop_v2(jsonb,boolean)'),
 ('public.sincronizar_desktop_v2(jsonb,uuid)'))
select e.assinatura, p.oid is not null as instalada,
       has_function_privilege('anon',p.oid,'EXECUTE') as anon_pode_executar,
       has_function_privilege('authenticated',p.oid,'EXECUTE') as autenticado_pode_executar,
       p.prosecdef as security_definer, p.proconfig as opcoes
from esperadas e left join pg_proc p on p.oid=to_regprocedure(e.assinatura)
order by e.assinatura;

-- Configuração privada usa revogação de acesso ao esquema/tabela. RLS falso
-- nesta tabela privada, por si só, não significa acesso público.
select has_schema_privilege('anon','private','USAGE') as anon_acessa_esquema_privado,
       has_schema_privilege('authenticated','private','USAGE') as autenticado_acessa_esquema_privado,
       has_table_privilege('anon','private.app_config','SELECT') as anon_le_configuracao,
       has_table_privilege('authenticated','private.app_config','SELECT') as autenticado_le_configuracao;

-- Somente contagem e booleano: não revela o UUID nem o e-mail do proprietário.
select count(*) as proprietarios_configurados,
       coalesce(bool_and(exists(select 1 from auth.users u where u.id=c.owner_id)),false) as proprietario_existe
from private.app_config c;

commit;
