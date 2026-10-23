import { criarConfiguracaoFechamento } from './painel-fechamento.js';
import { criarCampoData } from './campo-data.js';
import { criarSeletorFinanceiro } from './seletor-financeiro.js';
import { hoje, mesFechamento, moeda } from './regras.js';
import {
  compraDoLancamento,
  limitesFinanceiros,
  taxasSemanaFormulario,
  resumoFinanceiro,
  lancamentoFormulario,
  anualFormulario,
  erroFinanceiro,
  recusaConfirmada,
} from './financeiro.js';
const $ = (id) => document.getElementById(id);
const br = (data) => data.split('-').reverse().join('/');
const texto = (tag, conteudo, classe = '') => {
  const e = document.createElement(tag);
  e.textContent = conteudo;
  e.className = classe;
  return e;
};
export function criarPainelFinanceiro({ api, sessao, aoFechamentoAlterado = () => {} }) {
  let dados = null,
    selecao = null,
    ocupado = false,
    geracao = 0,
    editando = null,
    anual = null;
  const ref = mesFechamento();
  $('fin-referencia').value =
    `${ref.ano}-${String(ref.mes).padStart(2, '0')}-10`;
  const seletorFinanceiro = criarSeletorFinanceiro();
  const campoData = criarCampoData({
    valor: $('fin-form').elements.data,
    dia: $('fin-data-dia'), mes: $('fin-data-mes'), ano: $('fin-data-ano'),
    resumo: $('fin-data-confirmada'), mudou: atualizarPrevia,
  });
  $('taxas-referencia').value = hoje();
  const seletorTaxas = criarSeletorFinanceiro('taxas', desenharTaxas);
  const dialogo = (prefixo) => $(prefixo + '-dialogo');
  const configuracaoFechamento = criarConfiguracaoFechamento({ api, sessao, aoSalvar: async () => { aoFechamentoAlterado(); await atualizar(); } });
  const chave = (uid) => `feira-financeiro-pendente:${uid}`;
  function pendente(uid = sessao()?.user.id) {
    if (!uid) return null;
    const valor = sessionStorage.getItem(chave(uid));
    return valor ? JSON.parse(valor) : null;
  }
  function controles() {
    let pendencia = false;
    try {
      pendencia = !!pendente();
    } catch {
      pendencia = true;
    }
    const offline = !navigator.onLine;
    for (const e of $('fin-dados').querySelectorAll('button'))
      e.disabled = ocupado || offline || pendencia;
    $('fin-atualizar').disabled = ocupado || offline;
    $('fin-consultar').disabled = ocupado || offline;
    $('fin-configurar-fechamento').disabled = ocupado || offline || pendencia;
    for (const prefixo of ['fin', 'anual', 'taxas']) {
      const form = $(prefixo + '-form');
      for (const e of form.querySelectorAll('input,select'))
        e.disabled = ocupado || pendencia || e.dataset.somenteLeitura === '1';
      if (prefixo === 'fin' && !ocupado && !pendencia)
        form.elements.parcelas.disabled =
          form.elements.tipo.value === 'taxa';
      $(prefixo + '-salvar').disabled = ocupado || offline;
      $(prefixo + '-salvar').textContent = pendencia
        ? 'Confirmar envio'
        : prefixo === 'fin'
          ? $('fin-form').elements.tipo.value === 'taxa' ? 'Salvar taxa' : 'Salvar compra'
          : prefixo === 'taxas' ? 'Salvar taxas da semana' : 'Salvar ajuste';
      $(prefixo + '-cancelar').disabled = ocupado;
    }
  }
  async function enviar(lote, uid) {
    try {
      await api().aplicarFinanceiro(lote);
      sessionStorage.removeItem(chave(uid));
    } catch (erro) {
      if (recusaConfirmada(erro)) sessionStorage.removeItem(chave(uid));
      throw erro;
    }
  }
  async function retomar(uid) {
    const lote = pendente(uid);
    if (lote) await enviar(lote, uid);
  }
  function acoes(item, tabela, registro) {
    const grupo = texto('div', '', 'acoes');
    const editar = texto('button', 'Editar');
    editar.addEventListener('click', () =>
      tabela === 'financeiro_lancamentos'
        ? abrir(registro.tipo, registro)
        : abrirAnual(registro)
    );
    const excluir = texto('button', 'Excluir', 'perigo');
    excluir.addEventListener('click', async () => {
      if (ocupado || !navigator.onLine) return;
      const nome =
        tabela === 'financeiro_taxas_anuais'
          ? `o ajuste de ${registro.ano}`
          : registro.parcelas > 1
            ? `somente a parcela ${registro.parcela}/${registro.parcelas}`
            : 'este lançamento';
      if (!confirm(`Excluir ${nome}?`)) return;
      await gravar([
        {
          tabela,
          acao: 'excluir',
          id: registro.id,
          versao: registro.versao,
          dados: null,
        },
      ]);
    });
    grupo.append(editar, excluir);
    item.append(grupo);
  }
  function desenhar() {
    const r = resumoFinanceiro(dados, selecao);
    for (const campo of [
      'bruto',
      'taxas',
      'liquido',
      'despesas',
      'saldo',
      'falta',
    ])
      $(`fin-${campo}`).textContent = moeda(r[campo]);
    $('fin-saldo').classList.toggle('negativo', r.saldo < 0);
    let aviso =
      'Saldo considera somente gastos e taxas cadastrados, inclusive futuros. Taxa não cadastrada não significa isenção.';
    if (r.parciais.length)
      aviso += ` Taxa anual de ${r.parciais.join(', ')} não descontada neste recorte: saldo provisório, sem rateio.`;
    if (r.estimados.length)
      aviso += ` Taxas estimadas em ${r.estimados.join(', ')}: o resultado não é um valor líquido confirmado.`;
    $('fin-aviso').textContent = aviso;
    $('fin-lancamentos').replaceChildren();
    $('fin-vazio').hidden = r.lancamentos.length > 0;
    for (const l of [...r.lancamentos].sort(
      (a, b) => b.data.localeCompare(a.data) || a.id.localeCompare(b.id)
    )) {
      const item = texto('li', '', 'painel registro');
      const topo = texto('div', '', 'titulo');
      topo.append(
        texto('strong', br(l.data)),
        texto('strong', moeda(l.valor_centavos), 'valor')
      );
      item.append(
        topo,
        texto('p', l.descricao),
        ...(l.data_compra ? [texto('p', `Compra em ${br(l.data_compra)} · Fatura em ${br(l.data)}`, 'nota')] : []),
        texto(
          'p',
          `${l.tipo === 'taxa' ? 'Taxa das vendas no cartão' : 'Despesa'} · ${l.meio} · ${l.categoria}${l.parcelas > 1 ? ` · Parcela ${l.parcela}/${l.parcelas}` : ''}`,
          'nota'
        )
      );
      acoes(item, 'financeiro_lancamentos', l);
      $('fin-lancamentos').append(item);
    }
    $('fin-semanas').replaceChildren();
    for (const [segunda, valor] of r.semanas) {
      const item = texto('li', '', 'painel registro titulo');
      item.append(
        texto('span', `Semana de ${br(segunda)}`),
        texto('strong', moeda(valor))
      );
      $('fin-semanas').append(item);
    }
    if (!r.semanas.length)
      $('fin-semanas').append(
        texto('li', 'Nenhuma despesa neste período.', 'nota')
      );
    $('fin-anuais').replaceChildren();
    for (const a of [...dados.financeiro_taxas_anuais].sort(
      (a, b) => b.ano - a.ano
    )) {
      const item = texto('li', '', 'painel registro');
      const topo = texto('div', '', 'titulo');
      topo.append(
        texto('strong', String(a.ano)),
        texto('strong', moeda(a.valor_centavos), 'valor')
      );
      item.append(
        topo,
        texto('p', `${a.natureza} · ${br(a.inicio)} a ${br(a.fim)}`, 'nota')
      );
      if (a.observacao) item.append(texto('p', a.observacao, 'nota'));
      acoes(item, 'financeiro_taxas_anuais', a);
      $('fin-anuais').append(item);
    }
    if (!dados.financeiro_taxas_anuais.length)
      $('fin-anuais').append(
        texto('li', 'Nenhum ajuste anual cadastrado.', 'nota')
      );
    $('fin-periodo').textContent = `${br(selecao.inicio)} a ${br(selecao.fim)}`;
    $('fin-dados').hidden = false;
    controles();
  }
  async function atualizar(nova = selecao) {
    if (ocupado || !sessao()) return;
    if (!navigator.onLine) {
      $('fin-status').textContent = 'Conecte-se para atualizar as finanças.';
      return;
    }
    const uid = sessao().user.id,
      atual = geracao;
    const tipoConsulta = nova?.tipo || $('fin-tipo').value;
    const referenciaConsulta = nova?.referencia || $('fin-referencia').value;
    ocupado = true;
    controles();
    $('fin-status').textContent = 'Consultando dados financeiros…';
    try {
      if (api().fechamentos) await api().fechamentos();
      const consulta = { ...limitesFinanceiros(tipoConsulta, referenciaConsulta), tipo: tipoConsulta, referencia: referenciaConsulta };
      await retomar(uid);
      const resposta = await api().financeiro();
      if (atual !== geracao) return;
      dados = resposta;
      selecao = consulta;
      desenhar();
      $('fin-status').textContent =
        'Dados consultados na nuvem. O PC recebe as alterações enquanto estiver aberto e conectado.';
      return true;
    } catch (erro) {
      if (atual === geracao)
        $('fin-status').textContent =
          erroFinanceiro(erro) + ' A consulta não foi atualizada.';
      return false;
    } finally {
      if (atual === geracao) {
        ocupado = false;
        controles();
      }
    }
  }
  function desenharTaxas() {
    if (!dados || !$('taxas-referencia').value) return;
    const inicio = $('taxas-referencia').value;
    const dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'];
    $('taxas-dias').replaceChildren();
    for (let i = 0; i < 7; i++) {
      const d = new Date(inicio + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + i);
      const data = d.toISOString().slice(0, 10);
      const anterior = dados.financeiro_lancamentos.find(r => r.tipo === 'taxa' && r.data === data);
      const coberto = dados.financeiro_taxas_anuais.find(a => a.inicio <= data && a.fim >= data);
      const label = texto('label', `${dias[i]} · ${br(data)} · Taxa em R$`);
      const input = document.createElement('input');
      input.name = data; input.inputMode = 'decimal'; input.placeholder = 'Sem taxa informada';
      input.value = anterior ? (Number(anterior.valor_centavos) / 100).toFixed(2).replace('.', ',') : '';
      if (coberto) { input.dataset.somenteLeitura = '1'; input.disabled = true; label.append(texto('small', `Incluída no histórico de ${coberto.ano}.`)); }
      label.append(input); $('taxas-dias').append(label);
    }
  }
  function abrirTaxas() {
    if (ocupado || !dados) return;
    $('taxas-erro-form').textContent = '';
    seletorTaxas.definir(hoje());
    controles();
    $('taxas-dialogo').showModal();
  }
  function atualizarPrevia() {
    const form = $('fin-form');
    const cartao = form.elements.tipo.value === 'despesa' && form.elements.meio.value === 'Cartão de crédito';
    $('fin-origem-campo').hidden = !cartao || !editando || !!editando.data_compra;
    $('fin-valor-titulo').textContent = form.elements.tipo.value === 'taxa' ? 'Valor total da taxa (R$)' : 'Valor total da compra (R$)';
    $('fin-data-titulo').textContent = cartao ? form.elements.origem_data.value === 'fatura' ? 'Primeira fatura já cadastrada' : 'Data da compra' :
      form.elements.tipo.value === 'taxa' ? 'Data da venda no cartão' : 'Data de pagamento ou vencimento';
    try {
      const campos = Object.fromEntries(new FormData(form));
      const ops = lancamentoFormulario(campos, editando, () => 'previa');
      const linhas = ops.filter(op => op.dados);
      const datas = linhas.map((op) => br(op.dados.data));
      const mostra = datas.length > 4 ? [...datas.slice(0, 3), '...', datas.at(-1)] : datas;
      $('fin-previa').textContent = `Total: ${moeda(linhas.reduce((s, op) => s + op.dados.valor_centavos, 0))} · ${linhas.length > 1 ? `${linhas.length} parcelas: ${[...new Set(linhas.map(op => moeda(op.dados.valor_centavos)))].join(' / ')}` : form.elements.tipo.value === 'taxa' ? 'taxa informada' : 'pagamento único'}. ${cartao ? 'Faturas previstas' : 'Lançamento em'}: ${mostra.join(' · ')}.`;
    } catch { $('fin-previa').textContent = ''; }
  }
  $('fin-form').addEventListener('change', atualizarPrevia);
  $('fin-form').addEventListener('input', atualizarPrevia);
  $('fin-form').elements.origem_data.addEventListener('change', () => {
    if (!editando) return;
    if ($('fin-form').elements.origem_data.value === 'compra') campoData.limpar();
    else campoData.definir(editando.data);
  });
  function abrir(tipo, anterior = null) {
    if (ocupado) return;
    try {
      editando = anterior ? compraDoLancamento(anterior, dados.financeiro_lancamentos) : null;
    } catch (erro) { $('fin-status').textContent = erro.message; return; }
    anterior = editando;
    const form = $('fin-form');
    form.reset();
    const valores = {
      tipo,
      data: anterior?.data_compra || anterior?.data || hoje(),
      origem_data: anterior && !anterior.data_compra && anterior.meio === 'Cartão de crédito' ? 'fatura' : 'compra',
      descricao: anterior?.descricao || '',
      valor: anterior
        ? (anterior.valor_centavos / 100).toFixed(2).replace('.', ',')
        : '',
      meio: anterior?.meio || (tipo === 'taxa' ? 'Outro' : 'Dinheiro'),
      categoria: anterior?.categoria || (tipo === 'taxa' ? 'Feira' : 'Outros'),
      parcelas: anterior?.parcelas || 1,
    };
    for (const [k, v] of Object.entries(valores)) form.elements[k].value = v;
    campoData.definir(valores.data);
    $('fin-titulo-form').textContent = anterior
      ? tipo === 'despesa' ? 'Editar compra completa' : 'Editar taxa'
      : tipo === 'taxa'
        ? 'Taxa da maquininha'
        : 'Nova despesa';
    $('fin-ajuda-form').textContent = anterior
      ? tipo === 'despesa' ? 'Você está editando a COMPRA INTEIRA, mesmo tendo aberto outra parcela. O valor é o total da compra. No cartão, a data da compra calcula as faturas automaticamente. Registros antigos mantêm a primeira fatura até você informar a compra original. Alterar a data original, o total ou a quantidade pode recalcular o histórico inteiro. Alterar só a descrição ou a categoria preserva datas e centavos; mudar a quantidade não acrescenta juros.' : 'Informe o desconto total em reais das vendas desta data.'
      : tipo === 'taxa'
        ? 'Informe em reais o desconto cobrado pela maquininha nas vendas desta data. Não é uma despesa nem uma taxa do cartão usado para fazer compras.'
        : 'Informe o TOTAL da compra. O programa divide esse valor pela quantidade de parcelas, sem acrescentar juros, e ajusta os centavos para manter a soma exata. No cartão, informe a DATA DA COMPRA. O programa calcula a primeira fatura e mostra a prévia antes de salvar. Compras no dia do fechamento entram na fatura seguinte. Não registre novamente o pagamento da fatura.';
    $('fin-erro-form').textContent = '';
    controles();
    atualizarPrevia();
    $('fin-dialogo').showModal();
  }
  function abrirAnual(anterior = null) {
    anual = anterior;
    const form = $('anual-form');
    form.reset();
    const ano = anterior?.ano || Number(hoje().slice(0, 4));
    for (const [k, v] of Object.entries({
      ano,
      inicio: anterior?.inicio || `${ano}-01-01`,
      fim: anterior?.fim || `${ano}-12-31`,
      valor: anterior
        ? (anterior.valor_centavos / 100).toFixed(2).replace('.', ',')
        : '',
      natureza: anterior?.natureza || 'Confirmada',
      observacao: anterior?.observacao || '',
    }))
      form.elements[k].value = v;
    $('anual-erro-form').textContent = '';
    controles();
    $('anual-dialogo').showModal();
  }
  async function gravar(operacoes, prefixo = null) {
    if (ocupado || !sessao() || !navigator.onLine) return;
    const uid = sessao().user.id,
      atual = geracao;
    ocupado = true;
    controles();
    try {
      let lote = pendente(uid);
      if (!lote) {
        lote = { alteracoes: operacoes, operacao_id: crypto.randomUUID() };
        try {
          sessionStorage.setItem(chave(uid), JSON.stringify(lote));
        } catch {
          throw { armazenamento: true };
        } // Sem o registro, não envia.
      }
      await enviar(lote, uid);
      if (atual !== geracao) return;
      if (prefixo)
        dialogo(prefixo).close();
      $('fin-status').textContent = 'Alteração salva.';
    } catch (erro) {
      if (atual === geracao)
        (prefixo ? $(prefixo + '-erro-form') : $('fin-status')).textContent =
          erroFinanceiro(erro);
      return;
    } finally {
      if (atual === geracao) {
        ocupado = false;
        controles();
      }
    }
    if (atual === geracao) await atualizar();
  }
  for (const prefixo of ['fin', 'anual', 'taxas']) {
    $(prefixo + '-form').addEventListener('submit', (event) => {
      event.preventDefault();
      if (ocupado || !navigator.onLine) return;
      try {
        const existente = pendente();
        const dadosForm = Object.fromEntries(new FormData(event.target));
        const operacoes = existente
          ? existente.alteracoes
          : prefixo === 'fin'
            ? lancamentoFormulario(dadosForm, editando)
            : prefixo === 'taxas'
              ? taxasSemanaFormulario($('taxas-referencia').value, dadosForm, dados.financeiro_lancamentos, dados.financeiro_taxas_anuais)
              : anualFormulario(dadosForm, anual);
        const removidas = operacoes.filter(op => op.acao === 'excluir').length;
        if (!existente && prefixo === 'fin' && editando?.tipo === 'despesa' && (Number(dadosForm.parcelas) > 1 || editando.parcelas > 1) && !confirm(`Atualizar a compra inteira? Todas as parcelas serão recalculadas com o total informado, incluindo meses anteriores.${removidas ? ` Serão removidas as últimas ${removidas} parcelas; o total será redistribuído nas restantes.` : ''}`)) return;
        gravar(operacoes, prefixo);
      } catch (erro) {
        $(prefixo + '-erro-form').textContent = erro.message;
      }
    });
    $(prefixo + '-cancelar').addEventListener('click', () => {
      if (!ocupado)
        dialogo(prefixo).close();
    });
    dialogo(prefixo).addEventListener(
      'cancel',
      (event) => {
        if (ocupado) event.preventDefault();
      }
    );
  }
  $('fin-despesa').addEventListener('click', () => abrir('despesa'));
  $('fin-taxa').addEventListener('click', abrirTaxas);
  $('fin-anual').addEventListener('click', () => abrirAnual());
  $('fin-atualizar').addEventListener('click', () => atualizar());
  $('fin-filtros').addEventListener('submit', (event) => {
    event.preventDefault();
    try {
      atualizar(
        { ...limitesFinanceiros($('fin-tipo').value, $('fin-referencia').value), tipo: $('fin-tipo').value, referencia: $('fin-referencia').value }
      );
    } catch (erro) {
      $('fin-status').textContent = erro.message;
    }
  });
  window.addEventListener('online', controles);
  window.addEventListener('offline', controles);
  return {
    atualizar,
    definirPadrao() {
      if (!selecao) { const ref = mesFechamento(); seletorFinanceiro.definir(`${ref.ano}-${String(ref.mes).padStart(2, '0')}-01`); }
    },
    ocupado: () => {
      try {
        return (
          ocupado ||
          configuracaoFechamento.ocupado() ||
          $('fin-dialogo').open ||
          $('anual-dialogo').open ||
          $('taxas-dialogo').open ||
          !!pendente()
        );
      } catch {
        return true;
      }
    },
    limpar() {
      geracao++;
      configuracaoFechamento.limpar();
      ocupado = false;
      dados = null;
      selecao = null;
      editando = anual = null;
      for (const id of ['fin-dialogo', 'anual-dialogo', 'taxas-dialogo']) $(id).close();
      $('fin-form').reset();
      $('anual-form').reset();
      $('taxas-form').reset();
      $('taxas-dias').replaceChildren();
      for (const id of ['fin-lancamentos', 'fin-semanas', 'fin-anuais'])
        $(id).replaceChildren();
      for (const campo of [
        'bruto',
        'taxas',
        'liquido',
        'despesas',
        'saldo',
        'falta',
      ])
        $('fin-' + campo).textContent = '—';
      $('fin-dados').hidden = true;
      $('fin-status').textContent = '';
      controles();
    },
  };
}
