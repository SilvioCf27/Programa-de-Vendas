import { dataValida } from './regras.js';
import { MEIOS, CATEGORIAS } from './financeiro.js';
export const CAMPOS_CORRECAO = ['tipo', 'data', 'data_compra', 'descricao', 'valor_centavos', 'meio', 'categoria', 'grupo', 'parcela', 'parcelas'];
const falhar = () => { throw Error('Arquivo de correções inválido ou diferente dos registros atuais. Gere nova conferência antes de aplicar.'); };
const uuid = s => typeof s === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);
const inteiro = n => Number.isSafeInteger(n) && n > 0;
function campos(r) {
  if (!r || Object.keys(r).some(k => !CAMPOS_CORRECAO.includes(k)) || CAMPOS_CORRECAO.some(k => !Object.hasOwn(r, k))) falhar();
  if (r.tipo !== 'despesa' || !dataValida(r.data) || (r.data_compra !== null && !dataValida(r.data_compra)) ||
      typeof r.descricao !== 'string' || !r.descricao.trim() || r.descricao.length > 200 ||
      !inteiro(r.valor_centavos) || r.valor_centavos > 99999999999 || !MEIOS.includes(r.meio) || !CATEGORIAS.includes(r.categoria) ||
      !inteiro(r.parcela) || !inteiro(r.parcelas) || r.parcela > r.parcelas || r.parcelas > 120 ||
      (r.parcelas === 1 ? r.grupo !== null : (typeof r.grupo !== 'string' || !r.grupo.trim() || r.grupo.length > 100 || r.meio !== 'Cartão de crédito')) ||
      (r.data_compra !== null && r.meio !== 'Cartão de crédito')) falhar();
  return Object.fromEntries(CAMPOS_CORRECAO.map(k => [k, r[k]]));
}
export function conferirCorrecoes(plano, registros) {
  if (!plano || plano.formato !== 'gestao-da-feira-correcoes' || plano.versao_formato !== 1 ||
      !Array.isArray(plano.verificacoes) || !Array.isArray(plano.alteracoes) || !plano.alteracoes.length || plano.alteracoes.length > 500 ||
      plano.verificacoes.length !== plano.alteracoes.length) falhar();
  const atuais = new Map(registros.map(r => [r.id, r]));
  const guardas = new Map();
  for (const v of plano.verificacoes) {
    if (!uuid(v.id) || !inteiro(v.versao) || guardas.has(v.id)) falhar();
    const antes = campos(v.campos), atual = atuais.get(v.id);
    if (!atual || atual.versao !== v.versao || CAMPOS_CORRECAO.some(k => (atual[k] ?? null) !== antes[k])) falhar();
    guardas.set(v.id, antes);
  }
  // Todos os membros atuais dos grupos envolvidos devem estar no lote, até os inalterados.
  const grupos = new Set([...guardas.values()].map(r => r.grupo).filter(Boolean));
  if (registros.some(r => grupos.has(r.grupo) && !guardas.has(r.id))) falhar();
  const ids = new Set();
  const operacoes = plano.alteracoes.map(op => {
    const antes = guardas.get(op.id);
    if (!antes || ids.has(op.id) || op.tabela !== 'financeiro_lancamentos' ||
        !['excluir', 'editar'].includes(op.acao) || op.versao !== atuais.get(op.id).versao) falhar();
    ids.add(op.id);
    const dados = op.acao === 'editar' ? campos(op.dados) : null;
    if (op.acao === 'excluir' && op.dados !== null) falhar();
    if (dados?.grupo) grupos.add(dados.grupo);
    return { tabela: 'financeiro_lancamentos', acao: op.acao, id: op.id, versao: op.versao, dados };
  });
  const resultado = new Map(registros.map(r => [r.id, r]));
  for (const op of operacoes) {
    if (op.acao === 'excluir') resultado.delete(op.id);
    else resultado.set(op.id, { id: op.id, ...op.dados });
  }
  for (const grupo of grupos) {
    const linhas = [...resultado.values()].filter(r => r.grupo === grupo).sort((a, b) => a.parcela - b.parcela);
    if (linhas.length && (linhas.length !== linhas[0].parcelas || linhas.some((r, i) =>
      r.parcela !== i + 1 || ['tipo', 'meio', 'categoria', 'descricao', 'parcelas', 'data_compra'].some(k => (r[k] ?? null) !== (linhas[0][k] ?? null))))) falhar();
  }
  return { operacoes, antes: [...guardas.values()].reduce((s, r) => s + r.valor_centavos, 0),
    depois: operacoes.reduce((s, op) => s + (op.dados?.valor_centavos ?? 0), 0),
    exclusoes: operacoes.filter(op => op.acao === 'excluir').length };
}
