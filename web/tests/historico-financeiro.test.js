import test from 'node:test';
import assert from 'node:assert/strict';
import { historicoFinanceiro, dataDaCompra } from '../src/historico-financeiro.js';
import { resumoFinanceiro } from '../src/financeiro.js';
const compra = (id, data, data_compra, meio = 'Cartão de crédito', valor_centavos = 12345) => ({ id, tipo: 'despesa', data, data_compra, meio, valor_centavos, descricao: 'Mercado terça', categoria: 'Casa', parcela: 1, parcelas: 3 });
test('cronologia usa a compra, nunca cadastro ou fatura; legado desconhecido não ganha data', () => {
  const antigas = compra('antiga', '2026-12-09', '2026-09-01');
  antigas.created_at = '2099-12-31';
  const novas = compra('nova', '2026-11-09', '2026-10-20');
  const legado = compra('legado', '2027-01-09', null);
  const dinheiro = compra('dinheiro', '2026-10-21', null, 'Dinheiro');
  assert.deepEqual(historicoFinanceiro([antigas, legado, novas, dinheiro]).map(r => r.id), ['dinheiro', 'nova', 'antiga', 'legado']);
  assert.equal(dataDaCompra(legado), null);
  assert.equal(dataDaCompra(dinheiro), '2026-10-21');
  assert.equal(antigas.data, '2026-12-09');
});
test('busca financeira aceita compra, fatura, dia sem acento, descrição, meio e valor', () => {
  const registros = [compra('x', '2026-11-09', '2026-10-20')];
  for (const busca of ['20/10/2026', '09/11/2026', '2026-10-20', 'TERCA', 'mercado', 'credito', '123,45', '123.45', '1/3'])
    assert.equal(historicoFinanceiro(registros, busca).length, 1, busca);
  assert.equal(historicoFinanceiro(registros, 'ausente').length, 0);
});
test('meio limita despesas, saldo e semanas; vendas e taxas permanecem completas', () => {
  const dados = { vendas: [{ data: '2026-11-01', dinheiro_centavos: 50000, pix_centavos: 0, cartao_centavos: 0 }], financeiro_lancamentos: [compra('c', '2026-11-09', '2026-10-20', 'Cartão de crédito', 30000), compra('d', '2026-11-05', null, 'Dinheiro', 40000), { ...compra('t', '2026-11-01', null), tipo: 'taxa', valor_centavos: 1000 }], financeiro_taxas_anuais: [] };
  const periodo = { inicio: '2026-11-01', fim: '2026-11-30' };
  const completo = resumoFinanceiro(dados, periodo);
  const r = resumoFinanceiro(dados, { ...periodo, meio: 'Cartão de crédito' });
  assert.equal(completo.despesas, 70000); assert.equal(r.despesas, 30000);
  assert.equal(r.bruto, 50000); assert.equal(r.taxas, 1000); assert.equal(r.saldo, 19000);
  assert.equal(r.semanas.reduce((s, [, v]) => s + v, 0), 30000);
  assert.equal(resumoFinanceiro(dados, { ...periodo, meio: 'Dinheiro' }).despesas, 40000);
  assert.throws(() => resumoFinanceiro(dados, { ...periodo, meio: 'invalido' }));
});
