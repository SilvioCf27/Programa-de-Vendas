import { hoje, dataValida } from './regras.js';
import { limitesFinanceiros } from './financeiro.js';

export const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const iso = (d) => d.toISOString().slice(0, 10);
const br = (d) => d.split('-').reverse().join('/');

export function semanasDoMes(ano, mes) {
  const primeira = `${ano}-${String(mes).padStart(2, '0')}-01`;
  if (!dataValida(primeira)) throw Error('Confira o mês e o ano.');
  const ultima = new Date(`${primeira}T12:00:00Z`);
  ultima.setUTCMonth(ultima.getUTCMonth() + 1);
  ultima.setUTCDate(0);
  const d = new Date(limitesFinanceiros('Semana', primeira).inicio + 'T12:00:00Z');
  const resultado = [];
  while (d <= ultima) {
    resultado.push(limitesFinanceiros('Semana', iso(d)));
    d.setUTCDate(d.getUTCDate() + 7);
  }
  return resultado;
}

export function criarSeletorFinanceiro(prefixo = 'fin', mudou = () => {}) {
  const $ = (id) => document.getElementById(prefixo + '-' + id);
  const tipo = $('tipo'), ano = $('ano'), mes = $('mes');
  const semana = $('semana'), referencia = $('referencia');
  const [a, m] = referencia.value.split('-');
  ano.value = a;
  MESES.forEach((nome, i) => mes.add(new Option(nome, String(i + 1))));
  mes.value = String(Number(m));
  function atualizar(alvo) {
    const mostrarSemana = tipo.value === 'Semana';
    $('mes-rotulo').hidden = tipo.value === 'Ano';
    $('semana-rotulo').hidden = !mostrarSemana;
    semana.disabled = !mostrarSemana;
    mes.disabled = tipo.value === 'Ano';
    try {
      const inicio = `${ano.value}-${String(mes.value).padStart(2, '0')}-01`;
      if (!dataValida(inicio)) throw Error('Confira o mês e o ano.');
      if (mostrarSemana) {
        const anterior = typeof alvo === 'string' ? alvo : semana.value || hoje();
        const semanas = semanasDoMes(Number(ano.value), Number(mes.value));
        semana.replaceChildren(...semanas.map((s) => new Option(
          `${br(s.inicio)} a ${br(s.fim)}`, s.inicio)));
        semana.value = (semanas.find((s) => s.inicio <= anterior && s.fim >= anterior) || semanas[0]).inicio;
        referencia.value = semana.value;
      } else referencia.value = inicio;
    } catch {
      referencia.value = '';
      semana.replaceChildren();
    }
    mudou();
  }
  for (const campo of [tipo, mes, ano]) campo.addEventListener('change', atualizar);
  semana.addEventListener('change', () => { referencia.value = semana.value; mudou(); });
  atualizar();
  return { atualizar, definir(data) {
    if (!dataValida(data)) throw Error('Informe uma data válida.');
    ano.value = data.slice(0, 4); mes.value = String(Number(data.slice(5, 7))); atualizar(data);
  } };
}
