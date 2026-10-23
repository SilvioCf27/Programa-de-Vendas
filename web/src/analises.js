import { diaNoMes } from './fechamento.js';
import { dataValida, periodo, resumo } from './regras.js';

export const formas = ['Dinheiro', 'Pix', 'Cartão'];
export const dias = [
  'Segunda-feira',
  'Terça-feira',
  'Quarta-feira',
  'Quinta-feira',
  'Sexta-feira',
  'Sábado',
  'Domingo',
];
export function limitesAnalise(tipo, referencia, fim = '') {
  if (tipo === 'Todas') return { inicio: null, fim: null };
  if (!dataValida(referencia)) throw Error('Informe uma data válida.');
  if (tipo === 'Data' || tipo === 'Intervalo') {
    const ultima = tipo === 'Data' ? referencia : fim;
    if (!dataValida(ultima) || referencia > ultima)
      throw Error('Confira as datas: a inicial deve vir antes da final.');
    return { inicio: referencia, fim: ultima };
  }
  const [ano, mes] = referencia.split('-').map(Number);
  return periodo(tipo, ano, mes);
}
export function anterior(tipo, selecao) {
  if (!selecao.inicio || !['Mês', 'Ano', 'Fechamento'].includes(tipo))
    return null;
  const inicio = new Date(selecao.inicio + 'T12:00:00Z');
  if (tipo === 'Fechamento') inicio.setUTCDate(inicio.getUTCDate() - 1);
  const [ano, mes] = inicio.toISOString().slice(0, 10).split('-').map(Number);
  return tipo === 'Ano'
    ? periodo('Ano', ano - 1, 1)
    : periodo(tipo, mes === 1 ? ano - 1 : ano, mes === 1 ? 12 : mes - 1);
}
export function selecionar(vendas, { inicio, fim }) {
  return vendas.filter((r) => !inicio || (r.data >= inicio && r.data <= fim));
}
export function indicadores(vendas) {
  const pagamentos = ['dinheiro', 'pix', 'cartao'].map((forma) =>
    vendas.reduce((s, r) => s + Number(r[forma + '_centavos']), 0)
  );
  const porDia = dias.map((nome, indice) => {
    const grupo = vendas.filter(
      (r) => (new Date(r.data + 'T12:00:00Z').getUTCDay() + 6) % 7 === indice
    );
    return { nome, ...resumo(grupo) };
  });
  return { ...resumo(vendas), pagamentos, porDia };
}
export function comparar(a, b) {
  a = indicadores(a);
  b = indicadores(b);
  const motivo =
    !a.quantidade || !b.quantidade
      ? 'Sem registros em um dos períodos: não há base para calcular a variação.'
      : a.total === 0
        ? 'O total de A é zero: a variação percentual não pode ser calculada.'
        : '';
  return {
    a,
    b,
    diferenca: b.total - a.total,
    variacao: motivo ? null : ((b.total - a.total) * 100) / a.total,
    motivo,
  };
}

export function evolucao(vendas, tipo = 'Mês') {
  const grupos = new Map();
  for (const r of vendas) {
    let [ano, mes, dia] = r.data.split('-').map(Number);
    if (tipo === 'Fechamento' && dia <= diaNoMes(ano, mes)) {
      mes--;
      if (!mes) {
        mes = 12;
        ano--;
      }
    }
    const chave = `${ano}-${String(mes).padStart(2, '0')}`;
    if (!grupos.has(chave)) grupos.set(chave, []);
    grupos.get(chave).push(r);
  }
  if (!grupos.size) return [];
  const chaves = [...grupos.keys()].sort();
  let [ano, mes] = chaves.at(-1).split('-').map(Number);
  const resultado = [];
  for (let i = 0; i < 12; i++) {
    const chave = `${ano}-${String(mes).padStart(2, '0')}`;
    if (chave < chaves[0]) break;
    resultado.unshift({
      chave,
      rotulo: `${String(mes).padStart(2, '0')}/${ano}`,
      ...resumo(grupos.get(chave) || []),
    });
    mes--;
    if (!mes) {
      mes = 12;
      ano--;
    }
  }
  return resultado;
}
