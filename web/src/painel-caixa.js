import {calcularCaixa,movimentoCaixaFormulario} from './caixa.js';
import {hoje,moeda} from './regras.js';
import {baixar} from './exportacao.js';
const $=id=>document.getElementById('caixa-'+id);
const br=s=>s.split('-').reverse().join('/');
const texto=(tag,s)=>{const e=document.createElement(tag);e.textContent=s;return e;};
export function criarPainelCaixa({api,sessao}) {
  let snapshot=null,ocupado=false,geracao=0,editado=false;
  const form=$('form');
  const chave=()=>sessao()?`feira-caixa-pendente:${sessao().user.id}`:null;
  const pendente=()=>{const k=chave();return k?JSON.parse(localStorage.getItem(k)||'null'):null;};
  const aviso=s=>$('status').textContent=s;
  function controles() {
    let pendencia=true;try{pendencia=!!pendente();}catch{}
    $('atualizar').disabled=ocupado||!navigator.onLine||!sessao();
    $('exportar').disabled=ocupado||!snapshot||pendencia||!sessao();
    for(const e of form.elements) e.disabled=ocupado||pendencia||!snapshot||!navigator.onLine;
    $('salvar').disabled=ocupado||pendencia||!snapshot||!navigator.onLine;
    $('cancelar-form').disabled=ocupado;
    for(const e of $('historico').querySelectorAll('button'))e.disabled=ocupado||pendencia||!navigator.onLine;
  }
  function adaptar() {
    const posicao=['abertura','conferencia'].includes(form.elements.tipo.value);
    $('posicao').hidden=!posicao;$('movimento').hidden=posicao;
    form.elements.dinheiro.required=posicao;form.elements.saldo_conta.required=posicao;form.elements.valor.required=!posicao;
  }
  function limparFormulario() {form.reset();form.elements.data.value=hoje();form.elements.data.max=hoje();editado=false;const aberto=snapshot?.movimentos.some(r=>r.tipo==='abertura'&&!r.cancelado);form.elements.tipo.value=aberto?'entrada':'abertura';adaptar();}
  function desenhar() {
    const r=calcularCaixa(snapshot,hoje());
    $('saldos').hidden=!r;$('historico').replaceChildren();
    const nomes={abertura:'Saldo inicial',entrada:'Entrada recebida',saida:'Saída paga',transferencia:'Transferência',conferencia:'Conferência'};
    for(const m of [...snapshot.movimentos].sort((a,b)=>b.data.localeCompare(a.data)||b.created_at.localeCompare(a.created_at))) {
      const item=texto('li',`${br(m.data)} · ${nomes[m.tipo]} · ${m.descricao}${m.cancelado?' · Cancelado':''}`);
      const posicao=['abertura','conferencia'].includes(m.tipo);
      item.append(texto('p',posicao?`Dinheiro: ${moeda(m.dinheiro_centavos)} · Conta: ${moeda(m.conta_centavos)}`:`${m.conta==='dinheiro'?'Dinheiro físico':'Em conta'}${m.tipo==='transferencia'?' → '+(m.conta==='dinheiro'?'Em conta':'Dinheiro físico'):''}: ${moeda(m.valor_centavos)}`));
      const conferencia=r?.conferencias.find(c=>c.id===m.id);
      if(conferencia)item.append(texto('p',`Diferença (informado − calculado): dinheiro ${moeda(conferencia.diferenca_dinheiro)}; conta ${moeda(conferencia.diferenca_conta)}. Não altera o saldo. A comparação considera as vendas e despesas cadastradas hoje para essa data.`));
      if(!m.cancelado) {
        const b=texto('button','Cancelar registro');b.type='button';
        b.addEventListener('click',()=>{if(confirm(`Cancelar “${m.descricao}”? O registro permanece no histórico. Cancelar uma entrada/saída recalcula o saldo.`)) gravar({acao:'cancelar',id:m.id,versao:m.versao});});item.append(b);
      }
      $('historico').append(item);
    }
    if(r) {
      for(const k of ['dinheiro','conta','total'])$(k).textContent=moeda(r[k]);
      aviso(`Saldo acompanhado até ${br(hoje())}, após a posição inicial ao fim de ${br(r.abertura.data)}. Recebimentos do cartão e pagamentos de fatura precisam de confirmação.${r.outros?` Há ${r.outros} despesa(s) em “Outro” após o início: confira se a saída foi registrada no caixa.`:''}`);
    } else aviso('Informe o dinheiro físico e o saldo em conta que você já tem ao fim da data escolhida. O resultado do período abaixo continua separado.');
    form.elements.tipo.querySelector('[value="abertura"]').disabled=!!r;
    controles();
  }
  async function enviar(lote,k) {
    const remover=()=>{if(JSON.parse(localStorage.getItem(k)||'null')?.operacao_id===lote.operacao_id)localStorage.removeItem(k);};
    try {await api().salvarCaixa(lote);remover();}
    catch(e){if(['22023','23505','23514','23502','22P02','22007','22008','42501','40001'].includes(e?.code))remover();throw e;}
  }
  async function atualizar() {
    if(ocupado||!sessao())return;
    if(!navigator.onLine){aviso('Sem conexão: o caixa não foi atualizado.');controles();return;}
    const atual=geracao,k=chave();ocupado=true;controles();
    try {
      const lote=pendente();if(lote){await enviar(lote,k);if(atual===geracao)editado=false;}
      const recebido=await api().caixa();if(atual!==geracao)return;
      calcularCaixa(recebido,hoje());snapshot=recebido;desenhar();
      if(!editado)limparFormulario();
    } catch(e) {if(atual===geracao){snapshot=null;$('saldos').hidden=true;$('historico').replaceChildren();aviso(e?.code==='PGRST202'?'Caixa ainda não habilitado no banco. Execute supabase/migrations/007_caixa.sql no SQL Editor; as demais funções continuam disponíveis.':'Não foi possível confirmar/consultar o caixa. Use Atualizar caixa para retomar o mesmo envio. Nenhum envio pendente deve ser recriado.');}}
    finally{if(atual===geracao){ocupado=false;controles();}}
  }
  async function gravar(pedido) {
    if(ocupado||!sessao()||!navigator.onLine)return;
    const atual=geracao,k=chave();ocupado=true;controles();
    try {
      if(pendente())throw Error('Retome o envio pendente com Atualizar caixa.');
      const lote={pedido,operacao_id:crypto.randomUUID()};localStorage.setItem(k,JSON.stringify(lote));
      await enviar(lote,k);if(atual!==geracao)return;
      editado=false;limparFormulario();
    }catch(e){if(atual===geracao){aviso(e?.code==='40001'?'O registro mudou. Atualize o caixa antes de tentar novamente.':e?.code==='22023'?'Confira as datas: movimentos devem ser posteriores ao saldo inicial e não futuros. Para corrigir uma abertura que já tem movimentos, registre um ajuste com motivo.':'Envio não confirmado. Use Atualizar caixa para retomar o mesmo pedido.');return;}}
    finally{if(atual===geracao){ocupado=false;controles();}}
    if(atual===geracao)await atualizar();
  }
  form.addEventListener('input',()=>editado=true);
  form.elements.tipo.addEventListener('change',()=>{editado=true;adaptar();});
  form.addEventListener('submit',e=>{
    e.preventDefault();
    try{
      const dados=movimentoCaixaFormulario(Object.fromEntries(new FormData(form)),crypto.randomUUID());
      if(dados.data>hoje())throw Error('Informe uma data até hoje para valores efetivamente recebidos ou pagos.');
      if(dados.tipo!=='abertura'&&snapshot?.movimentos.some(r=>r.tipo==='abertura'&&!r.cancelado&&dados.data<=r.data))throw Error('Use uma data posterior ao saldo inicial, que representa o fim daquele dia.');
      if(dados.tipo==='abertura'&&!confirm('Esses valores são o dinheiro e o saldo em conta ao FIM da data escolhida? Movimentos desse dia já estão incluídos e não serão somados novamente.'))return;
      gravar({acao:'inserir',dados});
    }catch(e){aviso(e.message);}
  });
  $('atualizar').addEventListener('click',atualizar);
  $('cancelar-form').addEventListener('click',limparFormulario);
  $('exportar').addEventListener('click',()=>{
    if(!snapshot||ocupado||!sessao()||pendente())return;
    baixar(new Blob([JSON.stringify({formato:'gestao-da-feira-caixa',versao_formato:1,gerado_em:new Date().toISOString(),criterio:'Posição inicial ao fim do dia. Dinheiro/Pix automáticos; cartão e fatura confirmados manualmente. Exportação de conferência, sem restauração automática.',...snapshot},null,2)],{type:'application/json;charset=utf-8'}),`caixa-completo-${hoje()}.json`);
  });
  window.addEventListener('online',()=>{controles();if(snapshot)aviso('Conexão retomada. Atualize o caixa para conferir o saldo.');});window.addEventListener('offline',()=>{controles();if(snapshot)aviso('Sem conexão. Os valores são da última consulta; atualize o caixa ao reconectar.');});
  limparFormulario();controles();
  return {atualizar,ocupado:()=>{try{return ocupado||editado||!!pendente();}catch{return true;}},limpar(){geracao++;snapshot=null;ocupado=false;editado=false;form.reset();$('edicao').open=false;$('saldos').hidden=true;$('historico').replaceChildren();for(const k of ['dinheiro','conta','total'])$(k).textContent='—';aviso('');limparFormulario();controles();}};
}
