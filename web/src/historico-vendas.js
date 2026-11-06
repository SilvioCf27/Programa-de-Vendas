import { moeda } from './regras.js';
import { dias } from './analises.js';

export const diaDaSemana = (data) =>
  (new Date(`${data}T12:00:00Z`).getUTCDay() + 6) % 7;
export function filtrarDias(registros, selecionados = []) {
  return selecionados.length
    ? registros.filter((r) => selecionados.includes(diaDaSemana(r.data)))
    : registros;
}
const normalizar = (texto) => String(texto).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
export function paginaHistorico(registros, busca = '', pagina = 1, tamanho = 12) {
  const termo = normalizar(busca);
  const encontrados = registros.filter((r) => {
    const valores = ['dinheiro', 'pix', 'cartao'].map((p) => Number(r[`${p}_centavos`]));
    const total = valores.reduce((a, b) => a + b, 0);
    return normalizar([
      r.data, r.data.split('-').reverse().join('/'), dias[diaDaSemana(r.data)],
      ...[...valores, total].flatMap((v) => [moeda(v), (v / 100).toFixed(2), (v / 100).toFixed(2).replace('.', ',')]),
    ].join(' ')).includes(termo);
  }).sort((a, b) => b.data.localeCompare(a.data));
  const paginas = Math.max(1, Math.ceil(encontrados.length / tamanho));
  const atual = Math.max(1, Math.min(paginas, pagina));
  const inicio = (atual - 1) * tamanho;
  return { registros: encontrados.slice(inicio, inicio + tamanho), pagina: atual, paginas,
    quantidade: encontrados.length, inicio: encontrados.length ? inicio + 1 : 0,
    fim: Math.min(inicio + tamanho, encontrados.length) };
}
