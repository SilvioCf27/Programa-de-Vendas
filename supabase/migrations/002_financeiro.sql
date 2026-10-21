-- Execute depois de 001_vendas.sql. Não altera vendas nem importa dados.
begin;

create table public.financeiro_lancamentos (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null default auth.uid() references auth.users(id),
    tipo text not null check (tipo in ('despesa', 'taxa')),
    data date not null check (data between date '0001-01-01' and date '9999-12-31'),
    descricao text not null check (length(btrim(descricao)) between 1 and 200),
    valor_centavos bigint not null check (valor_centavos between 1 and 99999999999),
    meio text not null check (meio in ('Dinheiro', 'Pix', 'Cartão de crédito', 'Outro')),
    categoria text not null check (categoria in ('Casa', 'Feira', 'Outros', 'Compromisso inicial')),
    grupo text check (length(grupo) between 1 and 100),
    parcela integer not null default 1,
    parcelas integer not null default 1 check (parcelas between 1 and 120),
    versao integer not null default 1 check (versao > 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (parcela between 1 and parcelas),
    check ((parcelas = 1 and grupo is null) or
           (parcelas > 1 and grupo is not null and tipo = 'despesa' and meio = 'Cartão de crédito')),
    check (tipo <> 'taxa' or parcelas = 1)
);
create index financeiro_por_data on public.financeiro_lancamentos(user_id, data);
create unique index financeiro_parcela on public.financeiro_lancamentos(user_id, grupo, parcela)
    where grupo is not null;

create table public.financeiro_taxas_anuais (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null default auth.uid() references auth.users(id),
    ano integer not null check (ano between 1 and 9999),
    inicio date not null,
    fim date not null,
    valor_centavos bigint not null check (valor_centavos between 1 and 99999999999),
    natureza text not null default 'Confirmada' check (natureza in ('Confirmada', 'Estimada')),
    observacao text not null default '',
    versao integer not null default 1 check (versao > 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id, ano),
    check (inicio <= fim and extract(year from inicio) = ano and extract(year from fim) = ano)
);

-- Cada dia coberto por uma taxa é reservado uma única vez. A chave única
-- protege também contra transações simultâneas, sem ratear ajustes anuais.
create table private.financeiro_cobertura_taxas (
    user_id uuid not null references auth.users(id),
    data date not null,
    origem uuid not null,
    origem_tabela text not null,
    primary key (user_id, data)
);
create index cobertura_por_origem on private.financeiro_cobertura_taxas(origem);
alter table private.financeiro_cobertura_taxas enable row level security;
revoke all on private.financeiro_cobertura_taxas from public, anon, authenticated;

create function private.reservar_cobertura_taxa()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
    primeira date;
    ultima date;
    dia date;
begin
    if TG_OP <> 'INSERT' then
        delete from private.financeiro_cobertura_taxas where origem = old.id and origem_tabela = TG_TABLE_NAME;
    end if;
    if TG_OP = 'DELETE' then return old; end if;
    if TG_TABLE_NAME = 'financeiro_taxas_anuais' then
        primeira := new.inicio;
        ultima := new.fim;
    elsif new.tipo = 'taxa' then
        primeira := new.data;
        ultima := new.data;
    else
        return new;
    end if;
    dia := primeira;
    loop
        insert into private.financeiro_cobertura_taxas(user_id, data, origem, origem_tabela)
        values (new.user_id, dia, new.id, TG_TABLE_NAME);
        exit when dia = ultima;
        dia := dia + 1;
    end loop;
    return new;
end;
$$;
revoke all on function private.reservar_cobertura_taxa() from public, anon, authenticated;

create trigger atualizar_versao before update on public.financeiro_lancamentos
for each row execute function private.atualizar_venda();
create trigger reservar_taxa after insert or update or delete on public.financeiro_lancamentos
for each row execute function private.reservar_cobertura_taxa();
alter table public.financeiro_lancamentos enable row level security;
alter table public.financeiro_lancamentos force row level security;
revoke all on public.financeiro_lancamentos from public, anon, authenticated;
grant select, insert, update, delete on public.financeiro_lancamentos to authenticated;
create policy consultar on public.financeiro_lancamentos for select to authenticated
using (public.usuario_autorizado() and user_id = auth.uid());
create policy inserir on public.financeiro_lancamentos for insert to authenticated
with check (public.usuario_autorizado() and user_id = auth.uid() and versao = 1);
create policy editar on public.financeiro_lancamentos for update to authenticated
using (public.usuario_autorizado() and user_id = auth.uid())
with check (public.usuario_autorizado() and user_id = auth.uid());
create policy excluir on public.financeiro_lancamentos for delete to authenticated
using (public.usuario_autorizado() and user_id = auth.uid());

create trigger atualizar_versao before update on public.financeiro_taxas_anuais
for each row execute function private.atualizar_venda();
create trigger reservar_taxa after insert or update or delete on public.financeiro_taxas_anuais
for each row execute function private.reservar_cobertura_taxa();
alter table public.financeiro_taxas_anuais enable row level security;
alter table public.financeiro_taxas_anuais force row level security;
revoke all on public.financeiro_taxas_anuais from public, anon, authenticated;
grant select, insert, update, delete on public.financeiro_taxas_anuais to authenticated;
create policy consultar on public.financeiro_taxas_anuais for select to authenticated
using (public.usuario_autorizado() and user_id = auth.uid());
create policy inserir on public.financeiro_taxas_anuais for insert to authenticated
with check (public.usuario_autorizado() and user_id = auth.uid() and versao = 1);
create policy editar on public.financeiro_taxas_anuais for update to authenticated
using (public.usuario_autorizado() and user_id = auth.uid())
with check (public.usuario_autorizado() and user_id = auth.uid());
create policy excluir on public.financeiro_taxas_anuais for delete to authenticated
using (public.usuario_autorizado() and user_id = auth.uid());

commit;
