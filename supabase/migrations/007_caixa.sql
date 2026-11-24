-- PWA: posição inicial e movimentos de caixa. Não altera vendas/despesas.
-- Execute uma vez após 001 a 006, no SQL Editor do projeto usado pelo PWA.
begin;
create table if not exists public.caixa_movimentos (
 id uuid primary key,
 user_id uuid not null references auth.users(id),
 tipo text not null check(tipo in ('abertura','entrada','saida','transferencia','conferencia')),
 data date not null check(data between date '1900-01-01' and date '9998-12-31'),
 descricao text not null check(length(btrim(descricao)) between 1 and 200),
 conta text check(conta in ('dinheiro','conta')),
 valor_centavos bigint check(valor_centavos between 1 and 99999999999),
 dinheiro_centavos bigint check(dinheiro_centavos between 0 and 99999999999),
 conta_centavos bigint check(conta_centavos between 0 and 99999999999),
 cancelado boolean not null default false,
 versao integer not null default 1 check(versao>0),
 created_at timestamptz not null default now(),
 check((tipo in ('abertura','conferencia') and conta is null and valor_centavos is null and dinheiro_centavos is not null and conta_centavos is not null)
    or (tipo in ('entrada','saida','transferencia') and conta is not null and valor_centavos is not null and dinheiro_centavos is null and conta_centavos is null))
);
create unique index if not exists caixa_uma_abertura on public.caixa_movimentos(user_id) where tipo='abertura' and not cancelado;
create index if not exists caixa_por_data on public.caixa_movimentos(user_id,data);
alter table public.caixa_movimentos enable row level security;
alter table public.caixa_movimentos force row level security;
revoke all on public.caixa_movimentos from public,anon,authenticated;
grant select on public.caixa_movimentos to authenticated;
drop policy if exists consultar_caixa on public.caixa_movimentos;
create policy consultar_caixa on public.caixa_movimentos for select to authenticated using(public.usuario_autorizado() and user_id=auth.uid());
create table if not exists private.caixa_recibos (
 user_id uuid not null references auth.users(id),operacao_id uuid not null,
 pedido jsonb not null,resultado jsonb not null,created_at timestamptz not null default now(),
 primary key(user_id,operacao_id)
);
alter table private.caixa_recibos enable row level security;
revoke all on private.caixa_recibos from public,anon,authenticated;
create or replace function public.consultar_caixa() returns jsonb
language plpgsql security invoker set search_path='' as $$
begin
 if not public.usuario_autorizado() then raise exception 'Acesso não autorizado' using errcode='42501';end if;
 return (select jsonb_build_object('protocolo',1,'movimentos',coalesce((select jsonb_agg(to_jsonb(c)-'user_id' order by c.data,c.created_at,c.id) from public.caixa_movimentos c where c.user_id=auth.uid()),'[]'::jsonb),
 'vendas',coalesce((select jsonb_agg(jsonb_build_object('id',v.id,'data',v.data,'dinheiro_centavos',v.dinheiro_centavos,'pix_centavos',v.pix_centavos)) from public.vendas v where v.user_id=auth.uid()),'[]'::jsonb),
 'despesas',coalesce((select jsonb_agg(jsonb_build_object('id',f.id,'tipo',f.tipo,'data',f.data,'meio',f.meio,'valor_centavos',f.valor_centavos)) from public.financeiro_lancamentos f where f.user_id=auth.uid()),'[]'::jsonb)));
end;$$;
create or replace function public.salvar_caixa(pedido jsonb,operacao_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare dono uuid:=auth.uid();rec private.caixa_recibos;novo public.caixa_movimentos;anterior public.caixa_movimentos;inicio date;resposta jsonb;
begin
 if dono is null or not public.usuario_autorizado() then raise exception 'Acesso não autorizado' using errcode='42501';end if;
 if operacao_id is null or jsonb_typeof(pedido) is distinct from 'object' then raise exception 'Pedido inválido' using errcode='22023';end if;
 perform pg_advisory_xact_lock(hashtextextended(dono::text||':caixa',0));
 select * into rec from private.caixa_recibos r where r.user_id=dono and r.operacao_id=salvar_caixa.operacao_id;
 if found then
  if rec.pedido is distinct from pedido then raise exception 'Recibo pertence a outro pedido' using errcode='22023';end if;
  return rec.resultado;
 end if;
 if pedido->>'acao'='inserir' then
  if pedido - array['acao','dados'] <> '{}'::jsonb or jsonb_typeof(pedido->'dados') is distinct from 'object' or
    (pedido->'dados') - array['id','tipo','data','descricao','conta','valor_centavos','dinheiro_centavos','conta_centavos'] <> '{}'::jsonb or
    not ((pedido->'dados') ?& array['id','tipo','data','descricao','conta','valor_centavos','dinheiro_centavos','conta_centavos']) then raise exception 'Campos inválidos' using errcode='22023';end if;
  novo:=jsonb_populate_record(null::public.caixa_movimentos,pedido->'dados');
  if pedido->'dados'->>'data' is distinct from to_char(novo.data,'YYYY-MM-DD') then raise exception 'Use data ISO' using errcode='22023';end if;
  novo.user_id:=dono;novo.cancelado:=false;novo.versao:=1;novo.created_at:=now();
  if novo.data>(now() at time zone 'America/Sao_Paulo')::date then raise exception 'Movimento futuro não é saldo disponível' using errcode='22023';end if;
  select c.data into inicio from public.caixa_movimentos c where c.user_id=dono and c.tipo='abertura' and not c.cancelado;
  if novo.tipo='abertura' then
   if inicio is not null then raise exception 'Saldo inicial já existe' using errcode='40001';end if;
  elsif inicio is null or novo.data<=inicio then raise exception 'Use uma data posterior ao saldo inicial (fim do dia)' using errcode='22023';end if;
  insert into public.caixa_movimentos select novo.*;
 elsif pedido->>'acao'='cancelar' then
  if pedido - array['acao','id','versao'] <> '{}'::jsonb or not (pedido ?& array['acao','id','versao']) then raise exception 'Campos inválidos' using errcode='22023';end if;
  select * into anterior from public.caixa_movimentos c where c.user_id=dono and c.id=(pedido->>'id')::uuid for update;
  if not found or anterior.cancelado or anterior.versao is distinct from (pedido->>'versao')::integer then raise exception 'Registro mudou; consulte novamente' using errcode='40001';end if;
  if anterior.tipo='abertura' and exists(select 1 from public.caixa_movimentos c where c.user_id=dono and not c.cancelado and c.id<>anterior.id) then raise exception 'Saldo inicial possui movimentos; registre um ajuste com motivo' using errcode='22023';end if;
  update public.caixa_movimentos set cancelado=true,versao=versao+1 where id=anterior.id returning * into novo;
 else raise exception 'Ação inválida' using errcode='22023';end if;
 resposta:=jsonb_build_object('protocolo',1,'operacao_id',operacao_id,'registro',to_jsonb(novo)-'user_id');
 insert into private.caixa_recibos(user_id,operacao_id,pedido,resultado) values(dono,operacao_id,pedido,resposta);
 return resposta;
end;$$;
revoke all on function public.consultar_caixa() from public,anon;
revoke all on function public.salvar_caixa(jsonb,uuid) from public,anon;
grant execute on function public.consultar_caixa() to authenticated;
grant execute on function public.salvar_caixa(jsonb,uuid) to authenticated;
notify pgrst,'reload schema';
commit;
