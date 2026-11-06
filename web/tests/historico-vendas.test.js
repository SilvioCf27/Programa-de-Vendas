import test from 'node:test';
import assert from 'node:assert/strict';
import { diaDaSemana, filtrarDias, paginaHistorico } from '../src/historico-vendas.js';
import { montarExportacao, gerarCsv } from '../src/exportacao.js';
const venda = (data, valor = 0) => ({ id: data, data, dinheiro_centavos: valor, pix_centavos: 0, cartao_centavos: 0 });
test('dias têm base segunda-feira e preservam domingos e registros zerados', () => {
  const registros = [venda('2026-10-23', 100), venda('2026-10-25'), venda('2026-10-26', 900)];
  assert.equal(diaDaSemana('2026-10-26'), 0);
  assert.equal(diaDaSemana('2026-10-25'), 6);
  assert.equal(filtrarDias(registros).length, 3);
  assert.deepEqual(filtrarDias(registros, [4, 6]).map(r => r.data), ['2026-10-23', '2026-10-25']);
  assert.equal(filtrarDias(registros, [1]).length, 0);
});
test('busca por data brasileira, ISO, dia sem acento e valor total ou de pagamento', () => {
  const dados = [{ ...venda('2026-10-23', 10025), pix_centavos: 2050 }, venda('2026-10-25')];
  for (const termo of ['23/10/2026', '2026-10-23', 'SEXTA', '100,25', '100.25', '120,75', '20,50'])
    assert.equal(paginaHistorico(dados, termo).registros[0].data, '2026-10-23');
  assert.equal(paginaHistorico(dados, 'domingo').quantidade, 1);
  assert.equal(paginaHistorico(dados, 'nenhum').quantidade, 0);
  assert.equal(paginaHistorico(dados, '  ').quantidade, 2);
});
test('paginação ordena sem modificar origem e limita página após exclusão', () => {
  const dados = Array.from({ length: 25 }, (_, i) => venda(`2026-10-${String(i + 1).padStart(2, '0')}`));
  const p = paginaHistorico(dados, '', 2);
  assert.equal(p.paginas, 3); assert.equal(p.registros.length, 12);
  assert.equal(p.inicio, 13); assert.equal(p.fim, 24);
  assert.equal(p.registros[0].data, '2026-10-13');
  assert.equal(dados[0].data, '2026-10-01');
  const ultima = paginaHistorico(dados.slice(0, 12), '', 3);
  assert.equal(ultima.pagina, 1);
  const vazio = paginaHistorico([], '', 7);
  assert.equal(vazio.pagina, 1); assert.equal(vazio.inicio, 0); assert.equal(vazio.fim, 0);
});
test('exportação identifica dias aplicados e inclui todos os resultados sem a busca', () => {
  const dados = filtrarDias([venda('2026-10-23', 100), venda('2026-10-25'), venda('2026-10-26', 999)], [4, 6]);
  const csv = gerarCsv(montarExportacao(dados, { inicio: null, dias: [4, 6] }));
  assert.match(csv, /Sexta-feira, Domingo/);
  assert.match(csv, /25\/10\/2026/); assert.doesNotMatch(csv, /26\/10\/2026/);
  assert.match(csv, /"Registros \/ dias de feira";"2"/);
});
