import test from 'node:test';
import assert from 'node:assert/strict';
import {
  limitesAnalise,
  anterior,
  selecionar,
  indicadores,
  comparar,
} from '../src/analises.js';
const venda = (
  data,
  dinheiro_centavos = 0,
  pix_centavos = 0,
  cartao_centavos = 0
) => ({ data, dinheiro_centavos, pix_centavos, cartao_centavos });

test('fechamento seleciona o mês inicial, inclui dia 09 seguinte e cruza o ano', () => {
  const p = limitesAnalise('Fechamento', '2026-12-01');
  assert.deepEqual(p, { inicio: '2026-12-10', fim: '2027-01-09' });
  assert.deepEqual(
    selecionar(
      ['2026-12-09', '2026-12-10', '2027-01-09', '2027-01-10'].map((d) =>
        venda(d)
      ),
      p
    ).map((r) => r.data),
    ['2026-12-10', '2027-01-09']
  );
  assert.deepEqual(anterior('Fechamento', p), {
    inicio: '2026-11-10',
    fim: '2026-12-09',
  });
  assert.deepEqual(anterior('Mês', limitesAnalise('Mês', '2024-03-10')), {
    inicio: '2024-02-01',
    fim: '2024-02-29',
  });
});
test('datas, intervalos e consultas inválidas são validados', () => {
  assert.deepEqual(limitesAnalise('Data', '2026-10-16'), {
    inicio: '2026-10-16',
    fim: '2026-10-16',
  });
  assert.throws(() => limitesAnalise('Intervalo', '2026-10-16', '2026-10-15'));
  assert.throws(() => limitesAnalise('Data', '2026-02-29'));
  assert.deepEqual(limitesAnalise('Todas', ''), { inicio: null, fim: null });
});
test('indicadores incluem dias zerados e agrupam semana sem deslocamento de fuso', () => {
  const r = indicadores([
    venda('2026-10-16', 10000, 2000, 3000),
    venda('2026-10-23'),
  ]);
  assert.equal(r.total, 15000);
  assert.equal(r.media, 7500);
  assert.equal(r.quantidade, 2);
  assert.deepEqual(r.pagamentos, [10000, 2000, 3000]);
  assert.equal(r.porDia[4].quantidade, 2);
  assert.equal(r.porDia[4].media, 7500);
  assert.equal(r.porDia[0].total, 0);
});
test('comparação usa A como base e distingue ausência de registros de total zero', () => {
  const c = comparar([venda('2026-09-11', 200)], [venda('2026-10-16', 300)]);
  assert.equal(c.diferenca, 100);
  assert.equal(c.variacao, 50);
  assert.equal(
    comparar([venda('2026-09-11')], [venda('2026-10-16', 300)]).variacao,
    null
  );
  assert.match(comparar([], [venda('2026-10-16')]).motivo, /Sem registros/);
});

test('evolução agrupa fechamento por mês inicial e distingue lacunas de registros zerados', async () => {
  const { evolucao } = await import('../src/analises.js');
  const grupos = evolucao(
    [venda('2030-12-10', 1000), venda('2031-01-09', 2000), venda('2031-03-10')],
    'Fechamento'
  );
  assert.deepEqual(
    grupos.map((g) => g.rotulo),
    ['12/2030', '01/2031', '02/2031', '03/2031']
  );
  assert.equal(grupos[0].total, 3000);
  assert.equal(grupos[1].quantidade, 0);
  assert.equal(grupos[3].quantidade, 1);
  assert.equal(evolucao([]).length, 0);
});
