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
    "004_sincronizacao.sql",
    "005_fechamentos.sql",
    "006_datas_compras.sql",
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
  await db.exec("reset role; delete from public.nuvem_operacoes;");
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
async function sincronizar(alteracoes = [], id = null) {
  return (
    await db.query(
      "select public.sincronizar_desktop($1::jsonb,$2::uuid) as resultado",
      [JSON.stringify(alteracoes), id],
    )
  ).rows[0].resultado;
}
const OP1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const OP2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
function operacao(tabela, acao, registro, corpo = null) {
  return {
    tabela,
    acao,
    id: registro.id,
    versao: acao === "inserir" ? null : registro.versao,
    dados: corpo,
  };
}
function corpo(registro) {
  return Object.fromEntries(
    Object.entries(registro).filter(([k]) => !["id", "versao"].includes(k)),
  );
}
test("snapshot retorna todas as tabelas e versões apenas da conta autorizada", async () => {
  await migrar(dados(), true);
  const r = await sincronizar();
  assert.equal(r.protocolo, 1);
  assert.equal(r.usuario_id, DONO);
  assert.equal(r.dados.vendas.length, 2);
  assert.equal(r.dados.financeiro_taxas_anuais.length, 1);
  assert.equal(r.dados.vendas[0].versao, 1);
  assert.equal("user_id" in r.dados.vendas[0], false);
  await usuario(OUTRO);
  await assert.rejects(sincronizar(), { code: "42501" });
  await usuario("", "anon");
  await assert.rejects(sincronizar(), { code: "42501" });
});
test("edição, inclusão e exclusão de vendas são atômicas e aumentam versões", async () => {
  await migrar(dados(), true);
  const antes = (await sincronizar()).dados.vendas;
  const alteracoes = [
    operacao("vendas", "editar", antes[0], {
      ...corpo(antes[0]),
      pix_centavos: 1234,
    }),
    operacao("vendas", "excluir", antes[1]),
    operacao(
      "vendas",
      "inserir",
      { id: "66666666-6666-4666-8666-666666666666" },
      {
        data: "2030-02-01",
        dinheiro_centavos: 123,
        pix_centavos: 0,
        cartao_centavos: 456,
      },
    ),
  ];
  const r = await sincronizar(alteracoes, OP1);
  assert.equal(r.dados.vendas.length, 2);
  assert.equal(r.dados.vendas.find((v) => v.id === antes[0].id).versao, 2);
  assert.equal(
    r.dados.vendas.find((v) => v.id === antes[0].id).pix_centavos,
    1234,
  );
  assert.equal(
    r.dados.vendas.some((v) => v.id === antes[1].id),
    false,
  );
  assert.deepEqual((await sincronizar(alteracoes, OP1)).dados, r.dados);
});
test("recibo torna repetição segura mesmo após edição posterior pelo celular", async () => {
  await migrar(dados(), true);
  const venda = (await sincronizar()).dados.vendas[0];
  const alteracoes = [
    operacao("vendas", "editar", venda, { ...corpo(venda), pix_centavos: 999 }),
  ];
  await sincronizar(alteracoes, OP1);
  await db.query("update public.vendas set pix_centavos=888 where id=$1", [
    venda.id,
  ]);
  const repetida = await sincronizar(alteracoes, OP1);
  assert.equal(repetida.repetida, true);
  assert.equal(
    repetida.dados.vendas.find((v) => v.id === venda.id).pix_centavos,
    888,
  );
  assert.equal(repetida.dados.vendas.find((v) => v.id === venda.id).versao, 3);
  await assert.rejects(sincronizar([], OP1), { code: "PFS02" });
  await assert.rejects(
    db.exec("update public.nuvem_operacoes set assinatura='x'"),
    { code: "42501" },
  );
  await assert.rejects(db.exec("delete from public.nuvem_operacoes"), {
    code: "42501",
  });
});
test("versão desatualizada cancela o lote inteiro sem registrar recibo", async () => {
  await migrar(dados(), true);
  const vendas = (await sincronizar()).dados.vendas;
  await db.query("update public.vendas set pix_centavos=999 where id=$1", [
    vendas[1].id,
  ]);
  const lote = vendas.map((v) =>
    operacao("vendas", "editar", v, { ...corpo(v), pix_centavos: 111 }),
  );
  await assert.rejects(sincronizar(lote, OP1), { code: "PFS01" });
  const atual = (await sincronizar()).dados.vendas;
  assert.equal(
    atual.find((v) => v.id === vendas[0].id).pix_centavos,
    vendas[0].pix_centavos,
  );
  assert.equal(
    (await db.query("select * from public.nuvem_operacoes")).rows.length,
    0,
  );
});
test("financeiro sincroniza valores e parcelas; erro tardio desfaz vendas e despesas", async () => {
  await migrar(dados(), true);
  const anterior = (await sincronizar()).dados;
  const parcela = anterior.financeiro_lancamentos[0];
  const anual = anterior.financeiro_taxas_anuais[0];
  const lote = [
    operacao("financeiro_lancamentos", "editar", parcela, {
      ...corpo(parcela),
      valor_centavos: 12346,
    }),
    operacao("financeiro_taxas_anuais", "editar", anual, {
      ...corpo(anual),
      valor_centavos: 501,
    }),
  ];
  const final = (await sincronizar(lote, OP1)).dados;
  assert.equal(
    final.financeiro_lancamentos.find((r) => r.id === parcela.id).parcelas,
    2,
  );
  assert.equal(final.financeiro_taxas_anuais[0].valor_centavos, 501);
  const venda = final.vendas[0];
  const errado = [
    operacao("vendas", "editar", venda, {
      ...corpo(venda),
      dinheiro_centavos: 777,
    }),
    operacao(
      "financeiro_lancamentos",
      "inserir",
      { id: OP2 },
      {
        tipo: "taxa",
        data: "2030-01-15",
        descricao: "Teste",
        valor_centavos: 1,
        meio: "Outro",
        categoria: "Feira",
        grupo: null,
        parcela: 1,
        parcelas: 1,
      },
    ),
  ];
  await assert.rejects(sincronizar(errado, OP2), { code: "23505" });
  assert.deepEqual((await sincronizar()).dados, final);
});
test("tabelas arbitrárias e campos técnicos não entram na operação", async () => {
  await migrar(dados(), true);
  const venda = (await sincronizar()).dados.vendas[0];
  await assert.rejects(
    sincronizar([operacao("auth.users", "excluir", venda)], OP1),
    { code: "PFS02" },
  );
  await assert.rejects(
    sincronizar(
      [
        operacao("vendas", "editar", venda, {
          ...corpo(venda),
          user_id: OUTRO,
        }),
      ],
      OP1,
    ),
    { code: "PFS02" },
  );
  const op = operacao("vendas", "excluir", venda);
  await assert.rejects(sincronizar([op, op], OP1), { code: "PFS02" });
  assert.equal((await sincronizar()).dados.vendas.length, 2);
});

test('editar compra inteira usa um lote atômico e conflito em uma parcela impede todas', async () => {
  const sincronizar = async (alteracoes = [], id = null) => (await db.query('select public.sincronizar_desktop_v2($1::jsonb,$2::uuid) as resultado',[JSON.stringify(alteracoes),id])).rows[0].resultado;
  const { lancamentoFormulario, compraDoLancamento } = await import('../src/financeiro.js');
  const form = {tipo:'despesa', data:'2030-05-09', descricao:'Compra de teste', valor:'100,00', meio:'Cartão de crédito', categoria:'Casa', parcelas:3};
  const inicial = await sincronizar(lancamentoFormulario(form), OP1);
  const registros = inicial.dados.financeiro_lancamentos;
  const ultima = registros.find(r => r.parcela === 3);
  const compra = compraDoLancamento(ultima, registros);
  const ops = lancamentoFormulario({...form, valor:'150,01', parcelas:5}, compra);
  await sincronizar([{...ops[0], dados:{...corpo(registros.find(r=>r.id===ops[0].id)), descricao:'Mudança concorrente'}}], OP2);
  await assert.rejects(sincronizar(ops, 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'), {code:'PFS01'});
  let atuais = (await sincronizar()).dados.financeiro_lancamentos;
  assert.equal(atuais.length, 3);
  assert.equal(atuais.reduce((s,r)=>s+r.valor_centavos,0), 10000);
  const atualizada = compraDoLancamento(atuais.find(r=>r.parcela===3), atuais);
  const salvo = await sincronizar(lancamentoFormulario({...form,valor:'150,01',parcelas:5},atualizada), 'dddddddd-dddd-4ddd-8ddd-dddddddddddd');
  atuais = salvo.dados.financeiro_lancamentos.sort((a,b)=>a.parcela-b.parcela);
  assert.deepEqual(atuais.map(r=>r.valor_centavos),[3000,3000,3000,3000,3001]);
  assert.ok(registros.every(r=>atuais.some(n=>n.id===r.id)));
});

test('SQL 006 preserva dados antigos, transmite a compra e mantém recibos de ambas as versões', async () => {
  await migrar(dados(),true);
  const antigo = await sincronizar();
  assert.ok(antigo.dados.financeiro_lancamentos.every(r=>!('data_compra' in r)));
  const sql = await readFile(new URL('../../supabase/migrations/006_datas_compras.sql', import.meta.url),'utf8');
  await db.exec('reset role'); await db.exec(sql); await usuario();
  assert.deepEqual((await sincronizar()).dados, antigo.dados);
  const nova = { tabela:'financeiro_lancamentos',acao:'inserir',id:'99999999-9999-4999-8999-999999999999',versao:null,
    dados:{tipo:'despesa',data:'2026-11-09',data_compra:'2026-10-09',descricao:'Mercado de teste',valor_centavos:1300,meio:'Cartão de crédito',categoria:'Feira',grupo:null,parcela:1,parcelas:1}};
  const v2 = async(ops,id=null)=>(await db.query('select public.sincronizar_desktop_v2($1::jsonb,$2::uuid) r',[JSON.stringify(ops),id])).rows[0].r;
  const salvo = await v2([nova],OP1);
  assert.equal(salvo.protocolo,2);
  assert.equal(salvo.dados.financeiro_lancamentos.find(r=>r.id===nova.id).data_compra,'2026-10-09');
  assert.equal((await v2([nova],OP1)).repetida,true);
  await assert.rejects(v2([{...nova,dados:{...nova.dados,data_compra:'2026-10-08'}}],OP1),{code:'PFS02'});
  const velho=(await sincronizar()).dados.financeiro_lancamentos.find(r=>r.id===nova.id);
  await sincronizar([operacao('financeiro_lancamentos','editar',velho,{...corpo(velho),descricao:'Edição por aplicativo antigo'})],OP2);
  assert.equal((await v2([])).dados.financeiro_lancamentos.find(r=>r.id===nova.id).data_compra,null);
  await usuario(OUTRO); await assert.rejects(v2([]),{code:'42501'});
});


test('roteiro de auditoria consulta permissões sem expor ou alterar dados', async () => {
  await db.exec('reset role');
  const antes=(await db.query('select count(*) n from public.financeiro_lancamentos')).rows[0].n;
  const resultados=await db.exec(await readFile(new URL('../../supabase/auditoria_somente_leitura.sql',import.meta.url),'utf8'));
  const tabelas=resultados.find(r=>r.rows.some(l=>'anon_pode_consultar' in l)).rows;
  assert.equal(tabelas.length,4);
  assert.ok(tabelas.every(r=>r.rls && r.force_rls && !r.anon_pode_consultar && !r.anon_pode_inserir && !r.anon_pode_editar && !r.anon_pode_excluir));
  assert.equal((await db.query('select count(*) n from public.financeiro_lancamentos')).rows[0].n,antes);
});
