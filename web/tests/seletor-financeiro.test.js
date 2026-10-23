import { test } from 'node:test';
import assert from 'node:assert/strict';
import { semanasDoMes } from '../src/seletor-financeiro.js';

test('semanas do mês incluem semanas completas que atravessam mês e ano', () => {
  const semanas = semanasDoMes(2026, 1);
  assert.deepEqual(semanas[0], { inicio: '2025-12-29', fim: '2026-01-04' });
  assert.deepEqual(semanas.at(-1), { inicio: '2026-01-26', fim: '2026-02-01' });
  assert.equal(semanas.length, 5);
});
test('semana iniciada no primeiro dia não inclui semana anterior', () => {
  assert.deepEqual(semanasDoMes(2026, 6)[0], { inicio: '2026-06-01', fim: '2026-06-07' });
  assert.throws(() => semanasDoMes(2026, 13));
});
