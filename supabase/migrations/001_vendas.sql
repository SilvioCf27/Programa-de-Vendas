-- Execute uma vez no SQL Editor do projeto. A autorização começa fechada.
begin;
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
create table if not exists private.app_config (
    singleton boolean primary key default true check (singleton),
    owner_id uuid not null references auth.users(id)
);
revoke all on private.app_config from public, anon, authenticated;

create or replace function public.usuario_autorizado()
returns boolean language sql stable security definer set search_path = '' as $$
    select auth.uid() is not null and exists (
        select 1 from private.app_config where singleton and owner_id = auth.uid()
    );
$$;
revoke all on function public.usuario_autorizado() from public, anon;
grant execute on function public.usuario_autorizado() to authenticated;

create table if not exists public.vendas (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null default auth.uid() references auth.users(id),
    data date not null check (data between date '0001-01-01' and date '9999-12-31'),
    dinheiro_centavos bigint not null default 0 check (dinheiro_centavos between 0 and 99999999999),
    pix_centavos bigint not null default 0 check (pix_centavos between 0 and 99999999999),
    cartao_centavos bigint not null default 0 check (cartao_centavos between 0 and 99999999999),
    total_centavos bigint generated always as (dinheiro_centavos + pix_centavos + cartao_centavos) stored,
    versao integer not null default 1 check (versao > 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id, data)
);
create or replace function private.atualizar_venda()
returns trigger language plpgsql set search_path = '' as $$
begin
    new.id := old.id;
    new.user_id := old.user_id;
    new.created_at := old.created_at;
    new.versao := old.versao + 1;
    new.updated_at := now();
    return new;
end;
$$;
drop trigger if exists vendas_atualizadas on public.vendas;
create trigger vendas_atualizadas before update on public.vendas
for each row execute function private.atualizar_venda();

alter table public.vendas enable row level security;
alter table public.vendas force row level security;
revoke all on public.vendas from public, anon, authenticated;
grant select, insert, update, delete on public.vendas to authenticated;
drop policy if exists consultar_vendas on public.vendas;
create policy consultar_vendas on public.vendas for select to authenticated
using (public.usuario_autorizado() and user_id = auth.uid());
drop policy if exists inserir_vendas on public.vendas;
create policy inserir_vendas on public.vendas for insert to authenticated
with check (public.usuario_autorizado() and user_id = auth.uid() and versao = 1);
drop policy if exists editar_vendas on public.vendas;
create policy editar_vendas on public.vendas for update to authenticated
using (public.usuario_autorizado() and user_id = auth.uid())
with check (public.usuario_autorizado() and user_id = auth.uid());
drop policy if exists excluir_vendas on public.vendas;
create policy excluir_vendas on public.vendas for delete to authenticated
using (public.usuario_autorizado() and user_id = auth.uid());
commit;
