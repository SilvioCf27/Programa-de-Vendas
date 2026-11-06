import { moeda } from './regras.js';
import { dias } from './analises.js';
import { diaDaSemana } from './historico-vendas.js';

export function dataDaCompra(r) {
  return r.data_compra || (r.tipo === 'despesa' && r.meio !== 'Cartão de crédito' ? r.data : null);
}
const normalizar = (s) => String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
export function historicoFinanceiro(registros, busca = '') {
  const termo = normalizar(busca);
  return registros.filter((r) => {
    const datas = [dataDaCompra(r), r.data].filter(Boolean);
    const texto = [r.descricao, r.meio, r.categoria, r.tipo === 'taxa' ? 'taxa das vendas no cartão' : 'despesa',
      r.parcelas > 1 ? `parcela ${r.parcela}/${r.parcelas}` : '',
      ...datas.flatMap(d => [d, d.split('-').reverse().join('/'), dias[diaDaSemana(d)]]),
      moeda(r.valor_centavos), (r.valor_centavos / 100).toFixed(2), (r.valor_centavos / 100).toFixed(2).replace('.', ',')];
    return normalizar(texto.join(' ')).includes(termo);
  }).sort((a, b) => {
    const data = r => dataDaCompra(r) || (r.tipo === 'taxa' ? r.data : '');
    return data(b).localeCompare(data(a)) || b.data.localeCompare(a.data) || String(a.id).localeCompare(String(b.id));
  });
}
