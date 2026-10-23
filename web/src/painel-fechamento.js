import { proporFechamento, periodoFechamento, diaNoMes } from './fechamento.js';
import { MESES } from './seletor-financeiro.js';
const $ = id => document.getElementById(id);
const br = d => d.split('-').reverse().join('/');

export function criarConfiguracaoFechamento({ api, sessao, aoSalvar }) {
  let config = null, enviando = false, geracao = 0;
  const modal = $('fechamento-dialogo');
  const form = $('fechamento-form');
  for (let dia = 1; dia <= 31; dia++) $('fechamento-dia').add(new Option(String(dia), String(dia)));
  MESES.forEach((mes, i) => $('fechamento-mes').add(new Option(mes, String(i + 1))));
  function controles() {
    for (const campo of form.querySelectorAll('input, select, button')) campo.disabled = enviando;
  }
  function parametros() {
    return { vigencia: `${$('fechamento-ano').value}-${String($('fechamento-mes').value).padStart(2, '0')}-01`, dia: Number($('fechamento-dia').value) };
  }
  function previa() {
    if (!config) return;
    try {
      const { vigencia, dia } = parametros();
      const proposta = proporFechamento(config, vigencia, dia);
      const [ano, mes] = vigencia.split('-').map(Number);
      const antes = new Date(Date.UTC(ano, mes - 2, 1));
      const periodos = [periodoFechamento(antes.getUTCFullYear(), antes.getUTCMonth() + 1, proposta.historico), periodoFechamento(ano, mes, proposta.historico)];
      $('fechamento-previa').textContent = 'Prévia dos períodos: ' + periodos.map(p => `${br(p.inicio)} a ${br(p.fim)}`).join(' · ');
      $('fechamento-erro').textContent = '';
    } catch (erro) { $('fechamento-previa').textContent = ''; $('fechamento-erro').textContent = erro.message; }
  }
  form.addEventListener('change', previa);
  $('fin-configurar-fechamento').addEventListener('click', async () => {
    if (!sessao() || enviando) return;
    const uid = sessao().user.id, atual = ++geracao;
    config = null; enviando = true; controles();
    $('fechamento-erro').textContent = 'Consultando a regra compartilhada…';
    $('fechamento-previa').textContent = ''; $('fechamento-historico').replaceChildren();
    modal.showModal();
    try {
      config = await api().fechamentos();
      if (atual !== geracao || sessao()?.user.id !== uid) return;
      if (!config) throw Error('Conclua a atualização da estrutura da nuvem para configurar o fechamento.');
      const hoje = new Date(), proximo = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 1);
      $('fechamento-ano').value = proximo.getFullYear();
      $('fechamento-mes').value = String(proximo.getMonth() + 1);
      $('fechamento-dia').value = diaNoMes(proximo.getFullYear(), proximo.getMonth() + 1, config.historico);
      for (const r of [{ vigencia: 'Regra inicial', dia: 9 }, ...config.historico]) {
        const item = document.createElement('li');
        item.textContent = `${r.vigencia}: dia ${String(r.dia).padStart(2, '0')}`;
        $('fechamento-historico').append(item);
      }
      previa();
    } catch (erro) { if (atual === geracao) $('fechamento-erro').textContent = erro.message || 'Não foi possível consultar o fechamento.'; }
    finally { if (atual === geracao) { enviando = false; controles(); $('fechamento-salvar').disabled = !config; } }
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!config || enviando || !sessao()) return;
    try {
      const { vigencia, dia } = parametros(); proporFechamento(config, vigencia, dia);
      enviando = true; controles();
      await api().salvarFechamento(config.versao, vigencia, dia);
      modal.close();
      await aoSalvar();
    } catch (erro) {
      $('fechamento-erro').textContent = erro.code === '40001' ? 'A regra mudou em outro dispositivo. Feche e consulte novamente.' : erro.message || 'Não foi possível salvar o fechamento.';
    } finally { enviando = false; controles(); }
  });
  $('fechamento-cancelar').addEventListener('click', () => { if (!enviando) modal.close(); });
  modal.addEventListener('cancel', event => { if (enviando) event.preventDefault(); });
  return { ocupado: () => modal.open || enviando, limpar() { geracao++; enviando = false; config = null; modal.close(); } };
}
