import { centavos, dataValida } from './regras.js';
const limite=99999999999;
export function validarMovimentoCaixa(r) {
  if (!r || !['abertura','entrada','saida','transferencia','conferencia'].includes(r.tipo) || !dataValida(r.data) ||
      typeof r.descricao !== 'string' || !r.descricao.trim() || r.descricao.length>200) throw Error('Confira a data e a descrição do movimento.');
  if (['abertura','conferencia'].includes(r.tipo)) {
    if (r.conta!==null || r.valor_centavos!==null || [r.dinheiro_centavos,r.conta_centavos].some(n=>!Number.isSafeInteger(n)||n<0||n>limite)) throw Error('Confira o dinheiro físico e o saldo em conta.');
  } else if (!['dinheiro','conta'].includes(r.conta) || !Number.isSafeInteger(r.valor_centavos) || r.valor_centavos<=0 || r.valor_centavos>limite || r.dinheiro_centavos!==null || r.conta_centavos!==null) throw Error('Confira a conta e o valor do movimento.');
  return r;
}
export function movimentoCaixaFormulario(form, id) {
  const posicao=['abertura','conferencia'].includes(form.tipo);
  return validarMovimentoCaixa({id,tipo:form.tipo,data:form.data,descricao:String(form.descricao||'').trim(),conta:posicao?null:form.conta,valor_centavos:posicao?null:centavos(form.valor),dinheiro_centavos:posicao?centavos(form.dinheiro):null,conta_centavos:posicao?centavos(form.saldo_conta):null});
}
export function calcularCaixa(snapshot, ate) {
  if (!dataValida(ate) || !Array.isArray(snapshot?.movimentos) || !Array.isArray(snapshot?.vendas) || !Array.isArray(snapshot?.despesas)) throw Error('Consulta de caixa incompleta.');
  const ativos=snapshot.movimentos.filter(r=>!r.cancelado);
  ativos.forEach(validarMovimentoCaixa);
  const aberturas=ativos.filter(r=>r.tipo==='abertura');
  if (aberturas.length>1) throw Error('Há mais de um saldo inicial ativo.');
  const abertura=aberturas[0];
  if (!abertura || abertura.data>ate) return null;
  const calcular=fim=>{
    let dinheiro=abertura.dinheiro_centavos,conta=abertura.conta_centavos;
    const dentro=r=>r.data>abertura.data && r.data<=fim;
    for (const r of snapshot.vendas.filter(dentro)) {
      for(const k of ['dinheiro_centavos','pix_centavos']) if(!Number.isSafeInteger(r[k]) || r[k]<0) throw Error('Venda inválida no caixa.');
      dinheiro+=r.dinheiro_centavos;conta+=r.pix_centavos;
    }
    for (const r of snapshot.despesas.filter(r=>r.tipo==='despesa'&&dentro(r))) {
      if(!Number.isSafeInteger(r.valor_centavos)||r.valor_centavos<=0) throw Error('Despesa inválida no caixa.');
      if(r.meio==='Dinheiro') dinheiro-=r.valor_centavos;
      if(r.meio==='Pix') conta-=r.valor_centavos;
    }
    for(const r of ativos.filter(dentro)) {
      const fator=r.tipo==='entrada'?1:r.tipo==='saida'?-1:0;
      if(fator) {if(r.conta==='dinheiro') dinheiro+=fator*r.valor_centavos;else conta+=fator*r.valor_centavos;}
      if(r.tipo==='transferencia') {const n=r.conta==='dinheiro'?r.valor_centavos:-r.valor_centavos;dinheiro-=n;conta+=n;}
    }
    if(!Number.isSafeInteger(dinheiro)||!Number.isSafeInteger(conta)||!Number.isSafeInteger(dinheiro+conta)) throw Error('Saldo fora do limite.');
    return {dinheiro,conta,total:dinheiro+conta};
  };
  const conferencias=ativos.filter(r=>r.tipo==='conferencia'&&r.data>=abertura.data&&r.data<=ate).sort((a,b)=>b.data.localeCompare(a.data)||b.created_at.localeCompare(a.created_at));
  return {abertura,...calcular(ate),conferencias:conferencias.map(r=>{const calculado=calcular(r.data);return {...r,calculado,diferenca_dinheiro:r.dinheiro_centavos-calculado.dinheiro,diferenca_conta:r.conta_centavos-calculado.conta};}),outros:snapshot.despesas.filter(r=>r.tipo==='despesa'&&r.meio==='Outro'&&r.data>abertura.data&&r.data<=ate).length};
}
