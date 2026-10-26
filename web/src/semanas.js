import { dataValida, hoje, mesFechamento, resumo } from './regras.js';

const iso = (d) => d.toISOString().slice(0, 10);
export const PERIODOS_INICIAIS = ['Fechamento atual', 'Mês atual', 'Ano atual', 'Todas as vendas'];
export function limitesSemana(data = hoje()) {
  if (!dataValida(data)) throw Error('Informe uma data válida.');
  const inicio = new Date(data + 'T12:00:00Z');
  inicio.setUTCDate(inicio.getUTCDate() - (inicio.getUTCDay() + 6) % 7);
  const fim = new Date(inicio); fim.setUTCDate(fim.getUTCDate() + 6);
  return { inicio: iso(inicio), fim: iso(fim), ate: data };
}
export function resumoSemana(vendas, data = hoje()) {
  const limites = limitesSemana(data);
  const registros = vendas.filter(r => dataValida(r.data) && r.data >= limites.inicio && r.data <= limites.ate);
  return { ...limites, ...resumo(registros), pagamentos: ['dinheiro', 'pix', 'cartao'].map(forma =>
    registros.reduce((s, r) => s + Number(r[forma + '_centavos']), 0)) };
}
export function agruparSemanas(vendas) {
  const grupos = new Map();
  for (const r of vendas) {
    if (!dataValida(r.data)) continue;
    const { inicio, fim } = limitesSemana(r.data);
    if (!grupos.has(inicio)) grupos.set(inicio, { inicio, fim, registros: [] });
    grupos.get(inicio).registros.push(r);
  }
  return [...grupos.values()].sort((a, b) => b.inicio.localeCompare(a.inicio))
    .map(({ inicio, fim, registros }) => ({ inicio, fim, ...resumo(registros) }));
}
export function selecaoInicial(preferencia, data = hoje()) {
  if (!PERIODOS_INICIAIS.includes(preferencia)) preferencia = 'Fechamento atual';
  const [ano, mes] = data.split('-').map(Number);
  if (preferencia === 'Fechamento atual') return { tipo: 'Fechamento', ...mesFechamento(data) };
  return { tipo: { 'Mês atual': 'Mês', 'Ano atual': 'Ano', 'Todas as vendas': 'Todas' }[preferencia], ano, mes };
}
export function carregarPeriodoInicial(armazenamento) {
  try {
    const valor = armazenamento.getItem('feira-periodo-inicial');
    return PERIODOS_INICIAIS.includes(valor) ? valor : 'Fechamento atual';
  } catch { return 'Fechamento atual'; }
}
export function salvarPeriodoInicial(armazenamento, valor) {
  if (!PERIODOS_INICIAIS.includes(valor)) throw Error('Período inicial inválido.');
  armazenamento.setItem('feira-periodo-inicial', valor);
}
