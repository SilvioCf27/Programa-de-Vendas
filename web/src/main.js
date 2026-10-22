import { createClient } from '@supabase/supabase-js';
import { criarApi } from './api.js';
import { validarConfig } from './config.js';
import {
  hoje,
  mesFechamento,
  periodo,
  resumo,
  moeda,
  vendaFormulario,
  erroAmigavel,
} from './regras.js';
import './style.css';
import {
  montarExportacao,
  gerarCsv,
  gerarExcel,
  baixar,
} from './exportacao.js';
import { criarAtualizacao } from './atualizacao.js';
import { criarPainelAnalises } from './painel-analises.js';
import { criarPainelFinanceiro } from './painel-financeiro.js';

const $ = (id) => document.getElementById(id);
const form = $('venda');
const modal = $('formulario');
let cliente,
  api,
  sessao,
  registros = [],
  editando = null,
  carregando = false,
  gravando = false;
let selecao;
let exportando = false;
let geracao = 0;
const financeiro = criarPainelFinanceiro({
  api: () => api,
  sessao: () => sessao,
});
const analises = criarPainelAnalises({ api: () => api, sessao: () => sessao });
function mudarArea(area) {
  for (const nome of ['vendas', 'analises', 'financas']) {
    $('area-' + nome).hidden = nome !== area;
    $('aba-' + nome).setAttribute('aria-pressed', String(nome === area));
  }
  if (area === 'financas') financeiro.atualizar();
  if (area === 'analises') analises.atualizar();
}
$('aba-vendas').addEventListener('click', () => {
  mudarArea('vendas');
  carregar();
});
$('aba-analises').addEventListener('click', () => mudarArea('analises'));
$('aba-financas').addEventListener('click', () => mudarArea('financas'));
const referencia = mesFechamento();
$('ano').value = referencia.ano;
const meses = [
  'Janeiro',
  'Fevereiro',
  'Março',
  'Abril',
  'Maio',
  'Junho',
  'Julho',
  'Agosto',
  'Setembro',
  'Outubro',
  'Novembro',
  'Dezembro',
];
meses.forEach((mes, i) => $('mes').add(new Option(mes, i + 1)));
$('mes').value = referencia.mes;
const dataBr = (data) => data.split('-').reverse().join('/');
function mensagem(texto) {
  $('mensagem').textContent = texto;
}
function conexao() {
  $('rede').hidden = navigator.onLine;
  $('salvar').disabled = gravando || !navigator.onLine;
}
window.addEventListener('online', conexao);
window.addEventListener('offline', conexao);
conexao();
function controles() {
  $('mes').disabled = ['Ano', 'Todas'].includes($('tipo').value);
  $('ano').disabled = $('tipo').value === 'Todas';
}
$('tipo').addEventListener('change', controles);
controles();
function desenhar() {
  const indicadores = resumo(registros);
  $('total').textContent = moeda(indicadores.total);
  $('quantidade').textContent = indicadores.quantidade;
  $('media').textContent = moeda(indicadores.media);
  $('vazio').hidden = registros.length > 0;
  $('vendas').replaceChildren();
  for (const r of registros) {
    const item = document.createElement('li');
    item.className = 'painel registro';
    const linha = document.createElement('div');
    linha.className = 'titulo';
    const data = document.createElement('strong');
    data.textContent = dataBr(r.data);
    const total = document.createElement('strong');
    total.className = 'valor';
    total.textContent = moeda(
      Number(r.dinheiro_centavos) +
        Number(r.pix_centavos) +
        Number(r.cartao_centavos)
    );
    linha.append(data, total);
    const detalhe = document.createElement('p');
    detalhe.className = 'nota';
    detalhe.textContent = `Dinheiro ${moeda(r.dinheiro_centavos)} · Pix ${moeda(r.pix_centavos)} · Cartão ${moeda(r.cartao_centavos)}`;
    const acoes = document.createElement('div');
    acoes.className = 'acoes';
    const editar = document.createElement('button');
    editar.textContent = 'Editar';
    editar.addEventListener('click', () => abrir(r));
    const excluir = document.createElement('button');
    excluir.textContent = 'Excluir';
    excluir.className = 'perigo';
    excluir.addEventListener('click', async () => {
      if (gravando || !navigator.onLine)
        return mensagem('Conecte-se à internet antes de excluir.');
      if (!confirm(`Excluir a venda de ${dataBr(r.data)}?`)) return;
      gravando = true;
      excluir.disabled = true;
      try {
        await api.excluir(r);
        mensagem('Venda excluída.');
        await carregar();
      } catch (erro) {
        mensagem(erroAmigavel(erro));
      } finally {
        gravando = false;
        excluir.disabled = false;
      }
    });
    acoes.append(editar, excluir);
    item.append(linha, detalhe, acoes);
    $('vendas').append(item);
  }
}
async function carregar(novaSelecao = selecao) {
  if (!sessao || carregando) return false;
  if (!navigator.onLine)
    return mensagem(
      'Conecte-se para atualizar. A lista pode estar desatualizada.'
    );
  carregando = true;
  $('atualizar').disabled = true;
  $('filtros').querySelector('button').disabled = true;
  const atual = geracao;
  try {
    const linhas = await api.listar(novaSelecao);
    if (atual !== geracao || !sessao) return;
    registros = linhas;
    selecao = novaSelecao;
    $('periodo').textContent = selecao.inicio
      ? `${dataBr(selecao.inicio)} a ${dataBr(selecao.fim)}`
      : 'Todas as vendas';
    desenhar();
    return true;
  } catch (erro) {
    mensagem(`${erroAmigavel(erro)} A lista não foi atualizada.`);
    return false;
  } finally {
    carregando = false;
    $('atualizar').disabled = false;
    $('filtros').querySelector('button').disabled = false;
  }
}
// Mantém a seleção já aplicada; campos de filtros em preparação não são lidos.
const atualizacao = criarAtualizacao({
  disponivel: () =>
    document.visibilityState === 'visible' &&
    navigator.onLine &&
    sessao &&
    !$('conteudo').hidden,
  ocupado: () =>
    carregando ||
    exportando ||
    gravando ||
    modal.open ||
    financeiro.ocupado() ||
    analises.ocupado(),
  atualizar: () =>
    !$('area-financas').hidden
      ? financeiro.atualizar()
      : !$('area-analises').hidden
        ? analises.atualizar()
        : carregar(),
  informar: (sucesso) => {
    $('atualizacao-web').textContent = sucesso
      ? `Conferido às ${new Date().toLocaleTimeString('pt-BR')}. Nova consulta em cerca de 1 minuto.`
      : 'Não foi possível conferir a nuvem. Tentaremos novamente em cerca de 1 minuto.';
  },
});
window.addEventListener('focus', () => atualizacao.verificar());
window.addEventListener('online', () => atualizacao.verificar());
document.addEventListener('visibilitychange', () => atualizacao.verificar());
$('filtros').addEventListener('submit', (event) => {
  event.preventDefault();
  mensagem('');
  try {
    carregar(periodo($('tipo').value, $('ano').value, $('mes').value));
  } catch (erro) {
    mensagem(erro.message);
  }
});
$('atualizar').addEventListener('click', () => {
  mensagem('');
  carregar();
});
function abrir(registro = null) {
  editando = registro;
  form.reset();
  $('erro-venda').textContent = '';
  form.elements.data.value = registro?.data ?? hoje();
  for (const campo of ['dinheiro', 'pix', 'cartao'])
    form.elements[campo].value = registro
      ? (Number(registro[`${campo}_centavos`]) / 100)
          .toFixed(2)
          .replace('.', ',')
      : '';
  $('titulo-form').textContent = registro ? 'Editar venda' : 'Nova venda';
  conexao();
  modal.showModal();
}
async function exportarVendas(formato) {
  if (!sessao || !selecao || carregando || exportando) return;
  const conta = sessao.user.id;
  const relatorio = montarExportacao(registros, selecao);
  exportando = true;
  $('exportar-csv').disabled = $('exportar-excel').disabled = true;
  try {
    const blob =
      formato === 'csv'
        ? new Blob([gerarCsv(relatorio)], { type: 'text/csv;charset=utf-8' })
        : await gerarExcel(relatorio);
    if (sessao?.user.id !== conta) return;
    baixar(blob, `vendas-filtradas.${formato}`);
    mensagem(
      'Arquivo gerado. Confira a pasta Downloads ou a opção de compartilhar do navegador.'
    );
  } catch {
    if (sessao?.user.id === conta)
      mensagem(
        'Não foi possível gerar o arquivo. Confira a conexão para carregar a exportação Excel e tente novamente.'
      );
  } finally {
    exportando = false;
    $('exportar-csv').disabled = $('exportar-excel').disabled = false;
  }
}
$('exportar-csv').addEventListener('click', () => exportarVendas('csv'));
$('exportar-excel').addEventListener('click', () => exportarVendas('xlsx'));
$('nova').addEventListener('click', () => abrir());
function fechar() {
  if (!gravando) modal.close();
}
$('fechar-form').addEventListener('click', fechar);
$('cancelar').addEventListener('click', fechar);
modal.addEventListener('cancel', (e) => {
  if (gravando) e.preventDefault();
});
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (gravando) return;
  if (!navigator.onLine) {
    $('erro-venda').textContent = 'Conecte-se à internet para salvar.';
    return;
  }
  let dados;
  try {
    dados = vendaFormulario(Object.fromEntries(new FormData(form)));
  } catch (erro) {
    $('erro-venda').textContent = erro.message;
    return;
  }
  gravando = true;
  conexao();
  $('erro-venda').textContent = '';
  try {
    await api.salvar(dados, editando);
    modal.close();
    mensagem('Venda salva.');
    await carregar();
  } catch (erro) {
    $('erro-venda').textContent = erroAmigavel(erro);
  } finally {
    gravando = false;
    conexao();
  }
});
async function receberSessao(nova) {
  atualizacao.parar();
  const mudouConta = sessao?.user.id !== nova?.user.id;
  sessao = nova;
  geracao++;
  if (mudouConta) {
    financeiro.limpar();
    analises.limpar();
    mudarArea('vendas');
    registros = [];
    desenhar();
    modal.close();
    $('conteudo').hidden = true;
    $('acesso').hidden = false;
  }
  $('sair').hidden = !nova;
  if (!nova) {
    $('atualizacao-web').textContent = '';
    registros = [];
    desenhar();
    modal.close();
    $('conteudo').hidden = true;
    $('sair').hidden = true;
    $('acesso').hidden = false;
    return;
  }
  try {
    const autorizada = await api.autorizado();
    if (sessao !== nova) return;
    if (!autorizada) {
      mensagem('Esta conta não está autorizada. Confira a conta de acesso.');
      return;
    }
    $('acesso').hidden = true;
    $('conteudo').hidden = false;
    $('sair').hidden = false;
    selecao ??= periodo($('tipo').value, $('ano').value, $('mes').value);
    await carregar();
    if (sessao === nova) atualizacao.iniciar();
  } catch {
    mensagem(
      'Não foi possível acessar os dados. Confira a conexão e tente entrar novamente.'
    );
  }
}
$('login').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!cliente || !navigator.onLine) return;
  const botao = $('login').querySelector('button');
  botao.disabled = true;
  mensagem('');
  try {
    const { error } = await cliente.auth.signInWithPassword({
      email: event.target.elements.email.value.trim(),
      password: event.target.elements.senha.value,
    });
    if (error)
      mensagem(
        'Não foi possível entrar. Confira o e-mail, a senha e a conexão.'
      );
    else event.target.elements.senha.value = '';
  } catch {
    mensagem('Não foi possível entrar. Confira a conexão e tente novamente.');
  } finally {
    botao.disabled = false;
  }
});
$('sair').addEventListener('click', async () => {
  const { error } = await cliente.auth.signOut({ scope: 'local' });
  if (error)
    mensagem('Não foi possível sair. Confira a conexão e tente novamente.');
  else mensagem('Você saiu da sua conta.');
});
try {
  const url = import.meta.env.VITE_SUPABASE_URL;
  const chave = import.meta.env.VITE_SUPABASE_ANON_KEY;
  if (validarConfig(url, chave)) {
    cliente = createClient(url, chave);
    api = criarApi(cliente);
    cliente.auth.onAuthStateChange((_evento, nova) => {
      setTimeout(() => receberSessao(nova), 0);
    });
    $('login').querySelector('fieldset').disabled = false;
  } else throw Error('configuração ausente');
} catch {
  $('login')
    .querySelectorAll('input, button')
    .forEach((el) => {
      el.disabled = true;
    });
  mensagem(
    'O acesso online ainda está sendo preparado. Esta versão não está conectada aos seus dados.'
  );
}
if ('serviceWorker' in navigator && import.meta.env.PROD)
  navigator.serviceWorker.register('/sw.js').catch(() => {});
