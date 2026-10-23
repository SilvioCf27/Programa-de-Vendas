import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  limitesFinanceiros,
  resumoFinanceiro,
  lancamentoFormulario,
  anualFormulario,
  erroFinanceiro,
} from '../src/financeiro.js';
const periodo = { inicio: '2030-01-01', fim: '2030-01-31' };
const dados = () => ({
  vendas: [
    {
      data: '2030-01-02',
      dinheiro_centavos: 10000,
      pix_centavos: 5000,
      cartao_centavos: 5000,
    },
    {
      data: '2030-01-03',
      dinheiro_centavos: 0,
      pix_centavos: 0,
      cartao_centavos: 0,
    },
  ],
  financeiro_lancamentos: [
    { data: '2030-01-04', tipo: 'despesa', valor_centavos: 3000 },
    { data: '2030-01-05', tipo: 'taxa', valor_centavos: 100 },
  ],
  financeiro_taxas_anuais: [
    {
      ano: 2030,
      inicio: '2030-01-01',
      fim: '2030-01-31',
      valor_centavos: 500,
      natureza: 'Estimada',
    },
  ],
});
test('financeiro preserva a regra do desktop: bruto, taxas, líquido, despesas, saldo e falta', () => {
  const r = resumoFinanceiro(dados(), periodo);
  assert.deepEqual(
    [r.bruto, r.taxas, r.liquido, r.despesas, r.saldo, r.falta],
    [20000, 600, 19400, 3000, 16400, 0]
  );
  assert.deepEqual(r.estimados, [2030]);
  assert.deepEqual(r.parciais, []);
  assert.deepEqual(r.semanas, [['2029-12-31', 3000]]);
});
test('taxa anual parcial não é rateada e despesas fora do recorte não entram', () => {
  const d = dados();
  d.financeiro_lancamentos.push({
    data: '2030-02-01',
    tipo: 'despesa',
    valor_centavos: 99999,
  });
  const r = resumoFinanceiro(d, { inicio: '2030-01-02', fim: '2030-01-10' });
  assert.equal(r.taxas, 100);
  assert.equal(r.despesas, 3000);
  assert.deepEqual(r.parciais, [2030]);
  assert.equal(r.saldo, 16900);
  assert.deepEqual(r.estimados, [2030]);
});
test('sem vendas, falta corresponde a taxas mais despesas e intervalos incluem os limites', () => {
  const d = dados();
  d.vendas = [];
  const r = resumoFinanceiro(d, periodo);
  assert.equal(r.saldo, -3600);
  assert.equal(r.falta, 3600);
  assert.deepEqual(limitesFinanceiros('Fechamento', '2030-12-01'), {
    inicio: '2030-12-10',
    fim: '2031-01-09',
  });
  assert.deepEqual(limitesFinanceiros('Semana', '2030-01-06'), {
    inicio: '2029-12-31',
    fim: '2030-01-06',
  });
  assert.deepEqual(limitesFinanceiros('Semana', '2030-01-07'), {
    inicio: '2030-01-07',
    fim: '2030-01-13',
  });
  assert.throws(() => limitesFinanceiros('Semana', '2030-02-30'));
});
const form = () => ({
  tipo: 'despesa',
  data: '2030-01-31',
  descricao: 'Compra fictícia',
  valor: '123,45',
  meio: 'Cartão de crédito',
  categoria: 'Casa',
  parcelas: '3',
});
test('parcelamento mantém valor por parcela, grupo e dia original após fevereiro', () => {
  let i = 0;
  const linhas = lancamentoFormulario(form(), null, () => `id-${++i}`);
  assert.deepEqual(
    linhas.map((r) => r.dados.data),
    ['2030-01-31', '2030-02-28', '2030-03-31']
  );
  assert.deepEqual(
    linhas.map((r) => r.dados.valor_centavos),
    [12345, 12345, 12345]
  );
  assert.equal(new Set(linhas.map((r) => r.dados.grupo)).size, 1);
  assert.deepEqual(
    linhas.map((r) => r.dados.parcela),
    [1, 2, 3]
  );
  assert.equal(new Set(linhas.map((r) => r.id)).size, 3);
  const anterior = {
    id: 'original',
    versao: 7,
    grupo: 'grupo',
    parcela: 2,
    parcelas: 3,
  };
  const editado = lancamentoFormulario({ ...form(), parcelas: 1 }, anterior)[0];
  assert.equal(editado.id, 'original');
  assert.equal(editado.versao, 7);
  assert.equal(editado.dados.parcela, 2);
  assert.equal(editado.dados.parcelas, 3);
});
test('lançamentos inválidos são recusados antes de escrever', () => {
  for (const alteracao of [
    { valor: '0' },
    { valor: '1,001' },
    { descricao: ' ' },
    { parcelas: '121' },
    { parcelas: '2', meio: 'Pix' },
    { tipo: 'taxa', parcelas: '2' },
    { data: '2030-02-30' },
  ])
    assert.throws(() => lancamentoFormulario({ ...form(), ...alteracao }));
});
test('ajustes anuais validam cobertura e preservam natureza e versão', () => {
  const f = {
    ano: '2030',
    inicio: '2030-01-01',
    fim: '2030-12-31',
    valor: '50,01',
    natureza: 'Estimada',
    observacao: ' teste ',
  };
  const r = anualFormulario(f, { id: 'original', versao: 2 })[0];
  assert.equal(r.dados.valor_centavos, 5001);
  assert.equal(r.dados.natureza, 'Estimada');
  assert.equal(r.versao, 2);
  for (const alteracao of [
    { fim: '2031-01-01' },
    { inicio: '2030-12-31', fim: '2030-01-01' },
    { natureza: 'Outra' },
    { valor: '-1' },
  ])
    assert.throws(() => anualFormulario({ ...f, ...alteracao }));
  assert.match(erroFinanceiro({ code: '23505' }), /ajuste anual/);
});

test('compra no dia do fechamento vai para a fatura seguinte', async () => {
  const { primeiraFatura } = await import('../src/financeiro.js');
  assert.equal(primeiraFatura('2026-09-08'), '2026-09-09');
  assert.equal(primeiraFatura('2026-09-09'), '2026-10-09');
  assert.equal(primeiraFatura('2026-12-09'), '2027-01-09');
  assert.equal(primeiraFatura('2026-02-28', 31), '2026-03-31');
  const r = lancamentoFormulario({ ...form(), data: primeiraFatura('2026-09-09'), parcelas: '3' });
  assert.deepEqual(r.map(op => op.dados.data), ['2026-10-09', '2026-11-09', '2026-12-09']);
});

test('taxas semanais mantêm datas, editam as existentes e recusam histórico sobreposto', async () => {
  const { taxasSemanaFormulario } = await import('../src/financeiro.js');
  const existentes = [{ id: 'sexta', versao: 2, tipo: 'taxa', data: '2026-10-09', descricao: 'Taxa', valor_centavos: 100, meio: 'Outro', categoria: 'Feira', grupo: null, parcela: 1, parcelas: 1 }];
  const ops = taxasSemanaFormulario('2026-10-05', { '2026-10-09': '2,00', '2026-10-11': '3,00' }, existentes, [], () => 'domingo');
  assert.deepEqual(ops.map(op => [op.acao, op.dados.data, op.dados.valor_centavos]), [['editar', '2026-10-09', 200], ['inserir', '2026-10-11', 300]]);
  assert.equal(ops[0].id, 'sexta');
  assert.equal(ops[0].versao, 2);
  assert.throws(() => taxasSemanaFormulario('2026-10-05', { '2026-10-11': '3,00' }, [], [{ inicio: '2026-01-01', fim: '2026-12-31' }]), /histórico/);
  assert.throws(() => taxasSemanaFormulario('2026-10-05', { '2026-10-09': '0,00' }, existentes, []), /Excluir/);
});
