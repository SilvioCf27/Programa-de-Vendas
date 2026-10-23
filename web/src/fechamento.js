import { dataValida } from './regras.js';
// Nenhuma alteração financeira: estas regras apenas definem os recortes de consulta.
let estado = { versao: 0, historico: [] };
export function validarFechamentos(config) {
  if (!config || !Number.isInteger(config.versao) || config.versao < 0 || !Array.isArray(config.historico))
    throw Error('Configuração de fechamento inválida.');
  let anterior = '';
  for (const regra of config.historico) {
    if (!dataValida(regra.vigencia) || !regra.vigencia.endsWith('-01') || regra.vigencia <= anterior || !Number.isInteger(regra.dia) || regra.dia < 1 || regra.dia > 31)
      throw Error('Histórico de fechamentos inválido.');
    anterior = regra.vigencia;
  }
  return structuredClone({ versao: config.versao, historico: config.historico });
}
export const estadoFechamentos = () => validarFechamentos(estado);
export function definirFechamentos(config) { estado = validarFechamentos(config); }
export function diaNoMes(ano, mes, historico = estado.historico) {
  const referencia = `${ano}-${String(mes).padStart(2, '0')}-01`;
  let dia = 9;
  for (const regra of historico) if (regra.vigencia <= referencia) dia = regra.dia;
  return Math.min(dia, new Date(Date.UTC(ano, mes, 0)).getUTCDate());
}
export function periodoFechamento(ano, mes, historico = estado.historico) {
  const inicio = new Date(Date.UTC(ano, mes - 1, diaNoMes(ano, mes, historico) + 1));
  const proximo = new Date(Date.UTC(ano, mes, 1));
  const fim = new Date(Date.UTC(proximo.getUTCFullYear(), proximo.getUTCMonth(), diaNoMes(proximo.getUTCFullYear(), proximo.getUTCMonth() + 1, historico)));
  return { inicio: inicio.toISOString().slice(0, 10), fim: fim.toISOString().slice(0, 10) };
}

export function proporFechamento(config, vigencia, dia, hoje = new Date()) {
  config = validarFechamentos(config);
  const primeiro = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}-01`;
  if (!dataValida(vigencia) || !vigencia.endsWith('-01') || vigencia <= primeiro)
    throw Error('Escolha uma vigência a partir do próximo mês. Fechamentos antigos não podem ser alterados.');
  if (!Number.isInteger(dia) || dia < 1 || dia > 31) throw Error('Escolha um dia entre 1 e 31.');
  if (config.historico.at(-1)?.vigencia > vigencia) throw Error('A vigência deve ser igual ou posterior à regra mais recente.');
  return validarFechamentos({ versao: config.versao + 1,
    historico: [...config.historico.filter(r => r.vigencia !== vigencia), { vigencia, dia }] });
}
