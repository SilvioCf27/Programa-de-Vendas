import { periodoFechamento } from './fechamento.js';
import { dataValida } from './regras.js';
import { MEIOS, CATEGORIAS, lancamentoFormulario } from './financeiro.js';
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
  if (!plano || plano.formato !== 'gestao-da-feira-correcoes' || ![1, 2, 3].includes(plano.versao_formato) ||
      !Array.isArray(plano.verificacoes) || !Array.isArray(plano.alteracoes) || !plano.alteracoes.length || plano.alteracoes.length > 500 ||
      plano.verificacoes.length !== plano.alteracoes.length) falhar();
  const atuais = new Map(registros.map(r => [r.id, r]));
  const guardas = new Map();
  for (const v of plano.verificacoes) {
    if (!uuid(v.id) || guardas.has(v.id)) falhar();
    if (plano.versao_formato >= 2 && v.versao === null && v.campos === null) {
      if (atuais.has(v.id)) falhar();
      guardas.set(v.id, null);
      continue;
    }
    if (!inteiro(v.versao)) falhar();
    const antes = campos(v.campos), atual = atuais.get(v.id);
    if (!atual || atual.versao !== v.versao || CAMPOS_CORRECAO.some(k => (atual[k] ?? null) !== antes[k])) falhar();
    guardas.set(v.id, antes);
  }
  // Todos os membros atuais dos grupos envolvidos devem estar no lote, até os inalterados.
  const gruposOriginais = new Set([...guardas.values()].filter(Boolean).map(r => r.grupo).filter(Boolean));
  const grupos = new Set(gruposOriginais);
  if (registros.some(r => grupos.has(r.grupo) && !guardas.has(r.id))) falhar();
  const ids = new Set();
  const operacoes = plano.alteracoes.map(op => {
    const antes = guardas.get(op.id);
    const insercao = op.acao === 'inserir';
    if (!guardas.has(op.id) || ids.has(op.id) || op.tabela !== 'financeiro_lancamentos' ||
        !['excluir', 'editar', 'inserir'].includes(op.acao)) falhar();
    if (insercao ? (plano.versao_formato < 2 || antes !== null || op.versao !== null || atuais.has(op.id)) : (!antes || op.versao !== atuais.get(op.id).versao)) falhar();
    ids.add(op.id);
    const dados = op.acao === 'excluir' ? null : campos(op.dados);
    if (plano.versao_formato !== 3 && insercao && (dados.parcelas <= 1 || !gruposOriginais.has(dados.grupo))) falhar();
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
  const faturas = plano.versao_formato === 2 ? plano.faturas : [];
  if (!Array.isArray(faturas) || faturas.length > 10) falhar();
  const conferidos = new Set();
  for (const meta of faturas) {
    if (!meta || !gruposOriginais.has(meta.grupo) || conferidos.has(meta.grupo) ||
        !dataValida(meta.data_compra) || !inteiro(meta.total_centavos) || meta.total_centavos > 99999999999 ||
        !inteiro(meta.parcelas) || meta.parcelas > 120) falhar();
    conferidos.add(meta.grupo);
    const linhas = [...resultado.values()].filter(r => r.grupo === meta.grupo).sort((a,b) => a.parcela - b.parcela);
    if (!linhas.length || linhas.length !== meta.parcelas) falhar();
    const valor = `${Math.floor(meta.total_centavos / 100)}.${String(meta.total_centavos % 100).padStart(2,'0')}`;
    const modelo = lancamentoFormulario({tipo:'despesa',data:meta.data_compra,origem_data:'compra',descricao:linhas[0].descricao,valor,meio:'Cartão de crédito',categoria:linhas[0].categoria,parcelas:meta.parcelas}, null, () => 'validacao-sem-envio');
    if (linhas.some((r,i) => ['data','data_compra','valor_centavos','parcela','parcelas'].some(k => r[k] !== modelo[i].dados[k]))) throw Object.assign(Error('Datas ou valores diferem das regras de parcelamento e fechamento.'), {code:'PLANO_FATURAS_DIVERGENTE'});
  }
  if (plano.versao_formato !== 3 && operacoes.some(op => op.acao === 'inserir' && !conferidos.has(op.dados.grupo))) falhar();
  if (plano.versao_formato === 3) conferirConciliacoes(plano, guardas, operacoes, resultado);
  const insercoes = operacoes.filter(op => op.acao === 'inserir').length;
  return { operacoes, insercoes, atualizacoes: operacoes.length - insercoes - operacoes.filter(op => op.acao === 'excluir').length,
    antes: [...guardas.values()].filter(Boolean).reduce((s, r) => s + r.valor_centavos, 0),
    depois: operacoes.reduce((s, op) => s + (op.dados?.valor_centavos ?? 0), 0),
    exclusoes: operacoes.filter(op => op.acao === 'excluir').length };
}

// O documento é uma referência fornecida pelo usuário, não uma assinatura do banco.
// O plano mantém a cópia, a confirmação e as versões do mesmo protocolo de gravação.
function conferirConciliacoes(plano, guardas, operacoes, resultado) {
  const metas = plano.conciliacoes;
  if (!Array.isArray(metas) || !metas.length || metas.length > 12) falhar();
  const inseridos = new Set(operacoes.filter(op => op.acao === 'inserir').map(op => op.id));
  const cobertos = new Set(), periodos = new Set();
  for (const antes of guardas.values()) if (antes && antes.meio !== 'Cartão de crédito') falhar();
  for (const op of operacoes) {
    if (op.acao === 'inserir' && (op.dados.meio !== 'Cartão de crédito' || op.dados.parcelas !== 1)) falhar();
    // Reclassificar uma despesa não pode mudar o valor nem criar parcelas não-cartão.
    if (op.dados && op.dados.meio !== 'Cartão de crédito' &&
        (op.dados.meio !== 'Outro' || op.dados.valor_centavos !== guardas.get(op.id)?.valor_centavos)) falhar();
  }
  for (const meta of metas) {
    if (!meta || !dataValida(meta.inicio) || !dataValida(meta.fim) || meta.inicio > meta.fim ||
        !inteiro(meta.total_centavos) || !Array.isArray(meta.movimentos) || !meta.movimentos.length || meta.movimentos.length > 500 ||
        typeof meta.referencia !== 'string' || !meta.referencia.trim() || meta.referencia.length > 200 ||
        typeof meta.completa !== 'boolean') falhar();
    const [ano, mes] = meta.inicio.split('-').map(Number);
    const periodo = periodoFechamento(ano, mes);
    if (periodo.inicio !== meta.inicio || periodo.fim !== meta.fim || periodos.has(meta.inicio)) falhar();
    periodos.add(meta.inicio);
    const porRegistro = new Map();
    let total = 0;
    for (const m of meta.movimentos) {
      if (!m || !uuid(m.id) || !inteiro(m.valor_centavos) ||
          (m.data_compra !== null && !dataValida(m.data_compra)) || !inteiro(m.parcela) || !inteiro(m.parcelas)) falhar();
      const r = resultado.get(m.id);
      if (!r || r.tipo !== 'despesa' || r.meio !== 'Cartão de crédito' || r.data < meta.inicio || r.data > meta.fim ||
          (r.data_compra ?? null) !== m.data_compra || r.parcela !== m.parcela || r.parcelas !== m.parcelas) falhar();
      porRegistro.set(m.id, (porRegistro.get(m.id) || 0) + m.valor_centavos);
      total += m.valor_centavos;
      cobertos.add(m.id);
    }
    if (!Number.isSafeInteger(total) || total !== meta.total_centavos) falhar();
    for (const [id, valor] of porRegistro) if (resultado.get(id).valor_centavos !== valor) falhar();
    const linhas = [...resultado.values()].filter(r => r.tipo === 'despesa' && r.meio === 'Cartão de crédito' && r.data >= meta.inicio && r.data <= meta.fim);
    if (meta.completa && (linhas.length !== porRegistro.size || linhas.some(r => !porRegistro.has(r.id)))) falhar();
  }
  if ([...inseridos].some(id => !cobertos.has(id))) falhar();
  if (!Array.isArray(plano.totais_preservados) || plano.totais_preservados.length > 50) falhar();
  const grupos = new Set();
  for (const meta of plano.totais_preservados) {
    if (!meta || typeof meta.grupo !== 'string' || grupos.has(meta.grupo) || !inteiro(meta.total_centavos)) falhar();
    grupos.add(meta.grupo);
    const antes = [...guardas.values()].filter(r => r?.grupo === meta.grupo);
    const depois = [...resultado.values()].filter(r => r.grupo === meta.grupo);
    if (!antes.length || !depois.length || [antes, depois].some(rs => rs.reduce((n,r) => n+r.valor_centavos, 0) !== meta.total_centavos)) falhar();
  }
}
