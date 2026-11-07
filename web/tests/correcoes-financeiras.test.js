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
