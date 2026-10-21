import { test, before, after, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { PGlite } from "@electric-sql/pglite";
const DONO = "11111111-1111-4111-8111-111111111111";
const OUTRO = "22222222-2222-4222-8222-222222222222";
let db;
before(async () => {
  db = new PGlite();
  await db.exec(`create schema auth;
    create table auth.users(id uuid primary key);
    create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
    create role anon; create role authenticated;
    grant usage on schema auth to authenticated, anon;
    grant execute on function auth.uid() to authenticated, anon;
    insert into auth.users values ('${DONO}'),('${OUTRO}');`);
  for (const arquivo of [
    "001_vendas.sql",
    "002_financeiro.sql",
    "003_migracao_desktop.sql",
  ]) {
    await db.exec(
      await readFile(
        new URL("../../supabase/migrations/" + arquivo, import.meta.url),
        "utf8",
      ),
    );
  }
  await db.query("insert into private.app_config(owner_id) values ($1)", [
    DONO,
  ]);
});
after(async () => {
  await db?.close();
});
async function usuario(id = DONO, role = "authenticated") {
  await db.exec("reset role");
  await db.query("select set_config('request.jwt.claim.sub',$1,false)", [id]);
  await db.exec(`set role ${role}`);
}
beforeEach(async () => {
  await usuario();
  await db.exec(
    "delete from public.financeiro_lancamentos; delete from public.financeiro_taxas_anuais; delete from public.vendas;",
  );
});
function dados() {
  return {
    vendas: [
      {
        data: "2030-01-01",
        dinheiro_centavos: 101,
        pix_centavos: 202,
        cartao_centavos: 303,
      },
      {
        data: "2030-01-02",
        dinheiro_centavos: 0,
        pix_centavos: 0,
        cartao_centavos: 0,
      },
    ],
    financeiro_lancamentos: [
      {
        id: "33333333-3333-4333-8333-333333333333",
        tipo: "despesa",
        data: "2030-02-09",
        descricao: "Parcela fictícia",
        valor_centavos: 12345,
        meio: "Cartão de crédito",
        categoria: "Casa",
        grupo: "grupo-ficticio",
        parcela: 1,
        parcelas: 2,
      },
      {
        id: "44444444-4444-4444-8444-444444444444",
        tipo: "despesa",
        data: "2030-03-09",
        descricao: "Parcela fictícia",
        valor_centavos: 12345,
        meio: "Cartão de crédito",
        categoria: "Casa",
        grupo: "grupo-ficticio",
        parcela: 2,
        parcelas: 2,
      },
    ],
    financeiro_taxas_anuais: [
      {
        ano: 2030,
        inicio: "2030-01-01",
        fim: "2030-01-31",
        valor_centavos: 500,
        natureza: "Estimada",
        observacao: "Ajuste fictício",
      },
    ],
  };
}
async function migrar(payload, aplicar = false) {
  return (
    await db.query("select public.migrar_desktop($1::jsonb,$2) as resultado", [
      JSON.stringify(payload),
      aplicar,
    ])
  ).rows[0].resultado;
}
async function quantidades() {
  return Promise.all(
    ["vendas", "financeiro_lancamentos", "financeiro_taxas_anuais"].map(
      async (tabela) =>
        Number(
          (await db.query(`select count(*) as n from public.${tabela}`)).rows[0]
            .n,
        ),
    ),
  );
}
test("conferência não grava; transferência preserva campos e repetição não duplica", async () => {
  const payload = dados();
  const previa = await migrar(payload);
  assert.equal(previa.aplicado, false);
  assert.deepEqual(await quantidades(), [0, 0, 0]);
  assert.deepEqual(previa.novos, {
    vendas: 2,
    financeiro_lancamentos: 2,
    financeiro_taxas_anuais: 1,
  });
  const final = await migrar(payload, true);
  assert.deepEqual(final.dados, payload);
  assert.deepEqual(await quantidades(), [2, 2, 1]);
  const repetida = await migrar(payload, true);
  assert.deepEqual(repetida.dados, payload);
  assert.deepEqual(repetida.novos, {
    vendas: 0,
    financeiro_lancamentos: 0,
    financeiro_taxas_anuais: 0,
  });
  assert.equal(
    Number(
      (await db.query("select sum(total_centavos) as total from public.vendas"))
        .rows[0].total,
    ),
    606,
  );
});
test("divergência na última tabela desfaz inserções anteriores da mesma operação", async () => {
  await db.exec(
    "insert into public.financeiro_taxas_anuais(ano,inicio,fim,valor_centavos) values (2030,'2030-01-01','2030-01-31',999)",
  );
  await assert.rejects(migrar(dados(), true), { code: "PFM01" });
  assert.deepEqual(await quantidades(), [0, 0, 1]);
});
test("mudança na nuvem após a conferência bloqueia envio sem sobrescrever", async () => {
  await migrar(dados());
  await db.exec(
    "insert into public.vendas(data,pix_centavos) values ('2030-01-01',999)",
  );
  await assert.rejects(migrar(dados(), true), { code: "PFM01" });
  assert.deepEqual(await quantidades(), [1, 0, 0]);
  assert.equal(
    Number(
      (await db.query("select pix_centavos from public.vendas")).rows[0]
        .pix_centavos,
    ),
    999,
  );
});
test("taxas sobrepostas causam rollback integral, inclusive reservas privadas", async () => {
  const payload = dados();
  payload.financeiro_lancamentos.push({
    id: "55555555-5555-4555-8555-555555555555",
    tipo: "taxa",
    data: "2030-01-15",
    descricao: "Taxa fictícia",
    valor_centavos: 123,
    meio: "Outro",
    categoria: "Feira",
    grupo: null,
    parcela: 1,
    parcelas: 1,
  });
  await assert.rejects(migrar(payload, true), { code: "23505" });
  assert.deepEqual(await quantidades(), [0, 0, 0]);
  await db.exec("reset role");
  assert.equal(
    Number(
      (
        await db.query(
          "select count(*) as n from private.financeiro_cobertura_taxas",
        )
      ).rows[0].n,
    ),
    0,
  );
});
test("registros extras, duplicações, campos técnicos e valores inválidos são recusados", async () => {
  await db.exec("insert into public.vendas(data) values ('2030-12-31')");
  await assert.rejects(migrar(dados(), true), { code: "PFM01" });
  await db.exec("delete from public.vendas");
  const duplicado = dados();
  duplicado.vendas.push(duplicado.vendas[0]);
  await assert.rejects(migrar(duplicado, true), { code: "PFM02" });
  const tecnico = dados();
  tecnico.vendas[0].user_id = OUTRO;
  await assert.rejects(migrar(tecnico, true), { code: "PFM02" });
  const invalido = dados();
  invalido.financeiro_taxas_anuais[0].valor_centavos = -1;
  await assert.rejects(migrar(invalido, true), { code: "23514" });
  await assert.rejects(migrar({ vendas: [] }, true), { code: "PFM02" });
  assert.deepEqual(await quantidades(), [0, 0, 0]);
});
test("anon e outra conta não executam migração nem obtêm dados", async () => {
  await migrar(dados(), true);
  await usuario(OUTRO);
  await assert.rejects(migrar(dados()), { code: "42501" });
  await assert.rejects(migrar(dados(), true), { code: "42501" });
  await usuario("", "anon");
  await assert.rejects(migrar(dados()), { code: "42501" });
  await usuario();
  assert.deepEqual(await quantidades(), [2, 2, 1]);
});
