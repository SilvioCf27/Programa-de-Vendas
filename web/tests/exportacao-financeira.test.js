import test from 'node:test';
import assert from 'node:assert/strict';
import { montarExportacaoFinanceira, gerarJsonFinanceiro, gerarCsvFinanceiro } from '../src/exportacao-financeira.js';
const quando = '2026-11-07T12:00:00.000Z';
const selecao = { tipo: 'Mês', referencia: '2026-11-01', inicio: '2026-11-01', fim: '2026-11-30', meio: 'Cartão de crédito', token: 'SEGREDO' };
const parcela = (i, data) => ({ id: `p${i}`, tipo: 'despesa', data, data_compra: '2026-09-09', descricao: 'Compra em três vezes', valor_centavos: i === 1 ? 1001 : 1000, meio: 'Cartão de crédito', categoria: 'Casa', grupo: 'grupo-original', parcela: i, parcelas: 3, versao: 7, user_id: 'SEGREDO', access_token: 'SEGREDO' });
const dados = () => ({ senha: 'SEGREDO', vendas: [{ id: 'SEGREDO' }], financeiro_lancamentos: [parcela(1, '2026-10-09'), parcela(2, '2026-11-09'), parcela(3, '2026-12-09'), { ...parcela(1, '2026-11-02'), id: 'dinheiro', meio: 'Dinheiro', grupo: null, data_compra: null }, { ...parcela(1, '2026-11-03'), id: 'taxa', tipo: 'taxa', meio: 'Outro' }], financeiro_taxas_anuais: [{ id: 'a', ano: 2026, inicio: '2026-01-01', fim: '2026-12-31', valor_centavos: 34563, natureza: 'Confirmada', observacao: 'Histórico', versao: 2, user_id: 'SEGREDO' }] });
test('JSON completo conserva centavos, datas, IDs e grupos sem credenciais ou dados de login', () => {
  const origem = dados();
  const r = montarExportacaoFinanceira(origem, selecao, 'historico_completo', quando, quando);
  assert.equal(r.consulta, null); assert.equal(r.totais_registros.lancamentos, 5);
  assert.equal(r.financeiro_lancamentos.filter(l => l.grupo === 'grupo-original' && l.tipo === 'despesa' && l.meio === 'Cartão de crédito').reduce((s, l) => s + l.valor_centavos, 0), 3001);
  const json = gerarJsonFinanceiro(r);
  assert.doesNotMatch(json, /SEGREDO|access_token|user_id|senha/);
  assert.equal(JSON.parse(json).financeiro_taxas_anuais[0].valor_centavos, 34563);
  origem.financeiro_lancamentos[0].valor_centavos = 99999;
  assert.equal(r.financeiro_lancamentos.find(l => l.id === 'p1').valor_centavos, 1001);
  assert.equal(r.consultado_em, quando); assert.equal(r.gerado_em, quando);
});
test('consulta aplicada recorta faturas e meio, preserva taxas e identifica parcelas parciais', () => {
  const r = montarExportacaoFinanceira(dados(), selecao, 'consulta_aplicada', quando, quando);
  assert.deepEqual(r.financeiro_lancamentos.map(l => l.id).sort(), ['p2', 'taxa']);
  assert.equal(r.consulta.meio, 'Cartão de crédito'); assert.equal(r.consulta.token, undefined);
  assert.match(r.criterios.parcelas, /incompleto/);
  assert.equal(r.financeiro_taxas_anuais.length, 1);
  assert.equal(r.totais_registros.despesas_centavos, 1000);
  assert.equal(r.totais_registros.ajustes_anuais_centavos, 34563);
});
test('CSV mantém valores monetários e protege texto com fórmulas, aspas e quebras', () => {
  const origem = dados(); origem.financeiro_lancamentos[0].descricao = '=HYPERLINK("teste");\nOutro';
  origem.financeiro_taxas_anuais[0].observacao = '\t+COMANDO';
  const csv = gerarCsvFinanceiro(montarExportacaoFinanceira(origem, selecao, 'historico_completo', quando, quando));
  assert.ok(csv.startsWith('\ufeff')); assert.match(csv, /"1001";"10,01"/);
  assert.match(csv, /'=HYPERLINK\(""teste""\);\nOutro/); assert.match(csv, /'\t\+COMANDO/);
  assert.match(csv, /"ajuste_anual"/); assert.doesNotMatch(csv, /SEGREDO/);
});
test('sem snapshot ou com escopo inválido não exporta; seleção vazia tem estrutura explícita', () => {
  assert.throws(() => montarExportacaoFinanceira(null, selecao, 'historico_completo', quando));
  assert.throws(() => montarExportacaoFinanceira(dados(), selecao, 'invalido', quando));
  const r = montarExportacaoFinanceira({ financeiro_lancamentos: [], financeiro_taxas_anuais: [] }, selecao, 'consulta_aplicada', quando, quando);
  assert.equal(r.totais_registros.lancamentos, 0);
  assert.equal(r.financeiro_taxas_anuais.length, 0);
  assert.equal(gerarCsvFinanceiro(r).split('\r\n').length, 1);
});
