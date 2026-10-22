import test from 'node:test';
import assert from 'node:assert/strict';
import { unzipSync, strFromU8 } from 'fflate';
import { montarExportacao, gerarCsv, gerarExcel } from '../src/exportacao.js';
const vendas = [
  {
    id: '=1+1',
    data: '2030-10-11',
    dinheiro_centavos: 10025,
    pix_centavos: 2050,
    cartao_centavos: 3000,
  },
  {
    id: 'zero',
    data: '2030-10-18',
    dinheiro_centavos: 0,
    pix_centavos: 0,
    cartao_centavos: 0,
  },
];
const periodo = { inicio: '2030-10-01', fim: '2030-10-31' };
test('exportação congela a seleção aplicada e mantém dias zerados e centavos', () => {
  const copia = structuredClone(vendas);
  const r = montarExportacao(copia, periodo);
  copia[0].dinheiro_centavos = 999999;
  const csv = gerarCsv(r);
  assert.ok(csv.startsWith('\ufeff'));
  assert.match(csv, /11\/10\/2030/);
  assert.match(csv, /Sexta-feira/);
  assert.match(csv, /"100,25";"20,50";"30,00";"150,75"/);
  assert.match(csv, /"'=1\+1"/);
  assert.match(csv, /"Registros \/ dias de feira";"2"/);
  assert.match(csv, /01\/10\/2030 a 31\/10\/2030/);
});
test('Excel possui duas abas, células numéricas e datas; texto não vira fórmula', async () => {
  const blob = await gerarExcel(montarExportacao(vendas, periodo));
  const arquivos = unzipSync(new Uint8Array(await blob.arrayBuffer()));
  const livro = strFromU8(arquivos['xl/workbook.xml']);
  assert.match(livro, /name="Vendas"/);
  assert.match(livro, /name="Resumo"/);
  const sheet = strFromU8(arquivos['xl/worksheets/sheet1.xml']);
  assert.match(sheet, /100\.25/);
  assert.match(sheet, /150\.75/);
  assert.ok(!sheet.includes('<f>'));
  assert.match(strFromU8(arquivos['xl/styles.xml']), /dd\/mm\/yyyy/);
});
