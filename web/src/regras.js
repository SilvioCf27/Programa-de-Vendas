export function centavos(texto) {
  let valor = String(texto).trim();
  if (!valor) return 0;
  if (valor.includes(',')) {
    if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+),\d{1,2}$/.test(valor))
      throw Error('Informe valores como 125,50.');
    valor = valor.replaceAll('.', '').replace(',', '.');
  }
  if (!/^\d+(?:\.\d{1,2})?$/.test(valor))
    throw Error('Use valores positivos com até duas casas decimais.');
  const [inteiro, fracao = ''] = valor.split('.');
  const resultado = Number(inteiro) * 100 + Number(fracao.padEnd(2, '0'));
  if (!Number.isSafeInteger(resultado) || resultado > 99999999999)
    throw Error('Valor fora do limite permitido.');
  return resultado;
}
export const moeda = (valor) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(
    valor / 100
  );
export function dataValida(valor) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(valor) || valor.startsWith('0000'))
    return false;
  const dia = new Date(`${valor}T12:00:00Z`);
  return !Number.isNaN(+dia) && dia.toISOString().slice(0, 10) === valor;
}
export function hoje() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
export function mesFechamento(data = hoje()) {
  const [ano, mes, dia] = data.split('-').map(Number);
  return dia > 9
    ? { ano, mes }
    : mes === 1
      ? { ano: ano - 1, mes: 12 }
      : { ano, mes: mes - 1 };
}
export function periodo(tipo, ano, mes) {
  if (tipo === 'Todas') return { inicio: null, fim: null };
  ano = Number(ano);
  mes = Number(mes);
  if (
    !Number.isInteger(ano) ||
    ano < 1900 ||
    ano > 9998 ||
    !Number.isInteger(mes) ||
    mes < 1 ||
    mes > 12
  )
    throw Error('Confira o ano e o mês.');
  const prefixo = `${ano}-${String(mes).padStart(2, '0')}`;
  if (tipo === 'Ano') return { inicio: `${ano}-01-01`, fim: `${ano}-12-31` };
  if (tipo === 'Mês')
    return {
      inicio: `${prefixo}-01`,
      fim: `${prefixo}-${new Date(Date.UTC(ano, mes, 0)).getUTCDate()}`,
    };
  if (tipo === 'Fechamento')
    return {
      inicio: `${prefixo}-10`,
      fim: `${mes === 12 ? ano + 1 : ano}-${String(mes === 12 ? 1 : mes + 1).padStart(2, '0')}-09`,
    };
  throw Error('Escolha um período válido.');
}
export function resumo(vendas) {
  const total = vendas.reduce(
    (s, r) =>
      s +
      Number(r.dinheiro_centavos) +
      Number(r.pix_centavos) +
      Number(r.cartao_centavos),
    0
  );
  return {
    total,
    quantidade: vendas.length,
    media: vendas.length ? Math.round(total / vendas.length) : 0,
  };
}
export function vendaFormulario(form) {
  if (!dataValida(form.data)) throw Error('Informe uma data válida.');
  return {
    data: form.data,
    dinheiro_centavos: centavos(form.dinheiro),
    pix_centavos: centavos(form.pix),
    cartao_centavos: centavos(form.cartao),
  };
}
export function erroAmigavel(erro) {
  if (erro?.code === '23505')
    return 'Já existe uma venda nessa data. Edite o registro existente.';
  if (erro?.code === '42501')
    return 'Esta conta não tem permissão para alterar os dados.';
  if (erro?.conflito)
    return 'Esse registro foi alterado em outro acesso. Atualize a lista antes de tentar novamente.';
  return 'Não foi possível concluir. Confira a conexão e tente novamente.';
}
