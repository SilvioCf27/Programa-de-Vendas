import {test,before,after} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {PGlite} from '@electric-sql/pglite';
const DONO='11111111-1111-4111-8111-111111111111',OUTRO='22222222-2222-4222-8222-222222222222';
const uuid=n=>`30000000-0000-4000-8000-${String(n).padStart(12,'0')}`;
let db;
before(async()=>{
 db=new PGlite();await db.exec(`create schema auth;create table auth.users(id uuid primary key);create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;create role anon;create role authenticated;grant usage on schema auth to authenticated,anon;grant execute on function auth.uid() to authenticated,anon;insert into auth.users values('${DONO}'),('${OUTRO}');`);
 for(const n of ['001_vendas','002_financeiro','003_migracao_desktop','004_sincronizacao','005_fechamentos','006_datas_compras','007_caixa','007_caixa'])await db.exec(await readFile(new URL('../../supabase/migrations/'+n+'.sql',import.meta.url),'utf8'));
 await db.exec(await readFile(new URL('../../supabase/auditoria_somente_leitura.sql',import.meta.url),'utf8'));
 await db.query('insert into private.app_config(owner_id) values($1)',[DONO]);
 await usuario();
});
after(async()=>{await db?.close();});
async function usuario(id=DONO,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);await db.exec('set role '+role);}
const salvar=async(pedido,n)=>(await db.query('select public.salvar_caixa($1::jsonb,$2::uuid) r',[JSON.stringify(pedido),uuid(n)])).rows[0].r;
const consultar=async()=>(await db.query('select public.consultar_caixa() r')).rows[0].r;
const abertura={id:uuid(1),tipo:'abertura',data:'2020-01-01',descricao:'Saldo inicial fictício',conta:null,valor_centavos:null,dinheiro_centavos:0,conta_centavos:10000};
test('migração pode ser repetida; abertura e recibo são idempotentes, sem aceitar reuso com dados diferentes',async()=>{
 const p={acao:'inserir',dados:abertura};const r=await salvar(p,101);assert.equal(r.registro.conta_centavos,10000);assert.deepEqual(await salvar(p,101),r);
 await assert.rejects(salvar({...p,dados:{...abertura,conta_centavos:999}},101),{code:'22023'});
 assert.equal((await consultar()).movimentos.length,1);
});
test('unicidade da abertura, datas, campos extras e escrita direta protegidos no servidor',async()=>{
 await assert.rejects(salvar({acao:'inserir',dados:{...abertura,id:uuid(2)}},102),{code:'40001'});
 await assert.rejects(salvar({acao:'inserir',dados:{...abertura,id:uuid(2),data:'9998-01-01'}},103),{code:'22023'});
 await assert.rejects(salvar({acao:'inserir',dados:{...abertura,id:uuid(2),user_id:OUTRO}},104),{code:'22023'});
 await assert.rejects(db.query('update public.caixa_movimentos set conta_centavos=1'),{code:'42501'});
 await assert.rejects(db.query('select * from private.caixa_recibos'),{code:'42501'});
});
test('entrada confirmada, cancelamento com versão, preservação do histórico e recusa de cancelar abertura com movimentos',async()=>{
 const dados={...abertura,id:uuid(3),tipo:'entrada',data:'2020-01-02',conta:'conta',valor_centavos:1234,dinheiro_centavos:null,conta_centavos:null};
 await assert.rejects(salvar({acao:'inserir',dados:{...dados,data:'2020-01-01'}},105),{code:'22023'});
 await salvar({acao:'inserir',dados},106);
 await assert.rejects(salvar({acao:'cancelar',id:abertura.id,versao:1},107),{code:'22023'});
 await assert.rejects(salvar({acao:'cancelar',id:dados.id,versao:9},108),{code:'40001'});
 const p={acao:'cancelar',id:dados.id,versao:1};const r=await salvar(p,109);assert.equal(r.registro.versao,2);assert.equal(r.registro.cancelado,true);assert.deepEqual(await salvar(p,109),r);
 assert.equal((await consultar()).movimentos.length,2);
});
test('conta não autorizada e anônimo não consultam nem alteram o caixa do proprietário',async()=>{
 await usuario(OUTRO);assert.equal((await db.query('select * from public.caixa_movimentos')).rows.length,0);
 await assert.rejects(consultar(),{code:'42501'});await assert.rejects(salvar({acao:'cancelar',id:abertura.id,versao:1},110),{code:'42501'});
 await usuario('', 'anon');await assert.rejects(consultar(),{code:'42501'});await assert.rejects(salvar({acao:'inserir',dados:abertura},111),{code:'42501'});
 await usuario();assert.equal((await consultar()).movimentos.length,2);
});

test('snapshot único inclui mais de mil vendas; movimentos de caixa não alteram nem criam despesas',async()=>{
 await db.exec("insert into public.vendas(data,dinheiro_centavos,pix_centavos,cartao_centavos) select date '2020-01-01'+n,100,200,300 from generate_series(1,1100) n");
 const s=await consultar();assert.equal(s.vendas.length,1100);assert.equal(s.despesas.length,0);
 assert.equal(s.vendas.reduce((n,r)=>n+r.dinheiro_centavos,0),110000);
});
