import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';
import { periodoFechamento, diaNoMes, definirFechamentos } from '../src/fechamento.js';
import { primeiraFatura } from '../src/financeiro.js';

test('mudança futura mantém ciclos contíguos e preserva os períodos anteriores', () => {
  const historico = [{ vigencia: '2090-11-01', dia: 14 }];
  const antes = periodoFechamento(2090, 9, historico);
  assert.deepEqual(antes, { inicio: '2090-09-10', fim: '2090-10-09' });
  assert.deepEqual(periodoFechamento(2090, 10, historico), { inicio: '2090-10-10', fim: '2090-11-14' });
  assert.deepEqual(periodoFechamento(2090, 11, historico), { inicio: '2090-11-15', fim: '2090-12-14' });
  assert.equal(diaNoMes(2092, 2, [{ vigencia: '2090-01-01', dia: 31 }]), 29);
  definirFechamentos({ versao: 1, historico });
  assert.equal(primeiraFatura('2090-11-14'), '2090-12-14');
  definirFechamentos({ versao: 0, historico: [] });
});

let db;
const DONO = '11111111-1111-4111-8111-111111111111', OUTRO = '22222222-2222-4222-8222-222222222222';
before(async () => {
  db = new PGlite();
  await db.exec(`create schema auth; create table auth.users(id uuid primary key);
    create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
    create role anon; create role authenticated;
    insert into auth.users values ('${DONO}'),('${OUTRO}');`);
  for (const nome of ['001_vendas.sql', '005_fechamentos.sql', '005_fechamentos.sql'])
    await db.exec(await readFile(new URL('../../supabase/migrations/' + nome, import.meta.url), 'utf8'));
  await db.query('insert into private.app_config(owner_id) values ($1)', [DONO]);
});
after(async () => { await db?.close(); });
async function usuario(id = DONO) {
  await db.exec('reset role');
  await db.query("select set_config('request.jwt.claim.sub',$1,false)", [id]);
  await db.exec('set role authenticated');
}
test('SQL preserva histórico, impede concorrência e recusa contas não autorizadas', async () => {
  await usuario();
  assert.deepEqual((await db.query('select public.consultar_fechamentos() as c')).rows[0].c, { versao: 0, historico: [] });
  const salvar = (versao, vigencia, dia) => db.query('select public.salvar_fechamento($1,$2,$3) as c', [versao, vigencia, dia]);
  const primeira = (await salvar(0, '2090-11-01', 14)).rows[0].c;
  assert.equal(primeira.versao, 1);
  await assert.rejects(salvar(0, '2091-01-01', 12), /configuração mudou/i);
  await assert.rejects(salvar(1, '2020-01-01', 12), /vigência/i);
  await assert.rejects(salvar(1, '2090-10-01', 12), /regra mais recente/i);
  const segunda = (await salvar(1, '2091-01-01', 12)).rows[0].c;
  assert.deepEqual(segunda.historico, [{ vigencia: '2090-11-01', dia: 14 }, { vigencia: '2091-01-01', dia: 12 }]);
  await assert.rejects(db.query('select * from private.configuracoes_fechamento'), /permission denied/i);
  await usuario(OUTRO);
  await assert.rejects(db.query('select public.consultar_fechamentos()'), /autorizada/i);
  await assert.rejects(salvar(0, '2091-01-01', 12), /autorizada/i);
});
