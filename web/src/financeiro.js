import { diaNoMes } from './fechamento.js';
import { centavos, dataValida, periodo, resumo } from './regras.js';
export const MEIOS = ['Dinheiro', 'Pix', 'Cartão de crédito', 'Outro'];
export const CATEGORIAS = ['Casa', 'Feira', 'Outros', 'Compromisso inicial'];
const iso = (d) => d.toISOString().slice(0, 10);
export function primeiraFatura(compra, fechamento = null) {
  if (!dataValida(compra) || (fechamento !== null && (!Number.isInteger(fechamento) || fechamento < 1 || fechamento > 31)))
    throw Error('Confira a data da compra e o dia de fechamento.');
  const d = new Date(compra + 'T12:00:00Z');
  const ultimo = new Date(d); ultimo.setUTCMonth(ultimo.getUTCMonth() + 1, 0);
  const atual = new Date(d); atual.setUTCDate(Math.min(fechamento ?? diaNoMes(d.getUTCFullYear(), d.getUTCMonth() + 1), ultimo.getUTCDate()));
  if (d < atual) return iso(atual);
  d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + 1);
  ultimo.setTime(+d); ultimo.setUTCMonth(ultimo.getUTCMonth() + 1, 0);
  d.setUTCDate(Math.min(fechamento ?? diaNoMes(d.getUTCFullYear(), d.getUTCMonth() + 1), ultimo.getUTCDate()));
  const resultado = iso(d);
  if (!dataValida(resultado)) throw Error('A fatura ultrapassa o limite de datas.');
  return resultado;
}
export function limitesFinanceiros(tipo, referencia) {
  if (!dataValida(referencia))
    throw Error('Informe uma data de referência válida.');
  const [ano, mes] = referencia.split('-').map(Number);
  if (tipo !== 'Semana') return periodo(tipo, ano, mes);
  const d = new Date(`${referencia}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  const inicio = iso(d);
  d.setUTCDate(d.getUTCDate() + 6);
  return { inicio, fim: iso(d) };
}
export function resumoFinanceiro(dados, { inicio, fim }) {
  const dentro = (r) => r.data >= inicio && r.data <= fim;
  const vendas = dados.vendas.filter(dentro);
  const lancamentos = dados.financeiro_lancamentos.filter(dentro);
  const bruto = resumo(vendas).total;
  let taxas = lancamentos
    .filter((r) => r.tipo === 'taxa')
    .reduce((s, r) => s + Number(r.valor_centavos), 0);
  const despesas = lancamentos
    .filter((r) => r.tipo === 'despesa')
    .reduce((s, r) => s + Number(r.valor_centavos), 0);
  const parciais = [],
    estimados = [],
    semanas = new Map();
  for (const r of dados.financeiro_taxas_anuais) {
    if (r.inicio > fim || r.fim < inicio) continue;
    if (r.natureza === 'Estimada') estimados.push(r.ano);
    if (inicio <= r.inicio && fim >= r.fim) taxas += Number(r.valor_centavos);
    else parciais.push(r.ano);
  }
  for (const r of lancamentos.filter((r) => r.tipo === 'despesa')) {
    const segunda = limitesFinanceiros('Semana', r.data).inicio;
    semanas.set(
      segunda,
      (semanas.get(segunda) || 0) + Number(r.valor_centavos)
    );
  }
  return {
    bruto,
    taxas,
    liquido: bruto - taxas,
    despesas,
    saldo: bruto - taxas - despesas,
    falta: Math.max(0, taxas + despesas - bruto),
    parciais,
    estimados,
    lancamentos,
    semanas: [...semanas].sort(([a], [b]) => a.localeCompare(b)),
  };
}
export function lancamentoFormulario(
  form,
  anterior = null,
  uuid = () => crypto.randomUUID()
) {
  const descricao = String(form.descricao || '').trim();
  const valor_centavos = centavos(form.valor);
  const parcelas = Number(form.parcelas || 1);
  if (!dataValida(form.data)) throw Error('Informe uma data válida.');
  if (!descricao || descricao.length > 200)
    throw Error('Preencha uma descrição de até 200 caracteres.');
  if (valor_centavos <= 0) throw Error('O valor deve ser maior que zero.');
  if (
    !['despesa', 'taxa'].includes(form.tipo) ||
    !MEIOS.includes(form.meio) ||
    !CATEGORIAS.includes(form.categoria)
  )
    throw Error('Confira o tipo, o meio de pagamento e a categoria.');
  if (
    !Number.isInteger(parcelas) ||
    parcelas < 1 ||
    parcelas > 120 ||
    (parcelas > 1 &&
      (anterior ||
        form.tipo !== 'despesa' ||
        form.meio !== 'Cartão de crédito'))
  )
    throw Error('Use de 1 a 120 parcelas apenas para nova despesa no cartão.');
  const grupo = parcelas > 1 ? uuid() : null;
  const [, mes, dia] = form.data.split('-').map(Number);
  return Array.from({ length: parcelas }, (_, i) => {
    const primeiro = new Date(`${form.data}T12:00:00Z`);
    primeiro.setUTCDate(1);
    primeiro.setUTCMonth(mes - 1 + i);
    const ultimo = new Date(primeiro);
    ultimo.setUTCMonth(ultimo.getUTCMonth() + 1);
    ultimo.setUTCDate(0);
    primeiro.setUTCDate(Math.min(dia, ultimo.getUTCDate()));
    const data = iso(primeiro);
    if (!dataValida(data) || Number(data.slice(0, 4)) > 9999)
      throw Error('O parcelamento ultrapassa o limite de datas.');
    const dados = {
      tipo: form.tipo,
      data,
      descricao,
      valor_centavos,
      meio: form.meio,
      categoria: form.categoria,
      grupo: anterior?.grupo ?? grupo,
      parcela: anterior?.parcela ?? i + 1,
      parcelas: anterior?.parcelas ?? parcelas,
    };
    if (dados.parcelas > 1 && dados.meio !== 'Cartão de crédito')
      throw Error('Uma parcela deve manter o pagamento no cartão de crédito.');
    return {
      tabela: 'financeiro_lancamentos',
      acao: anterior ? 'editar' : 'inserir',
      id: anterior?.id ?? uuid(),
      versao: anterior?.versao ?? null,
      dados,
    };
  });
}
export function anualFormulario(
  form,
  anterior = null,
  uuid = () => crypto.randomUUID()
) {
  const ano = Number(form.ano),
    valor_centavos = centavos(form.valor);
  if (
    !Number.isInteger(ano) ||
    ano < 1 ||
    ano > 9999 ||
    !dataValida(form.inicio) ||
    !dataValida(form.fim) ||
    Number(form.inicio.slice(0, 4)) !== ano ||
    Number(form.fim.slice(0, 4)) !== ano ||
    form.inicio > form.fim
  )
    throw Error(
      'O intervalo deve estar em ordem crescente e dentro do ano informado.'
    );
  if (!['Confirmada', 'Estimada'].includes(form.natureza))
    throw Error('Escolha Confirmada ou Estimada.');
  if (valor_centavos <= 0) throw Error('O valor deve ser maior que zero.');
  return [
    {
      tabela: 'financeiro_taxas_anuais',
      acao: anterior ? 'editar' : 'inserir',
      id: anterior?.id ?? uuid(),
      versao: anterior?.versao ?? null,
      dados: {
        ano,
        inicio: form.inicio,
        fim: form.fim,
        valor_centavos,
        natureza: form.natureza,
        observacao: String(form.observacao || '').trim(),
      },
    },
  ];
}
export function erroFinanceiro(erro) {
  if (erro?.armazenamento)
    return 'Não foi possível preparar o envio neste navegador. Permita armazenamento local para salvar com segurança.';
  if (erro?.code === '23505')
    return 'Há data, ano ou parcela duplicada, ou uma taxa diária coberta por ajuste anual. Confira os registros existentes.';
  if (erro?.code === 'PFS01' || erro?.conflito)
    return 'O registro mudou em outro acesso. Atualize e reabra o formulário antes de editar.';
  if (
    ['23514', '23502', '22P02', '22007', '22008', 'PFS02'].includes(erro?.code)
  )
    return 'O banco recusou os valores ou as datas. Nenhuma parte deste lote foi gravada.';
  if (erro?.code === '42501')
    return 'Sua conta não tem autorização para esta operação.';
  return 'Não foi possível confirmar o envio. Use Atualizar para retomar a mesma operação com segurança.';
}
export const recusaConfirmada = (erro) =>
  [
    '23505',
    'PFS01',
    '23514',
    '23502',
    '22P02',
    '22007',
    '22008',
    'PFS02',
    '42501',
  ].includes(erro?.code);

export function taxasSemanaFormulario(inicio, valores, existentes, anuais, uuid = () => crypto.randomUUID()) {
  if (!dataValida(inicio) || limitesFinanceiros('Semana', inicio).inicio !== inicio)
    throw Error('Escolha uma semana de segunda a domingo.');
  const datas = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(inicio + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + i); return iso(d);
  });
  if (Object.keys(valores).some(data => !datas.includes(data))) throw Error('Há uma data fora da semana.');
  const ops = [];
  for (const data of datas) {
    const texto = String(valores[data] ?? '').trim();
    if (!texto) continue;
    const valor = centavos(texto);
    const anterior = existentes.find(r => r.tipo === 'taxa' && r.data === data);
    if (!valor) {
      if (anterior) throw Error('Para remover uma taxa existente, use Excluir no lançamento.');
      continue;
    }
    if (anuais.some(a => a.inicio <= data && a.fim >= data))
      throw Error('Esta data já está incluída em um total histórico de taxas. Não registre o mesmo desconto novamente.');
    if (anterior && Number(anterior.valor_centavos) === valor) continue;
    ops.push(...lancamentoFormulario({ tipo: 'taxa', data, valor: texto,
      descricao: anterior?.descricao || 'Taxa das vendas no cartão',
      meio: anterior?.meio || 'Outro', categoria: anterior?.categoria || 'Feira', parcelas: '1' }, anterior, uuid));
  }
  if (!ops.length) throw Error('Nenhuma taxa nova ou alterada para salvar. Preencha os dias em que houve desconto.');
  return ops;
}
