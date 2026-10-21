import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  centavos,
  dataValida,
  periodo,
  resumo,
  mesFechamento,
} from '../src/regras.js';
import { validarConfig } from '../src/config.js';

test('dinheiro preserva centavos e recusa formatos ambíguos', () => {
  for (const [entrada, esperado] of [
    ['1.234,56', 123456],
    ['0,01', 1],
    ['', 0],
    ['0', 0],
    ['125.50', 12550],
  ])
    assert.equal(centavos(entrada), esperado);
  for (const entrada of [
    '-1',
    'NaN',
    'Infinity',
    '1e3',
    '1,234',
    '1.234',
    '9999999999999999999',
  ])
    assert.throws(() => centavos(entrada));
});
test('fechamentos respeitam o mês inicial, a virada do ano e os limites de 9 e 10', () => {
  assert.deepEqual(periodo('Fechamento', 2026, 10), {
    inicio: '2026-10-10',
    fim: '2026-11-09',
  });
  assert.deepEqual(periodo('Fechamento', 2026, 12), {
    inicio: '2026-12-10',
    fim: '2027-01-09',
  });
  assert.deepEqual(mesFechamento('2026-01-09'), { ano: 2025, mes: 12 });
  assert.deepEqual(mesFechamento('2026-01-10'), { ano: 2026, mes: 1 });
  assert.deepEqual(periodo('Mês', 2028, 2), {
    inicio: '2028-02-01',
    fim: '2028-02-29',
  });
  assert.deepEqual(periodo('Ano', 2026, 1), {
    inicio: '2026-01-01',
    fim: '2026-12-31',
  });
  assert.deepEqual(periodo('Todas'), { inicio: null, fim: null });
});
test('datas inválidas não são convertidas silenciosamente', () => {
  assert.equal(dataValida('2026-02-30'), false);
  assert.equal(dataValida('2028-02-29'), true);
  assert.equal(dataValida('0000-01-01'), false);
  assert.equal(dataValida('2026-1-1'), false);
});
test('dias zerados contam na média e período vazio não divide por zero', () => {
  assert.deepEqual(
    resumo([
      { dinheiro_centavos: 10000, pix_centavos: 5000, cartao_centavos: 0 },
      { dinheiro_centavos: 0, pix_centavos: 0, cartao_centavos: 0 },
    ]),
    { total: 15000, quantidade: 2, media: 7500 }
  );
  assert.deepEqual(resumo([]), { total: 0, quantidade: 0, media: 0 });
});
test('configuração aceita somente chave pública e exige HTTPS', () => {
  const jwt = (role) =>
    `x.${Buffer.from(JSON.stringify({ role })).toString('base64url')}.x`;
  assert.equal(validarConfig('', ''), false);
  assert.equal(
    validarConfig('https://exemplo.supabase.co', 'sb_publishable_exemplo'),
    true
  );
  assert.equal(validarConfig('https://exemplo.supabase.co', jwt('anon')), true);
  for (const chave of [
    jwt('service_role'),
    'sb_secret_exemplo',
    'qualquer coisa',
  ])
    assert.throws(() => validarConfig('https://exemplo.supabase.co', chave));
  assert.throws(() => validarConfig('http://exemplo.supabase.co', jwt('anon')));
});
