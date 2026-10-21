-- Instala sincronização com versões e recibos para retomada após falha de rede.
begin;
create table if not exists public.nuvem_operacoes (
    id uuid not null,
    user_id uuid not null default auth.uid() references auth.users(id),
    assinatura text not null,
    created_at timestamptz not null default now(),
    primary key(user_id, id)
);
alter table public.nuvem_operacoes enable row level security;
alter table public.nuvem_operacoes force row level security;
revoke all on public.nuvem_operacoes from public, anon, authenticated;
grant select, insert on public.nuvem_operacoes to authenticated;
drop policy if exists consultar on public.nuvem_operacoes;
create policy consultar on public.nuvem_operacoes for select to authenticated
using (public.usuario_autorizado() and user_id = auth.uid());
drop policy if exists inserir on public.nuvem_operacoes;
create policy inserir on public.nuvem_operacoes for insert to authenticated
with check (public.usuario_autorizado() and user_id = auth.uid());

create or replace function public.sincronizar_desktop(alteracoes jsonb default '[]', operacao_id uuid default null)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
    tabela text;
    colunas text[];
    omitidas text[] := array['user_id', 'total_centavos', 'created_at', 'updated_at'];
    operacao jsonb;
    registro jsonb;
    snapshot jsonb := '{}'::jsonb;
    remoto jsonb;
    lista text;
    valores text;
    versao_atual integer;
    recibo text;
    assinatura text;
    repetida boolean := false;
    afetados integer;
begin
    if not public.usuario_autorizado() then
        raise exception using errcode='42501', message='Conta não autorizada.';
    end if;
    if jsonb_typeof(alteracoes) is distinct from 'array' then
        raise exception using errcode='PFS02', message='Alterações inválidas.';
    end if;
    if jsonb_array_length(alteracoes) > 100000 or
       (jsonb_array_length(alteracoes) > 0 and operacao_id is null) then
        raise exception using errcode='PFS02', message='Identificação de operação inválida.';
    end if;
    perform set_config('lock_timeout', '5s', true);
    lock table public.vendas, public.financeiro_lancamentos,
        public.financeiro_taxas_anuais in share row exclusive mode;
    -- SELECT/INSERT são suficientes para o recibo: não é possível editá-lo.
    -- Os locks nas tabelas acima serializam as operações deste aplicativo.
    assinatura := encode(sha256(convert_to(alteracoes::text, 'UTF8')), 'hex');
    if operacao_id is not null then
        select n.assinatura into recibo from public.nuvem_operacoes n
        where n.user_id=auth.uid() and n.id=operacao_id;
        if found then
            if recibo <> assinatura then
                raise exception using errcode='PFS02', message='Operação reutilizada com conteúdo diferente.';
            end if;
            repetida := true;
        end if;
    end if;
    if not repetida then
        -- Valida todas as versões antes de alterar qualquer tabela.
        for operacao in select value from jsonb_array_elements(alteracoes) loop
            if jsonb_typeof(operacao) is distinct from 'object' then
                raise exception using errcode='PFS02', message='Operação inválida.';
            end if;
            if not (operacao ?& array['tabela','acao','id','versao','dados']) or
               (select count(*) from jsonb_object_keys(operacao)) <> 5 then
                raise exception using errcode='PFS02', message='Campos de operação inválidos.';
            end if;
            tabela := operacao->>'tabela';
            if tabela is null or tabela not in ('vendas','financeiro_lancamentos','financeiro_taxas_anuais') or
               operacao->>'acao' is null or operacao->>'acao' not in ('inserir','editar','excluir') or
               operacao->>'id' is null then
                raise exception using errcode='PFS02', message='Tabela ou ação inválida.';
            end if;
            if (select count(*) from jsonb_array_elements(alteracoes) r
                where r.value->>'tabela'=tabela and r.value->>'id'=operacao->>'id') <> 1 then
                raise exception using errcode='PFS02', message='Registro repetido na operação.';
            end if;
            execute format('select versao from public.%I where id=$1', tabela)
                into versao_atual using (operacao->>'id')::uuid;
            if (operacao->>'acao'='inserir' and (versao_atual is not null or operacao->'versao' <> 'null'::jsonb)) or
               (operacao->>'acao'<>'inserir' and (versao_atual is null or
                versao_atual is distinct from (operacao->>'versao')::integer)) then
                raise exception using errcode='PFS01', message='Registro alterado em outro acesso.',
                    detail=jsonb_build_object('tabela',tabela,'chave',operacao->>'id')::text;
            end if;
        end loop;
        -- Exclusões primeiro, para liberar datas e intervalos removidos no lote.
        for operacao in select value from jsonb_array_elements(alteracoes)
            order by case value->>'acao' when 'excluir' then 0 when 'editar' then 1 else 2 end loop
            tabela := operacao->>'tabela';
            if tabela='vendas' then
                colunas := array['data','dinheiro_centavos','pix_centavos','cartao_centavos'];
            elsif tabela='financeiro_lancamentos' then
                colunas := array['tipo','data','descricao','valor_centavos','meio','categoria','grupo','parcela','parcelas'];
            else
                colunas := array['ano','inicio','fim','valor_centavos','natureza','observacao'];
            end if;
            registro := operacao->'dados';
            if operacao->>'acao'='excluir' then
                if registro <> 'null'::jsonb then
                    raise exception using errcode='PFS02', message='Exclusão inválida.';
                end if;
                execute format('delete from public.%I where id=$1 and versao=$2',tabela)
                    using (operacao->>'id')::uuid, (operacao->>'versao')::integer;
            else
                if jsonb_typeof(registro) is distinct from 'object' then
                    raise exception using errcode='PFS02', message='Dados inválidos.';
                end if;
                if not (registro ?& colunas) or
                   (select count(*) from jsonb_object_keys(registro)) <> cardinality(colunas) then
                    raise exception using errcode='PFS02', message='Campos de dados inválidos.';
                end if;
                select string_agg(format('%I', c), ', '), string_agg(format('r.%I',c), ', ')
                    into lista, valores from unnest(colunas) as c;
                if operacao->>'acao'='inserir' then
                    execute format('insert into public.%I (id,%s) select $2,%s from jsonb_populate_record(null::public.%I,$1) r',tabela,lista,valores,tabela)
                        using registro, (operacao->>'id')::uuid;
                else
                    execute format('update public.%I set (%s)=(select %s from jsonb_populate_record(null::public.%I,$1) r) where id=$2 and versao=$3',tabela,lista,valores,tabela)
                        using registro, (operacao->>'id')::uuid, (operacao->>'versao')::integer;
                end if;
            end if;
            get diagnostics afetados = row_count;
            if afetados <> 1 then
                raise exception using errcode='PFS01', message='Quantidade inesperada de registros alterados.';
            end if;
        end loop;
        if operacao_id is not null then
            insert into public.nuvem_operacoes(id, assinatura) values(operacao_id, assinatura);
        end if;
    end if;
    foreach tabela in array array['vendas','financeiro_lancamentos','financeiro_taxas_anuais'] loop
        execute format('select coalesce(jsonb_agg(to_jsonb(t)-$1 order by id),''[]''::jsonb) from public.%I t',tabela)
            into remoto using omitidas;
        snapshot := snapshot || jsonb_build_object(tabela,remoto);
    end loop;
    return jsonb_build_object('protocolo',1,'usuario_id',auth.uid(),'dados',snapshot,'operacao_id',operacao_id,'repetida',repetida);
end;
$$;
revoke all on function public.sincronizar_desktop(jsonb,uuid) from public,anon;
grant execute on function public.sincronizar_desktop(jsonb,uuid) to authenticated;
commit;
