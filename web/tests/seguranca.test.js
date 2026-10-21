import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { PGlite } from "@electric-sql/pglite";

const DONO = "11111111-1111-4111-8111-111111111111";
const OUTRO = "22222222-2222-4222-8222-222222222222";
let db;
before(async () => {
  db = new PGlite();
  await db.exec(`create schema auth;
    create table auth.users (id uuid primary key);
    create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
    create role anon; create role authenticated;
    grant usage on schema auth to authenticated, anon;
    grant execute on function auth.uid() to authenticated, anon;
    insert into auth.users values ('${DONO}'),('${OUTRO}');`);
  await db.exec(
    await readFile(
      new URL("../../supabase/migrations/001_vendas.sql", import.meta.url),
      "utf8",
    ),
  );
  await db.exec(
    await readFile(
      new URL("../../supabase/migrations/002_financeiro.sql", import.meta.url),
      "utf8",
    ),
  );
});
after(async () => {
  await db?.close();
});
async function usuario(id = "", role = "authenticated") {
  await db.exec("reset role");
  await db.query("select set_config('request.jwt.claim.sub',$1,false)", [id]);
  await db.exec(`set role ${role}`);
}
test("sem proprietário configurado, o acesso começa fechado", async () => {
  await usuario(DONO);
  assert.equal(
    (await db.query("select public.usuario_autorizado() as permitido")).rows[0]
      .permitido,
    false,
  );
  await assert.rejects(
    db.query("insert into public.vendas(data) values ('2030-01-01')"),
  );
  await assert.rejects(db.query(DESPESA));
  await assert.rejects(db.query(ANUAL));
  await db.exec("reset role");
  await db.query("insert into private.app_config(owner_id) values ($1)", [
    DONO,
  ]);
});
test("proprietário grava centavos exatos; datas duplicadas e dinheiro negativo são recusados", async () => {
  await usuario(DONO);
  const r = await db.query(
    "insert into public.vendas(data,dinheiro_centavos,pix_centavos,cartao_centavos) values ('2030-01-01',101,202,303) returning *",
  );
  assert.equal(Number(r.rows[0].total_centavos), 606);
  await assert.rejects(
    db.query("insert into public.vendas(data) values ('2030-01-01')"),
  );
  await assert.rejects(
    db.query(
      "insert into public.vendas(data,pix_centavos) values ('2030-01-02',-1)",
    ),
  );
});
test("outro usuário não consegue ler, inserir, editar, excluir nem mudar o proprietário", async () => {
  await usuario(OUTRO);
  assert.equal((await db.query("select * from public.vendas")).rows.length, 0);
  await assert.rejects(
    db.query("insert into public.vendas(data) values ('2030-01-02')"),
  );
  assert.equal(
    (await db.query("update public.vendas set pix_centavos=1 returning id"))
      .rows.length,
    0,
  );
  assert.equal(
    (await db.query("delete from public.vendas returning id")).rows.length,
    0,
  );
  await assert.rejects(db.query("select * from private.app_config"));
  await assert.rejects(
    db.query("update private.app_config set owner_id=$1", [OUTRO]),
  );
});
test("visitante sem login não tem acesso à tabela", async () => {
  await usuario("", "anon");
  await assert.rejects(db.query("select * from public.vendas"));
  await assert.rejects(db.query("select public.usuario_autorizado()"));
});
test("edição aumenta a versão e impede sobrescrever uma alteração concorrente", async () => {
  await usuario(DONO);
  const antes = (await db.query("select * from public.vendas")).rows[0];
  const editada = await db.query(
    "update public.vendas set pix_centavos=999 where id=$1 and versao=$2 returning *",
    [antes.id, antes.versao],
  );
  assert.equal(editada.rows[0].versao, 2);
  assert.equal(
    (
      await db.query(
        "update public.vendas set pix_centavos=888 where id=$1 and versao=$2 returning *",
        [antes.id, antes.versao],
      )
    ).rows.length,
    0,
  );
  assert.equal(
    (
      await db.query(
        "delete from public.vendas where id=$1 and versao=$2 returning id",
        [antes.id, antes.versao],
      )
    ).rows.length,
    0,
  );
});

const DESPESA = `insert into public.financeiro_lancamentos
 (tipo,data,descricao,valor_centavos,meio,categoria)
 values ('despesa','2030-02-01','Teste fictício',12345,'Pix','Casa') returning *`;
const TAXA = (dia) => `insert into public.financeiro_lancamentos
 (tipo,data,descricao,valor_centavos,meio,categoria)
 values ('taxa','${dia}','Taxa fictícia',123,'Outro','Feira') returning *`;
const ANUAL = `insert into public.financeiro_taxas_anuais
 (ano,inicio,fim,valor_centavos,natureza)
 values (2030,'2030-01-01','2030-01-31',500,'Estimada') returning *`;

test("financeiro: proprietário grava despesas e preserva centavos e versões", async () => {
  await usuario(DONO);
  const registro = (await db.query(DESPESA)).rows[0];
  assert.equal(Number(registro.valor_centavos), 12345);
  const alterado = (
    await db.query(
      `update public.financeiro_lancamentos
    set valor_centavos=12346, id=$1, created_at='2000-01-01', user_id=$2
    where id=$3 and versao=1 returning *`,
      [OUTRO, OUTRO, registro.id],
    )
  ).rows[0];
  assert.equal(alterado.id, registro.id);
  assert.equal(alterado.user_id, DONO);
  assert.deepEqual(alterado.created_at, registro.created_at);
  assert.equal(alterado.versao, 2);
  assert.equal(
    (
      await db.query(
        "delete from public.financeiro_lancamentos where id=$1 and versao=1 returning id",
        [registro.id],
      )
    ).rows.length,
    0,
  );
  for (const valor of [0, -1, 100000000000]) {
    await assert.rejects(
      db.query(
        "update public.financeiro_lancamentos set valor_centavos=$1 where id=$2",
        [valor, registro.id],
      ),
    );
  }
});

test("financeiro: parcelas mantêm grupo e vencimento; duplicação e números inválidos são recusados", async () => {
  await usuario(DONO);
  const inserir = (numero) =>
    db.query(
      `insert into public.financeiro_lancamentos
    (tipo,data,descricao,valor_centavos,meio,categoria,grupo,parcela,parcelas)
    values ('despesa','2030-03-09','Parcela fictícia',100,'Cartão de crédito','Outros','grupo-ficticio',$1,3)`,
      [numero],
    );
  await inserir(1);
  await inserir(2);
  await assert.rejects(inserir(1));
  await assert.rejects(inserir(0));
  await assert.rejects(inserir(4));
  await assert.rejects(
    db.query(
      "update public.financeiro_lancamentos set meio='Pix' where grupo='grupo-ficticio'",
    ),
  );
});

test("financeiro: cobertura impede taxa anual e diária sobre o mesmo dia, nas duas ordens", async () => {
  await usuario(DONO);
  let anual = (await db.query(ANUAL)).rows[0];
  await assert.rejects(db.query(TAXA("2030-01-15")));
  // A atualização recusada não perde a reserva original.
  const diaria = (await db.query(TAXA("2030-02-15"))).rows[0];
  await assert.rejects(
    db.query(
      "update public.financeiro_lancamentos set data='2030-01-15' where id=$1",
      [diaria.id],
    ),
  );
  await assert.rejects(db.query(TAXA("2030-02-15")));
  await db.query(
    "delete from public.financeiro_taxas_anuais where id=$1 and versao=$2",
    [anual.id, anual.versao],
  );
  const janeiro = (await db.query(TAXA("2030-01-15"))).rows[0];
  await assert.rejects(db.query(ANUAL));
  await db.query("delete from public.financeiro_lancamentos where id=$1", [
    janeiro.id,
  ]);
  anual = (await db.query(ANUAL)).rows[0];
  assert.equal(anual.natureza, "Estimada");
  await assert.rejects(
    db.query(
      "update public.financeiro_taxas_anuais set fim='2031-01-01' where id=$1",
      [anual.id],
    ),
  );
  await assert.rejects(
    db.query(
      "update public.financeiro_taxas_anuais set inicio='2030-02-01' where id=$1",
      [anual.id],
    ),
  );
  await assert.rejects(
    db.query(
      "update public.financeiro_taxas_anuais set natureza='Outra' where id=$1",
      [anual.id],
    ),
  );
  const atualizada = (
    await db.query(
      "update public.financeiro_taxas_anuais set observacao='Teste' where id=$1 and versao=1 returning *",
      [anual.id],
    )
  ).rows[0];
  assert.equal(atualizada.versao, 2);
  assert.equal(
    (
      await db.query(
        "update public.financeiro_taxas_anuais set valor_centavos=1 where id=$1 and versao=1 returning id",
        [anual.id],
      )
    ).rows.length,
    0,
  );
  // A migração e as operações financeiras preservam as vendas existentes.
  assert.equal((await db.query("select * from public.vendas")).rows.length, 1);
});

test("financeiro: outra conta e visitantes não leem nem alteram dados ou reservas", async () => {
  await usuario(OUTRO);
  for (const tabela of ["financeiro_lancamentos", "financeiro_taxas_anuais"]) {
    assert.equal(
      (await db.query(`select * from public.${tabela}`)).rows.length,
      0,
    );
    assert.equal(
      (
        await db.query(
          `update public.${tabela} set valor_centavos=1 returning id`,
        )
      ).rows.length,
      0,
    );
    assert.equal(
      (await db.query(`delete from public.${tabela} returning id`)).rows.length,
      0,
    );
  }
  await assert.rejects(db.query(DESPESA));
  await assert.rejects(db.query(ANUAL));
  await assert.rejects(
    db.query("select * from private.financeiro_cobertura_taxas"),
  );
  await usuario("", "anon");
  for (const tabela of ["financeiro_lancamentos", "financeiro_taxas_anuais"]) {
    await assert.rejects(db.query(`select * from public.${tabela}`));
  }
  await assert.rejects(db.query(DESPESA));
  await assert.rejects(db.query(ANUAL));
});
