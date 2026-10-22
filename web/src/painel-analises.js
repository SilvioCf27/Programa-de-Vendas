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
  $('ana-referencia').value = data;
  $('ana-fim').value = hoje();
  const ajustarAnalise = () => {
    const tipo = $('ana-tipo').value;
    $('ana-referencia').disabled = tipo === 'Todas';
    $('ana-fim-rotulo').hidden = tipo !== 'Intervalo';
    $('ana-fim').disabled = tipo !== 'Intervalo';
  };
  $('ana-tipo').addEventListener('change', ajustarAnalise);
  ajustarAnalise();
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
  const hojeData = hoje();
  const anoAtual = Number(hojeData.slice(0, 4));
  const mesAtual = Number(hojeData.slice(5, 7));
  const anoAnterior = mesAtual === 1 ? anoAtual - 1 : anoAtual;
  const mesAnterior = mesAtual === 1 ? 12 : mesAtual - 1;
  function atualizarAnos(vendas = []) {
    const anos = new Set([anoAtual - 1, anoAtual, anoAtual + 1]);
    vendas.forEach((v) => anos.add(Number(v.data.slice(0, 4))));
    for (const p of ['cmp-a', 'cmp-b']) {
      const campo = $(p + '-ano'),
        escolhido = campo.value;
      if (escolhido) anos.add(Number(escolhido));
    }
    for (const p of ['cmp-a', 'cmp-b']) {
      const campo = $(p + '-ano'),
        escolhido = campo.value;
      campo.replaceChildren(
        ...[...anos].sort((a, b) => a - b).map((ano) => new Option(ano, ano))
      );
      if (escolhido) campo.value = escolhido;
    }
  }
  atualizarAnos();
  for (const p of ['cmp-a', 'cmp-b']) {
    const inicial =
      p === 'cmp-a'
        ? `${anoAnterior}-${String(mesAnterior).padStart(2, '0')}-01`
        : hojeData;
    meses.forEach((mes, i) => $(p + '-mes').add(new Option(mes, i + 1)));
    $(p + '-mes').value = Number(inicial.slice(5, 7));
    $(p + '-ano').value = inicial.slice(0, 4);
    $(p + '-referencia').value = inicial;
    $(p + '-fim').value = inicial;
    const ajustar = () => {
      const tipo = $(p + '-tipo').value;
      const datas = ['Data', 'Intervalo'].includes(tipo);
      $(p + '-mes-ano').hidden = datas;
      $(p + '-datas').hidden = !datas;
      $(p + '-mes').disabled = $(p + '-ano').disabled = datas;
      $(p + '-referencia').disabled = !datas;
      $(p + '-inicio-rotulo').textContent =
        tipo === 'Intervalo' ? 'De' : 'Data';
      $(p + '-fim-rotulo').hidden = tipo !== 'Intervalo';
      $(p + '-fim').disabled = tipo !== 'Intervalo';
    };
    $(p + '-tipo').addEventListener('change', ajustar);
    ajustar();
  }
  const ler = (p) => {
    const tipo = $(p + '-tipo').value;
    const mensal = p !== 'ana' && ['Mês', 'Fechamento'].includes(tipo);
    const referencia = mensal
      ? `${$(p + '-ano').value}-${String($(p + '-mes').value).padStart(2, '0')}-01`
      : $(p + '-referencia').value;
    return limitesAnalise(tipo, referencia, $(p + '-fim').value);
  };
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
      atualizarAnos(dados.vendas);
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
