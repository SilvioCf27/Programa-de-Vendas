import { historicoFinanceiro } from './historico-financeiro.js';

const CAMPOS = ['id', 'tipo', 'data', 'data_compra', 'descricao', 'valor_centavos', 'meio', 'categoria', 'grupo', 'parcela', 'parcelas', 'versao'];
const ANUAIS = ['id', 'ano', 'inicio', 'fim', 'valor_centavos', 'natureza', 'observacao', 'versao'];
const escolher = (r, campos) => Object.fromEntries(campos.map(c => [c, r[c] ?? null]));

export function montarExportacaoFinanceira(dados, selecao, escopo, consultadoEm, geradoEm = new Date().toISOString()) {
  if (!dados || !selecao || !consultadoEm || !['historico_completo', 'consulta_aplicada'].includes(escopo))
    throw Error('Consulte as finanças antes de exportar e confira o escopo.');
  const completo = escopo === 'historico_completo';
  const dentro = r => r.data >= selecao.inicio && r.data <= selecao.fim;
  const linhas = dados.financeiro_lancamentos.filter(r => completo || (dentro(r) && (r.tipo === 'taxa' || !selecao.meio || selecao.meio === 'Todos' || r.meio === selecao.meio)));
  const anuais = dados.financeiro_taxas_anuais.filter(r => completo || (r.inicio <= selecao.fim && r.fim >= selecao.inicio));
  return {
    formato: 'gestao-da-feira-financas', versao_formato: 1, moeda: 'BRL', unidade_monetaria: 'centavos',
    gerado_em: geradoEm, consultado_em: consultadoEm, escopo,
    consulta: completo ? null : escolher(selecao, ['tipo', 'referencia', 'inicio', 'fim', 'meio']),
    criterios: {
      periodo: 'Data da fatura/pagamento (campo data); data_compra é a compra original quando informada.',
      busca: 'A busca visual não limita esta exportação.',
      parcelas: completo ? 'Uma linha por parcela; parcelas do mesmo grupo conservam seus identificadores.' : 'Somente parcelas no período aplicado; o grupo pode estar incompleto neste arquivo.',
      taxas_anuais: 'Totais históricos separados das taxas por data; não são somados nem rateados automaticamente.',
      finalidade: 'Conferência somente leitura; não é backup completo nem arquivo de restauração.',
    },
    financeiro_lancamentos: historicoFinanceiro(linhas).map(r => escolher(r, CAMPOS)),
    financeiro_taxas_anuais: [...anuais].sort((a, b) => b.ano - a.ano).map(r => escolher(r, ANUAIS)),
    totais_registros: {
      lancamentos: linhas.length, ajustes_anuais: anuais.length,
      despesas_centavos: linhas.filter(r => r.tipo === 'despesa').reduce((s, r) => s + Number(r.valor_centavos), 0),
      taxas_por_data_centavos: linhas.filter(r => r.tipo === 'taxa').reduce((s, r) => s + Number(r.valor_centavos), 0),
      ajustes_anuais_centavos: anuais.reduce((s, r) => s + Number(r.valor_centavos), 0),
    },
  };
}

export const gerarJsonFinanceiro = (relatorio) => JSON.stringify(relatorio, null, 2);
const celula = (v) => {
  let texto = v == null ? '' : String(v);
  if (/^[\s]*[=+@-]/.test(texto)) texto = "'" + texto;
  return '"' + texto.replaceAll('"', '""') + '"';
};
export function gerarCsvFinanceiro(r) {
  const cabecalho = ['Escopo', 'ID', 'Tipo', 'Data compra (ISO)', 'Fatura/pagamento (ISO)', 'Descrição', 'Valor centavos', 'Valor R$', 'Meio', 'Categoria', 'Grupo', 'Parcela', 'Parcelas', 'Versão', 'Ano ajuste', 'Início cobertura', 'Fim cobertura', 'Natureza', 'Observação', 'Consulta início', 'Consulta fim', 'Filtro despesas', 'Consultado em', 'Gerado em'];
  const contexto = [r.consulta?.inicio, r.consulta?.fim, r.consulta?.meio, r.consultado_em, r.gerado_em];
  const linhas = r.financeiro_lancamentos.map(l => [r.escopo, l.id, l.tipo, l.data_compra, l.data, l.descricao, l.valor_centavos, (l.valor_centavos / 100).toFixed(2).replace('.', ','), l.meio, l.categoria, l.grupo, l.parcela, l.parcelas, l.versao, '', '', '', '', '', ...contexto]);
  for (const a of r.financeiro_taxas_anuais)
    linhas.push([r.escopo, a.id, 'ajuste_anual', '', '', '', a.valor_centavos, (a.valor_centavos / 100).toFixed(2).replace('.', ','), '', '', '', '', '', a.versao, a.ano, a.inicio, a.fim, a.natureza, a.observacao, ...contexto]);
  return '\ufeff' + [cabecalho, ...linhas].map(l => l.map(celula).join(';')).join('\r\n');
}
