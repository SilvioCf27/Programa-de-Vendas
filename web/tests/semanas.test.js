import test from 'node:test';
import assert from 'node:assert/strict';
import { limitesSemana, resumoSemana, agruparSemanas, selecaoInicial, carregarPeriodoInicial, salvarPeriodoInicial, PERIODOS_INICIAIS } from '../src/semanas.js';
import { definirFechamentos } from '../src/fechamento.js';
const venda = (data, dinheiro = 0, pix = 0, cartao = 0) => ({ data, dinheiro_centavos: dinheiro, pix_centavos: pix, cartao_centavos: cartao });

test('domingo soma segunda até hoje, inclui zero e segunda abre outra semana', () => {
  const dados = [venda('2026-10-18', 10000), venda('2026-10-19'), venda('2026-10-23', 1010, 2020, 3030), venda('2026-10-25', 500), venda('2026-10-26', 700), venda('2026-10-30', 900), venda('invalida', 999999)];
  const r = resumoSemana(dados, '2026-10-25');
  assert.equal(r.inicio, '2026-10-19'); assert.equal(r.fim, '2026-10-25');
  assert.equal(r.quantidade, 3); assert.equal(r.total, 6560);
  assert.deepEqual(r.pagamentos, [1510, 2020, 3030]);
  const s = resumoSemana(dados, '2026-10-26');
  assert.equal(s.total, 700); assert.equal(s.quantidade, 1); assert.equal(s.fim, '2026-11-01');
});
test('histórico cruza ano, respeita recorte, não inventa semanas e preserva zeros', () => {
  const dados = [venda('2026-12-31', 100), venda('2027-01-03', 200), venda('2027-01-11')];
  const grupos = agruparSemanas(dados);
  assert.equal(grupos.length, 2); assert.equal(grupos[0].quantidade, 1); assert.equal(grupos[0].total, 0);
  assert.equal(grupos[1].inicio, '2026-12-28'); assert.equal(grupos[1].fim, '2027-01-03'); assert.equal(grupos[1].media, 150);
  assert.equal(agruparSemanas(dados.filter(r => r.data >= '2027-01-01'))[1].total, 200);
  assert.deepEqual(agruparSemanas([]), []);
  assert.equal(resumoSemana([], '2026-10-26').quantidade, 0);
  assert.throws(() => limitesSemana('2026-02-30'));
});
test('preferência inicial respeita histórico de fechamento e início do ano', () => {
  definirFechamentos({ versao: 1, historico: [{ vigencia: '2027-01-01', dia: 15 }] });
  try {
    assert.deepEqual(selecaoInicial('Fechamento atual', '2026-01-09'), { tipo: 'Fechamento', ano: 2025, mes: 12 });
    assert.deepEqual(selecaoInicial('Fechamento atual', '2027-01-15'), { tipo: 'Fechamento', ano: 2026, mes: 12 });
    assert.deepEqual(selecaoInicial('Fechamento atual', '2027-01-16'), { tipo: 'Fechamento', ano: 2027, mes: 1 });
    assert.equal(selecaoInicial('Mês atual', '2026-10-26').tipo, 'Mês');
    assert.equal(selecaoInicial('Ano atual', '2026-10-26').tipo, 'Ano');
    assert.equal(selecaoInicial('Todas as vendas', '2026-10-26').tipo, 'Todas');
  } finally { definirFechamentos({ versao: 0, historico: [] }); }
});
test('salva somente a preferência, trata armazenamento bloqueado e valor inválido', () => {
  const mapa = new Map(); const storage = { getItem: k => mapa.get(k), setItem: (k, v) => mapa.set(k, v) };
  assert.equal(carregarPeriodoInicial(storage), 'Fechamento atual'); assert.equal(mapa.size, 0);
  for (const p of PERIODOS_INICIAIS) { salvarPeriodoInicial(storage, p); assert.equal(carregarPeriodoInicial(storage), p); }
  assert.equal(mapa.size, 1);
  assert.throws(() => salvarPeriodoInicial(storage, 'inválido'));
  assert.equal(carregarPeriodoInicial({ getItem() { throw Error('bloqueado'); } }), 'Fechamento atual');
  assert.throws(() => salvarPeriodoInicial({ setItem() { throw Error('bloqueado'); } }, 'Mês atual'));
});
