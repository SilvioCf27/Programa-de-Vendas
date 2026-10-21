import { hoje, mesFechamento, moeda } from './regras.js';
import {
  limitesAnalise,
  anterior,
  selecionar,
  indicadores,
  comparar,
  formas,
} from './analises.js';
const $ = (id) => document.getElementById(id);
const br = (data) => data.split('-').reverse().join('/');
const descrever = (p) =>
  p.inicio ? `${br(p.inicio)} a ${br(p.fim)}` : 'Todas as vendas';
const percentual = (v) =>
  v.toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + '%';
function linha(tabela, valores) {
  const tr = document.createElement('tr');
  valores.forEach((valor, i) => {
    const td = document.createElement(i ? 'td' : 'th');
    if (!i) td.scope = 'row';
    td.textContent = valor;
    tr.append(td);
  });
  tabela.append(tr);
}
export function criarPainelAnalises({ api, sessao }) {
  let selecao = null,
    comparacao = null,
    ocupado = false,
    geracao = 0;
  const ref = mesFechamento();
  const data = `${ref.ano}-${String(ref.mes).padStart(2, '0')}-10`;
  for (const prefixo of ['ana', 'cmp-a', 'cmp-b']) {
    $(prefixo + '-referencia').value =
      prefixo === 'cmp-a'
        ? anterior('Fechamento', limitesAnalise('Fechamento', data)).inicio
        : data;
    $(prefixo + '-fim').value = hoje();
    const ajustar = () => {
      const tipo = $(prefixo + '-tipo').value;
      $(prefixo + '-referencia').disabled = tipo === 'Todas';
      $(prefixo + '-fim-rotulo').hidden = tipo !== 'Intervalo';
      $(prefixo + '-fim').disabled = tipo !== 'Intervalo';
    };
    $(prefixo + '-tipo').addEventListener('change', ajustar);
    ajustar();
  }
  const ler = (p) =>
    limitesAnalise(
      $(p + '-tipo').value,
      $(p + '-referencia').value,
      $(p + '-fim').value
    );
  function desenhar(vendas) {
    const atual = selecionar(vendas, selecao.periodo);
    const r = indicadores(atual);
    $('ana-periodo').textContent = descrever(selecao.periodo);
    for (const campo of ['total', 'quantidade', 'media'])
      $('ana-' + campo).textContent =
        campo === 'quantidade' ? r[campo] : moeda(r[campo]);
    $('ana-vazio').hidden = !!r.quantidade;
    $('ana-pagamentos').replaceChildren();
    formas.forEach((forma, i) =>
      linha($('ana-pagamentos'), [
        forma,
        moeda(r.pagamentos[i]),
        r.total ? percentual((r.pagamentos[i] * 100) / r.total) : '—',
      ])
    );
    $('ana-semana').replaceChildren();
    r.porDia.forEach((dia) =>
      linha($('ana-semana'), [
        dia.nome,
        dia.quantidade,
        moeda(dia.total),
        moeda(dia.media),
      ])
    );
    const antes = anterior(selecao.tipo, selecao.periodo);
    if (antes) {
      const c = comparar(selecionar(vendas, antes), atual);
      $('ana-anterior').textContent =
        `Anterior (${descrever(antes)}): ${moeda(c.a.total)} em ${c.a.quantidade} dias. Diferença: ${moeda(c.diferenca)}. ` +
        (c.motivo || `Variação: ${percentual(c.variacao)}.`);
    } else
      $('ana-anterior').textContent =
        'Selecione Mês, Ano ou Fechamento para comparar com o período anterior.';
    if (comparacao) {
      const c = comparar(
        selecionar(vendas, comparacao.a),
        selecionar(vendas, comparacao.b)
      );
      $('cmp-periodo-a').textContent = descrever(comparacao.a);
      $('cmp-periodo-b').textContent = descrever(comparacao.b);
      $('cmp-resultado').hidden = false;
      $('cmp-valores').replaceChildren();
      linha($('cmp-valores'), [
        'Total bruto',
        moeda(c.a.total),
        moeda(c.b.total),
      ]);
      linha($('cmp-valores'), [
        'Dias de feira',
        c.a.quantidade,
        c.b.quantidade,
      ]);
      linha($('cmp-valores'), [
        'Média por dia',
        moeda(c.a.media),
        moeda(c.b.media),
      ]);
      formas.forEach((forma, i) =>
        linha($('cmp-valores'), [
          forma,
          moeda(c.a.pagamentos[i]),
          moeda(c.b.pagamentos[i]),
        ])
      );
      $('cmp-diferenca').textContent =
        `B − A: ${moeda(c.diferenca)}. ` +
        (c.motivo || `Variação: ${percentual(c.variacao)}.`);
    }
  }
  function controles() {
    for (const botao of $('area-analises').querySelectorAll('button'))
      botao.disabled = ocupado;
  }
  async function atualizar(nova = selecao, novaComparacao = comparacao) {
    if (!sessao() || ocupado || !navigator.onLine) return false;
    const conta = sessao().user.id,
      atual = geracao;
    ocupado = true;
    controles();
    $('ana-status').textContent = 'Consultando análises…';
    try {
      const consulta = nova || {
        tipo: $('ana-tipo').value,
        periodo: ler('ana'),
      };
      const dados = await api().financeiro();
      if (atual !== geracao || conta !== sessao()?.user.id) return false;
      selecao = consulta;
      comparacao = novaComparacao;
      desenhar(dados.vendas);
      $('ana-status').textContent = '';
      return true;
    } catch {
      if (atual === geracao)
        $('ana-status').textContent =
          'Não foi possível atualizar as análises. Confira a conexão.';
      return false;
    } finally {
      if (atual === geracao) {
        ocupado = false;
        controles();
      }
    }
  }
  $('ana-filtros').addEventListener('submit', (e) => {
    e.preventDefault();
    try {
      atualizar({ tipo: $('ana-tipo').value, periodo: ler('ana') });
    } catch (erro) {
      $('ana-status').textContent = erro.message;
    }
  });
  $('cmp-form').addEventListener('submit', (e) => {
    e.preventDefault();
    try {
      atualizar(selecao, { a: ler('cmp-a'), b: ler('cmp-b') });
    } catch (erro) {
      $('ana-status').textContent = erro.message;
    }
  });
  $('ana-atualizar').addEventListener('click', () => atualizar());
  return {
    atualizar,
    ocupado: () => ocupado,
    limpar() {
      geracao++;
      ocupado = false;
      selecao = comparacao = null;
      for (const id of ['ana-pagamentos', 'ana-semana', 'cmp-valores'])
        $(id).replaceChildren();
      for (const campo of ['total', 'quantidade', 'media'])
        $('ana-' + campo).textContent = '—';
      for (const id of [
        'ana-periodo',
        'ana-anterior',
        'ana-status',
        'cmp-periodo-a',
        'cmp-periodo-b',
        'cmp-diferenca',
      ])
        $(id).textContent = '';
      $('cmp-resultado').hidden = true;
      controles();
    },
  };
}
