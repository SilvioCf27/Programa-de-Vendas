-- Execute depois de 001 e 002. Apenas instala a operação; não transfere dados.
begin;
create or replace function public.migrar_desktop(dados jsonb, aplicar boolean default false)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
    tabela text;
    chave text;
    colunas text[];
    omitidas text[];
    registros jsonb;
    remoto jsonb;
    resultado jsonb := '{}'::jsonb;
    novos jsonb := '{}'::jsonb;
    linha jsonb;
    lista_colunas text;
    lista_origem text;
begin
    if not public.usuario_autorizado() then
        raise exception using errcode = '42501', message = 'Conta não autorizada.';
    end if;
    if aplicar is null or jsonb_typeof(dados) is distinct from 'object' then
        raise exception using errcode = 'PFM02', message = 'Formato de migração inválido.';
    end if;
    if not (dados ?& array['vendas', 'financeiro_lancamentos', 'financeiro_taxas_anuais'])
       or (select count(*) from jsonb_object_keys(dados)) <> 3 then
        raise exception using errcode = 'PFM02', message = 'Tabelas de migração inválidas.';
    end if;
    -- Bloqueia gravações durante a comparação e o envio; leituras continuam.
    -- O chamador mantém as permissões e o RLS, inclusive durante os INSERTs.
    perform set_config('lock_timeout', '5s', true);
    lock table public.vendas, public.financeiro_lancamentos,
        public.financeiro_taxas_anuais in share row exclusive mode;

    foreach tabela in array array['vendas', 'financeiro_lancamentos', 'financeiro_taxas_anuais'] loop
        registros := dados -> tabela;
        if jsonb_typeof(registros) is distinct from 'array' then
            raise exception using errcode = 'PFM02', message = 'Lista de registros inválida.';
        end if;
        if jsonb_array_length(registros) > 100000 then
            raise exception using errcode = 'PFM02', message = 'Quantidade de registros excedida.';
        end if;
        if tabela = 'vendas' then
            chave := 'data';
            colunas := array['data', 'dinheiro_centavos', 'pix_centavos', 'cartao_centavos'];
            omitidas := array['id', 'user_id', 'total_centavos', 'versao', 'created_at', 'updated_at'];
        elsif tabela = 'financeiro_lancamentos' then
            chave := 'id';
            colunas := array['id', 'tipo', 'data', 'descricao', 'valor_centavos', 'meio', 'categoria', 'grupo', 'parcela', 'parcelas'];
            omitidas := array['user_id', 'versao', 'created_at', 'updated_at'];
        else
            chave := 'ano';
            colunas := array['ano', 'inicio', 'fim', 'valor_centavos', 'natureza', 'observacao'];
            omitidas := array['id', 'user_id', 'versao', 'created_at', 'updated_at'];
        end if;
        for linha in select value from jsonb_array_elements(registros) loop
            if jsonb_typeof(linha) is distinct from 'object' then
                raise exception using errcode = 'PFM02', message = 'Registro inválido.';
            end if;
            if not (linha ?& colunas) or (select count(*) from jsonb_object_keys(linha)) <> cardinality(colunas)
               or linha ->> chave is null then
                raise exception using errcode = 'PFM02', message = 'Campos de migração inválidos.';
            end if;
        end loop;
        if (select count(distinct value ->> chave) from jsonb_array_elements(registros)) <> jsonb_array_length(registros) then
            raise exception using errcode = 'PFM02', message = 'Chaves duplicadas na origem.';
        end if;
        execute format('select coalesce(jsonb_agg(to_jsonb(t) - $1 order by t.%I), ''[]''::jsonb) from public.%I t', chave, tabela)
            into remoto using omitidas;
        -- Exige que todo registro remoto corresponda exatamente à origem.
        -- Nunca atualiza ou exclui registros já existentes.
        for linha in select value from jsonb_array_elements(remoto) loop
            if not exists (select 1 from jsonb_array_elements(registros) r where r.value = linha) then
                raise exception using errcode = 'PFM01', message = 'Há dados divergentes ou extras na nuvem. Migração cancelada.',
                    detail = jsonb_build_object('tabela', tabela, 'chave', linha ->> chave)::text;
            end if;
        end loop;
        novos := novos || jsonb_build_object(tabela, jsonb_array_length(registros) - jsonb_array_length(remoto));
        if aplicar then
            select string_agg(format('%I', c), ', '), string_agg(format('r.%I', c), ', ')
                into lista_colunas, lista_origem from unnest(colunas) as c;
            execute format('insert into public.%I (%s)
                select %s from jsonb_populate_recordset(null::public.%I, $1) r
                where not exists (select 1 from public.%I t where t.%I = r.%I)',
                tabela, lista_colunas, lista_origem, tabela, tabela, chave, chave)
                using registros;
            execute format('select coalesce(jsonb_agg(to_jsonb(t) - $1 order by t.%I), ''[]''::jsonb) from public.%I t', chave, tabela)
                into remoto using omitidas;
            -- Confere os campos persistidos dentro da mesma transação.
            if jsonb_array_length(remoto) <> jsonb_array_length(registros)
               or exists (select 1 from jsonb_array_elements(registros) r
                          where not exists (select 1 from jsonb_array_elements(remoto) t where t.value = r.value)) then
                raise exception using errcode = 'PFM01', message = 'A validação final divergiu. Migração cancelada.';
            end if;
        end if;
        resultado := resultado || jsonb_build_object(tabela, remoto);
    end loop;
    return jsonb_build_object('aplicado', aplicar, 'novos', novos, 'dados', resultado);
end;
$$;
revoke all on function public.migrar_desktop(jsonb, boolean) from public, anon;
grant execute on function public.migrar_desktop(jsonb, boolean) to authenticated;
commit;
