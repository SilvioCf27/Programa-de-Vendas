import { definirFechamentos } from '../src/fechamento.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import { conferirCorrecoes, CAMPOS_CORRECAO } from '../src/correcoes-financeiras.js';
const id = i => `00000000-0000-4000-8000-${String(i).padStart(12,'0')}`;
function exemplo() {
  const registros = [1,2,3,4].map((i) => ({ id: id(i), versao: 1, tipo:'despesa', data:`2026-${i%2 ? '10':'11'}-09`, data_compra:null, descricao:'Compra fictícia', valor_centavos:100, meio:'Cartão de crédito', categoria:'Casa', grupo:id(i<=2?10:11), parcela:i%2?1:2, parcelas:2 }));
  const campos = r => Object.fromEntries(CAMPOS_CORRECAO.map(k => [k,r[k]]));
  const plano = { formato:'gestao-da-feira-correcoes',versao_formato:1,verificacoes:registros.map(r=>({id:r.id,versao:r.versao,campos:campos(r)})),alteracoes:registros.map((r,i)=>({tabela:'financeiro_lancamentos',acao:i<2?'editar':'excluir',id:r.id,versao:r.versao,dados:i<2?campos(r):null})) };
  return { registros,plano };
}
test('plano conferido não altera snapshot e preserva grupos completos',()=>{
  const {registros,plano}=exemplo(); const antes=JSON.stringify(registros);
  const r=conferirCorrecoes(plano,registros);
  assert.equal(r.exclusoes,2);assert.equal(r.antes,400);assert.equal(r.depois,200);
  assert.equal(JSON.stringify(registros),antes);
});
test('outra conta, versão ou conteúdo alterado recusa todo plano',()=>{
  const {registros,plano}=exemplo();assert.throws(()=>conferirCorrecoes(plano,[]));
  registros[0].versao++;assert.throws(()=>conferirCorrecoes(plano,registros));
  registros[0].versao--;registros[0].valor_centavos++;assert.throws(()=>conferirCorrecoes(plano,registros));
});
test('tabela indevida, IDs repetidos e inserções não são aceitos',()=>{
  for(const alterar of [p=>p.alteracoes[0].tabela='vendas',p=>p.alteracoes[1]=p.alteracoes[0],p=>p.alteracoes[0].acao='inserir',p=>p.alteracoes[0].dados.valor_centavos=-1]) {
    const {registros,plano}=exemplo();alterar(plano);assert.throws(()=>conferirCorrecoes(plano,registros));
  }
});
test('grupo não coberto pelo plano ou incompleto após aplicar é recusado',()=>{
  const {registros,plano}=exemplo();registros.push({...registros[0],id:id(99),parcela:3});assert.throws(()=>conferirCorrecoes(plano,registros));
  registros.pop();plano.alteracoes[0].acao='excluir';plano.alteracoes[0].dados=null;assert.throws(()=>conferirCorrecoes(plano,registros));
});
test('grupos hexadecimais legados do desktop também podem ser conferidos',()=>{
  const {registros,plano}=exemplo();
  for(const r of registros)r.grupo=r.grupo.replaceAll('-','');
  for(const v of plano.verificacoes)v.campos.grupo=v.campos.grupo.replaceAll('-','');
  for(const op of plano.alteracoes)if(op.dados)op.dados.grupo=op.dados.grupo.replaceAll('-','');
  assert.equal(conferirCorrecoes(plano,registros).exclusoes,2);
});

function exemploInclusao() {
  const grupo=id(20), compra='2030-03-12';
  const base={tipo:'despesa',data_compra:compra,descricao:'Compra parcelada fictícia',valor_centavos:1000,meio:'Cartão de crédito',categoria:'Casa',grupo,parcelas:18};
  const registros=Array.from({length:17},(_,i)=>{const parcela=i+2,m=2030*12+3+parcela-1;return {id:id(100+parcela),versao:1,...base,parcela,valor_centavos:parcela===18?1001:1000,data:`${Math.floor(m/12)}-${String(m%12+1).padStart(2,'0')}-09`};});
  const selecionar=r=>Object.fromEntries(CAMPOS_CORRECAO.map(k=>[k,r[k]]));
  const nova={...base,parcela:1,data:'2030-04-09',valor_centavos:1000};
  const plano={formato:'gestao-da-feira-correcoes',versao_formato:2,
    faturas:[{grupo,data_compra:compra,total_centavos:18001,parcelas:18}],
    verificacoes:[...registros.map(r=>({id:r.id,versao:r.versao,campos:selecionar(r)})),{id:id(101),versao:null,campos:null}],
    alteracoes:[...registros.map(r=>({tabela:'financeiro_lancamentos',acao:'editar',id:r.id,versao:r.versao,dados:selecionar(r)})),{tabela:'financeiro_lancamentos',acao:'inserir',id:id(101),versao:null,dados:nova}]};
  return {registros,plano};
}
test('v2 completa parcela ausente em grupo existente e verifica total exato',()=>{
  const {registros,plano}=exemploInclusao();
  const r=conferirCorrecoes(plano,registros);
  assert.equal(r.insercoes,1);assert.equal(r.atualizacoes,17);assert.equal(r.depois,18001);
  assert.equal(registros.length,17);
  assert.equal(r.operacoes.at(-1).dados.data,'2030-04-09');
});
test('v2 rejeita ID já existente, inserção sem conferência de faturas e soma alterada',()=>{
  for(const alterar of [p=>p.faturas=[],p=>p.alteracoes.at(-1).dados.valor_centavos++,p=>p.verificacoes.at(-1).id=p.verificacoes[0].id]) {
    const {registros,plano}=exemploInclusao();alterar(plano);assert.throws(()=>conferirCorrecoes(plano,registros));
  }
  const {registros,plano}=exemploInclusao();registros.push({id:id(101)});assert.throws(()=>conferirCorrecoes(plano,registros));
});
test('v2 não aceita primeiro vencimento no mês da compra após fechar a fatura',()=>{
  const {registros,plano}=exemploInclusao();plano.alteracoes.at(-1).dados.data='2030-03-09';
  assert.throws(()=>conferirCorrecoes(plano,registros));
});

test('v2 recusa faturas se a regra vigente mudar em parte do parcelamento',()=>{
  const {registros,plano}=exemploInclusao();
  try {
    definirFechamentos({versao:1,historico:[{vigencia:'2031-01-01',dia:14}]});
    assert.throws(()=>conferirCorrecoes(plano,registros));
  } finally { definirFechamentos({versao:0,historico:[]}); }
});

function exemploConciliacao() {
  const selecionar=r=>Object.fromEntries(CAMPOS_CORRECAO.map(k=>[k,r[k]]));
  const r={id:id(501),versao:2,tipo:'despesa',data:'2031-04-09',data_compra:'2031-03-15',descricao:'Compra fictícia',valor_centavos:101,meio:'Cartão de crédito',categoria:'Casa',grupo:null,parcela:1,parcelas:1};
  const novo={...selecionar(r),valor_centavos:200,data_compra:'2031-03-16'};
  const plano={formato:'gestao-da-feira-correcoes',versao_formato:3,totais_preservados:[],
    verificacoes:[{id:r.id,versao:2,campos:selecionar(r)},{id:id(502),versao:null,campos:null}],
    alteracoes:[{tabela:'financeiro_lancamentos',acao:'editar',id:r.id,versao:2,dados:{...selecionar(r),valor_centavos:100}},{tabela:'financeiro_lancamentos',acao:'inserir',id:id(502),versao:null,dados:novo}],
    conciliacoes:[{referencia:'Documento fictício',inicio:'2031-03-10',fim:'2031-04-09',total_centavos:300,completa:true,movimentos:[{id:r.id,data_compra:r.data_compra,valor_centavos:100,parcela:1,parcelas:1},{id:id(502),data_compra:novo.data_compra,valor_centavos:200,parcela:1,parcelas:1}]}]};
  return {registros:[r],plano};
}
test('v3 confere fatura completa e permite despesa à vista documentada sem tocar Pix/dinheiro',()=>{
  const {registros,plano}=exemploConciliacao();
  registros.push({...registros[0],id:id(503),meio:'Pix',data_compra:null});
  const antes=JSON.stringify(registros), r=conferirCorrecoes(plano,registros);
  assert.equal(r.insercoes,1);assert.equal(r.depois,300);assert.equal(JSON.stringify(registros),antes);
});
test('v3 rejeita divergência de soma, data, parcela, fechamento, inserção sem referência e extra na fatura completa',()=>{
  for(const alterar of [p=>p.conciliacoes[0].total_centavos++,p=>p.conciliacoes[0].movimentos[0].data_compra='2031-03-14',p=>p.conciliacoes[0].movimentos[0].parcela=2,p=>p.conciliacoes[0].inicio='2031-03-09',p=>p.conciliacoes[0].movimentos.pop(),p=>p.alteracoes[1].dados.meio='Pix']) {
    const {registros,plano}=exemploConciliacao();alterar(plano);assert.throws(()=>conferirCorrecoes(plano,registros));
  }
  const {registros,plano}=exemploConciliacao();registros.push({...registros[0],id:id(509)});assert.throws(()=>conferirCorrecoes(plano,registros));
});
test('v3 agrega movimentos da mesma compra, mas não duplica o valor do cadastro',()=>{
  const {registros,plano}=exemploConciliacao();const m=plano.conciliacoes[0].movimentos[0];
  m.valor_centavos=40;plano.conciliacoes[0].movimentos.push({...m,valor_centavos:60});
  assert.equal(conferirCorrecoes(plano,registros).depois,300);
  plano.conciliacoes[0].movimentos.push({...m});assert.throws(()=>conferirCorrecoes(plano,registros));
});
test('v3 não admite editar Pix/dinheiro, mudar valor ao reclassificar ou violar total confirmado',()=>{
  for(const meio of ['Pix','Dinheiro']) {
    const {registros,plano}=exemploConciliacao();registros[0].meio=meio;registros[0].data_compra=null;plano.verificacoes[0].campos={...plano.verificacoes[0].campos,meio,data_compra:null};
    assert.throws(()=>conferirCorrecoes(plano,registros));
  }
  const {registros,plano}=exemploConciliacao();plano.alteracoes[0].dados.meio='Outro';plano.alteracoes[0].dados.data_compra=null;assert.throws(()=>conferirCorrecoes(plano,registros));
  const e=exemploConciliacao();e.plano.totais_preservados=[{grupo:'grupo-ausente',total_centavos:100}];assert.throws(()=>conferirCorrecoes(e.plano,e.registros));
});
test('v3 recusa segunda aplicação, versão alterada e fechamento mudado',()=>{
  const {registros,plano}=exemploConciliacao();registros[0].versao++;assert.throws(()=>conferirCorrecoes(plano,registros));registros[0].versao--;
  const aplicados=conferirCorrecoes(plano,registros).operacoes.map(op=>({id:op.id,...op.dados,versao:op.versao===null?1:op.versao+1}));
  assert.throws(()=>conferirCorrecoes(plano,aplicados));
  try {definirFechamentos({versao:1,historico:[{vigencia:'2031-01-01',dia:14}]});assert.throws(()=>conferirCorrecoes(plano,registros));}
  finally {definirFechamentos({versao:0,historico:[]});}
});

test('v3 permite retirar empréstimo do cartão preservando o valor e recusa alteração do total de compra',()=>{
  const e=exemploConciliacao();
  const emprestimo={...e.registros[0],id:id(510),descricao:'Empréstimo fictício',valor_centavos:50};
  e.registros.push(emprestimo);
  const campos=r=>Object.fromEntries(CAMPOS_CORRECAO.map(k=>[k,r[k]]));
  e.plano.verificacoes.push({id:emprestimo.id,versao:emprestimo.versao,campos:campos(emprestimo)});
  e.plano.alteracoes.push({tabela:'financeiro_lancamentos',acao:'editar',id:emprestimo.id,versao:emprestimo.versao,dados:{...campos(emprestimo),meio:'Outro',data_compra:null}});
  assert.equal(conferirCorrecoes(e.plano,e.registros).operacoes.at(-1).dados.valor_centavos,50);
  e.plano.alteracoes.at(-1).dados.valor_centavos=49;assert.throws(()=>conferirCorrecoes(e.plano,e.registros));
  const f=exemplo();f.plano.versao_formato=3;
  f.plano.conciliacoes=[{referencia:'Documento fictício',inicio:'2026-10-10',fim:'2026-11-09',total_centavos:100,completa:true,movimentos:[{id:f.registros[1].id,data_compra:null,valor_centavos:100,parcela:2,parcelas:2}]}];
  f.plano.totais_preservados=[{grupo:f.registros[0].grupo,total_centavos:200}];
  assert.equal(conferirCorrecoes(f.plano,f.registros).exclusoes,2);
  f.plano.alteracoes[0].dados.valor_centavos=101;assert.throws(()=>conferirCorrecoes(f.plano,f.registros));
});
