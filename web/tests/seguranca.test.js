import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';

const DONO = '11111111-1111-4111-8111-111111111111';
const OUTRO = '22222222-2222-4222-8222-222222222222';
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
      new URL('../../supabase/migrations/001_vendas.sql', import.meta.url),
      'utf8'
    )
  );
});
after(async () => {
  await db?.close();
});
async function usuario(id = '', role = 'authenticated') {
  await db.exec('reset role');
  await db.query("select set_config('request.jwt.claim.sub',$1,false)", [id]);
  await db.exec(`set role ${role}`);
}
test('sem proprietário configurado, o acesso começa fechado', async () => {
  await usuario(DONO);
  assert.equal(
    (await db.query('select public.usuario_autorizado() as permitido')).rows[0]
      .permitido,
    false
  );
  await assert.rejects(
    db.query("insert into public.vendas(data) values ('2030-01-01')")
  );
  await db.exec('reset role');
  await db.query('insert into private.app_config(owner_id) values ($1)', [
    DONO,
  ]);
});
test('proprietário grava centavos exatos; datas duplicadas e dinheiro negativo são recusados', async () => {
  await usuario(DONO);
  const r = await db.query(
    "insert into public.vendas(data,dinheiro_centavos,pix_centavos,cartao_centavos) values ('2030-01-01',101,202,303) returning *"
  );
  assert.equal(Number(r.rows[0].total_centavos), 606);
  await assert.rejects(
    db.query("insert into public.vendas(data) values ('2030-01-01')")
  );
  await assert.rejects(
    db.query(
      "insert into public.vendas(data,pix_centavos) values ('2030-01-02',-1)"
    )
  );
});
test('outro usuário não consegue ler, inserir, editar, excluir nem mudar o proprietário', async () => {
  await usuario(OUTRO);
  assert.equal((await db.query('select * from public.vendas')).rows.length, 0);
  await assert.rejects(
    db.query("insert into public.vendas(data) values ('2030-01-02')")
  );
  assert.equal(
    (await db.query('update public.vendas set pix_centavos=1 returning id'))
      .rows.length,
    0
  );
  assert.equal(
    (await db.query('delete from public.vendas returning id')).rows.length,
    0
  );
  await assert.rejects(db.query('select * from private.app_config'));
  await assert.rejects(
    db.query('update private.app_config set owner_id=$1', [OUTRO])
  );
});
test('visitante sem login não tem acesso à tabela', async () => {
  await usuario('', 'anon');
  await assert.rejects(db.query('select * from public.vendas'));
  await assert.rejects(db.query('select public.usuario_autorizado()'));
});
test('edição aumenta a versão e impede sobrescrever uma alteração concorrente', async () => {
  await usuario(DONO);
  const antes = (await db.query('select * from public.vendas')).rows[0];
  const editada = await db.query(
    'update public.vendas set pix_centavos=999 where id=$1 and versao=$2 returning *',
    [antes.id, antes.versao]
  );
  assert.equal(editada.rows[0].versao, 2);
  assert.equal(
    (
      await db.query(
        'update public.vendas set pix_centavos=888 where id=$1 and versao=$2 returning *',
        [antes.id, antes.versao]
      )
    ).rows.length,
    0
  );
  assert.equal(
    (
      await db.query(
        'delete from public.vendas where id=$1 and versao=$2 returning id',
        [antes.id, antes.versao]
      )
    ).rows.length,
    0
  );
});
