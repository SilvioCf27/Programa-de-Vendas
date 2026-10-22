import { resumo } from './regras.js';
import { dias } from './analises.js';
const br = (d) => d.split('-').reverse().join('/');
const numero = (centavos) => ({
  value: Number(centavos) / 100,
  type: Number,
  format: '#,##0.00',
});
export function montarExportacao(vendas, periodo) {
  const copia = structuredClone(vendas);
  const r = resumo(copia);
  const totais = ['dinheiro', 'pix', 'cartao'].map((p) =>
    copia.reduce((s, v) => s + Number(v[p + '_centavos']), 0)
  );
  const cabecalho = [
    'ID',
    'Data',
    'Dia da semana',
    'Dinheiro',
    'Pix',
    'Cartão',
    'Total',
  ];
  const linhas = copia.map((v) => {
    const pagamentos = ['dinheiro', 'pix', 'cartao'].map((p) =>
      Number(v[p + '_centavos'])
    );
    return [
      String(v.id),
      {
        value: new Date(v.data + 'T00:00:00Z'),
        type: Date,
        format: 'dd/mm/yyyy',
      },
      dias[(new Date(v.data + 'T12:00:00Z').getUTCDay() + 6) % 7],
      ...pagamentos.map(numero),
      numero(pagamentos.reduce((a, b) => a + b, 0)),
    ];
  });
  const resumoLinhas = [
    ['Indicador', 'Valor'],
    [
      'Filtro aplicado',
      periodo.inicio
        ? `${br(periodo.inicio)} a ${br(periodo.fim)}`
        : 'Todas as vendas',
    ],
    ['Registros / dias de feira', r.quantidade],
    ['Dinheiro', numero(totais[0])],
    ['Pix', numero(totais[1])],
    ['Cartão', numero(totais[2])],
    ['Total geral', numero(r.total)],
    ['Média por dia de feira', numero(r.media)],
    ['Contagem', 'Inclui registros com pagamentos zerados'],
    ['Valores', 'Brutos, antes de taxas e despesas'],
  ];
  return { vendas: [cabecalho, ...linhas], resumo: resumoLinhas };
}
function celulaCsv(celula) {
  let valor = celula?.value ?? celula;
  if (valor instanceof Date) valor = br(valor.toISOString().slice(0, 10));
  else if (typeof valor === 'number' && celula?.type === Number)
    valor = valor.toFixed(2).replace('.', ',');
  else if (typeof valor === 'string' && /^[\s]*[=+@-]/.test(valor))
    valor = "'" + valor;
  return '"' + String(valor ?? '').replaceAll('"', '""') + '"';
}
export function gerarCsv(relatorio) {
  return (
    '\ufeff' +
    [...relatorio.vendas, [], ...relatorio.resumo]
      .map((linha) => linha.map(celulaCsv).join(';'))
      .join('\r\n')
  );
}
export async function gerarExcel(relatorio) {
  const { default: escrever } = await import('write-excel-file/browser');
  return escrever([
    {
      sheet: 'Vendas',
      data: relatorio.vendas,
      columns: [16, 16, 23, 18, 18, 18, 18].map((width) => ({ width })),
    },
    {
      sheet: 'Resumo',
      data: relatorio.resumo,
      columns: [{ width: 38 }, { width: 75 }],
    },
  ]).toBlob();
}
export function baixar(blob, nome) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = nome;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
