-- Acrescenta preferências sem alterar vendas, despesas, taxas ou o protocolo de sincronização existente.
begin;
create table if not exists private.configuracoes_fechamento (
    user_id uuid primary key references auth.users(id) on delete cascade,
    versao integer not null default 0 check (versao >= 0),
    historico jsonb not null default '[]'::jsonb check (jsonb_typeof(historico) = 'array')
);
alter table private.configuracoes_fechamento enable row level security;
alter table private.configuracoes_fechamento force row level security;
revoke all on private.configuracoes_fechamento from public, anon, authenticated;

create or replace function public.consultar_fechamentos()
returns jsonb language plpgsql security definer set search_path = '' as $$
declare resultado jsonb;
begin
    if not public.usuario_autorizado() then
        raise exception using errcode='42501', message='Conta não autorizada.';
    end if;
    select jsonb_build_object('versao', versao, 'historico', historico) into resultado
      from private.configuracoes_fechamento where user_id = auth.uid();
    return coalesce(resultado, '{"versao":0,"historico":[]}'::jsonb);
end;
$$;

create or replace function public.salvar_fechamento(versao_esperada integer, vigencia date, dia integer)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare atual private.configuracoes_fechamento%rowtype;
    proximo_mes date := (date_trunc('month', timezone('America/Sao_Paulo', now())) + interval '1 month')::date;
    ultima date;
begin
    if not public.usuario_autorizado() then
        raise exception using errcode='42501', message='Conta não autorizada.';
    end if;
    if vigencia is null or date_trunc('month', vigencia)::date <> vigencia or vigencia < proximo_mes or vigencia > date '9998-12-01'
       or dia is null or dia < 1 or dia > 31 or versao_esperada is null or versao_esperada < 0 then
        raise exception using errcode='22023', message='Use uma vigência a partir do próximo mês e dia de 1 a 31.';
    end if;
    insert into private.configuracoes_fechamento(user_id) values(auth.uid()) on conflict do nothing;
    select * into atual from private.configuracoes_fechamento where user_id = auth.uid() for update;
    if atual.versao <> versao_esperada then
        raise exception using errcode='40001', message='A configuração mudou. Consulte novamente antes de salvar.';
    end if;
    if jsonb_array_length(atual.historico) > 0 then
        ultima := (atual.historico -> -1 ->> 'vigencia')::date;
        if vigencia < ultima then
            raise exception using errcode='22023', message='A vigência não pode vir antes da regra mais recente.';
        end if;
        if vigencia = ultima then
            atual.historico := atual.historico - (jsonb_array_length(atual.historico) - 1);
        end if;
    end if;
    update private.configuracoes_fechamento set
        historico = atual.historico || jsonb_build_array(jsonb_build_object('vigencia', vigencia::text, 'dia', dia)),
        versao = atual.versao + 1 where user_id = auth.uid();
    return public.consultar_fechamentos();
end;
$$;
revoke all on function public.consultar_fechamentos() from public, anon;
revoke all on function public.salvar_fechamento(integer,date,integer) from public, anon;
grant execute on function public.consultar_fechamentos() to authenticated;
grant execute on function public.salvar_fechamento(integer,date,integer) to authenticated;
commit;
