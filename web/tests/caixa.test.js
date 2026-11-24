import test from 'node:test';
import assert from 'node:assert/strict';
import {calcularCaixa,movimentoCaixaFormulario} from '../src/caixa.js';
const movimento=(r={})=>({id:'a',tipo:'abertura',data:'2020-01-01',descricao:'Posição inicial',conta:null,valor_centavos:null,dinheiro_centavos:10000,conta_centavos:20000,cancelado:false,created_at:'2020-01-01T00:00:00Z',...r});
const snapshot=()=>({movimentos:[movimento()],vendas:[],despesas:[]});
test('posição ao fim do dia evita somar novamente o dinheiro já contado; independente do período',()=>{
 const s=snapshot();s.vendas=[{data:'2020-01-01',dinheiro_centavos:100000,pix_centavos:100000},{data:'2020-01-02',dinheiro_centavos:1200,pix_centavos:3400,cartao_centavos:99999},{data:'2020-01-04',dinheiro_centavos:999,pix_centavos:999}];
 const r=calcularCaixa(s,'2020-01-03');assert.equal(r.dinheiro,11200);assert.equal(r.conta,23400);assert.equal(r.total,34600);assert.equal(calcularCaixa(s,'2019-12-31'),null);
});
test('dinheiro/Pix saem automaticamente; compras no cartão, taxas e Outro não duplicam movimentos de conta',()=>{
 const s=snapshot();s.despesas=[['Dinheiro',1000],['Pix',2000],['Cartão de crédito',5000],['Outro',100]].map(([meio,valor_centavos])=>({tipo:'despesa',meio,valor_centavos,data:'2020-01-02'}));s.despesas.push({tipo:'taxa',meio:'Cartão de crédito',data:'2020-01-02',valor_centavos:999});
 s.movimentos.push(movimento({id:'b',tipo:'entrada',data:'2020-01-02',conta:'conta',valor_centavos:4900,dinheiro_centavos:null,conta_centavos:null}),movimento({id:'c',tipo:'saida',data:'2020-01-03',conta:'conta',valor_centavos:5000,dinheiro_centavos:null,conta_centavos:null}));
 const r=calcularCaixa(s,'2020-01-03');assert.equal(r.dinheiro,9000);assert.equal(r.conta,17900);assert.equal(r.outros,1);
});
test('transferências preservam o total; conferência não redefine saldo nem esconde a diferença',()=>{
 const s=snapshot();s.movimentos.push(movimento({id:'b',tipo:'transferencia',data:'2020-01-02',conta:'dinheiro',valor_centavos:4000,dinheiro_centavos:null,conta_centavos:null}),movimento({id:'c',tipo:'conferencia',data:'2020-01-03',dinheiro_centavos:6500,conta_centavos:24500}));
 const r=calcularCaixa(s,'2020-01-03');assert.equal(r.total,30000);assert.equal(r.dinheiro,6000);assert.equal(r.conta,24000);assert.equal(r.conferencias[0].diferenca_dinheiro,500);assert.equal(r.conferencias[0].diferenca_conta,500);
 s.movimentos[1].cancelado=true;assert.equal(calcularCaixa(s,'2020-01-03').dinheiro,10000);
});
test('formulário aceita zero na posição inicial e centavos exatos; rejeita valores inválidos',()=>{
 const r=movimentoCaixaFormulario({tipo:'abertura',data:'2020-01-01',descricao:'Inicial',dinheiro:'0,00',saldo_conta:'1.234,56'},'a');assert.equal(r.conta_centavos,123456);assert.equal(r.dinheiro_centavos,0);
 for(const valor of ['0','-1','1,234'])assert.throws(()=>movimentoCaixaFormulario({tipo:'entrada',data:'2020-01-02',descricao:'Teste',conta:'conta',valor},'b'));
});
test('snapshot incompleto ou duas aberturas não vira saldo aparentemente correto',()=>{
 assert.throws(()=>calcularCaixa({},'2020-01-01'));
 const s=snapshot();s.movimentos.push(movimento({id:'b'}));assert.throws(()=>calcularCaixa(s,'2020-01-02'));
 s.movimentos=[];assert.equal(calcularCaixa(s,'2020-01-02'),null);
});
