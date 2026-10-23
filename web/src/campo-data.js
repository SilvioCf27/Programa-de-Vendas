import { dataValida } from './regras.js';
import { MESES } from './seletor-financeiro.js';

export function criarCampoData({ valor, dia, mes, ano, resumo, mudou = () => {} }) {
  MESES.forEach((nome, i) => mes.add(new Option(nome, String(i + 1))));
  function atualizar() {
    const anterior = Number(dia.value || 1);
    const primeiro = `${ano.value}-${String(mes.value).padStart(2, '0')}-01`;
    if (!dataValida(primeiro)) {
      valor.value = '';
      resumo.textContent = 'Confira o ano informado.';
      mudou();
      return;
    }
    const ultima = new Date(primeiro + 'T12:00:00Z');
    ultima.setUTCMonth(ultima.getUTCMonth() + 1); ultima.setUTCDate(0);
    dia.replaceChildren(...Array.from({ length: ultima.getUTCDate() }, (_, i) => new Option(String(i + 1), String(i + 1))));
    dia.value = String(Math.min(anterior, ultima.getUTCDate()));
    valor.value = `${ano.value}-${String(mes.value).padStart(2, '0')}-${String(dia.value).padStart(2, '0')}`;
    resumo.textContent = `Data selecionada: ${valor.value.split('-').reverse().join('/')}.`;
    mudou();
  }
  for (const campo of [dia, mes, ano]) campo.addEventListener('change', atualizar);
  ano.addEventListener('input', atualizar);
  return {
    limpar() { valor.value = ''; dia.value = ''; mes.value = ''; ano.value = ''; resumo.textContent = 'Informe a data original da compra.'; mudou(); },
    definir(data) {
      if (!dataValida(data)) throw Error('Informe uma data válida.');
      const [a, m, d] = data.split('-').map(Number);
      ano.value = String(a); mes.value = String(m);
      dia.replaceChildren(new Option(String(d), String(d)));
      atualizar();
    },
  };
}
