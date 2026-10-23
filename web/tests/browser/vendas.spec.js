import { test, expect } from '@playwright/test';

const USER = '11111111-1111-4111-8111-111111111111';
function token() {
  const codificar = (obj) =>
    Buffer.from(JSON.stringify(obj)).toString('base64url');
  return `${codificar({ alg: 'HS256', typ: 'JWT' })}.${codificar({ sub: USER, role: 'authenticated', exp: Math.floor(Date.now() / 1000) + 3600 })}.teste`;
}
async function preparar(page, { falharListagem = false } = {}) {
  const vendas = [];
  const financeiro = { lancamentos: [], anuais: [] };
  const fechamentos = { versao: 0, historico: [] };
  vendas.fechamentos = fechamentos;
  vendas.financeiro = financeiro;
  const recibos = new Set();
  await page.route('https://projeto-teste.supabase.co/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const headers = {
      'access-control-allow-origin': '*',
      'access-control-allow-headers': '*',
      'access-control-allow-methods': 'GET,POST,PATCH,DELETE,OPTIONS',
    };
    const responder = (data, status = 200) =>
      route.fulfill({
        status,
        headers,
        contentType: 'application/json',
        body: JSON.stringify(data),
      });
    if (request.method() === 'OPTIONS') return responder({});
    if (url.pathname === '/auth/v1/token')
      return responder({
        access_token: token(),
        refresh_token: 'refresh-apenas-teste',
        token_type: 'bearer',
        expires_in: 3600,
        user: {
          id: USER,
          email: 'exemplo@example.invalid',
          aud: 'authenticated',
          role: 'authenticated',
        },
      });
    if (url.pathname === '/auth/v1/logout')
      return route.fulfill({ status: 204, headers });
    if (url.pathname === '/rest/v1/rpc/consultar_fechamentos') return responder(fechamentos);
    if (url.pathname === '/rest/v1/rpc/salvar_fechamento') {
      const body = request.postDataJSON();
      if (body.versao_esperada !== fechamentos.versao) return responder({ code: '40001' }, 409);
      fechamentos.historico = [...fechamentos.historico.filter(r => r.vigencia !== body.vigencia), { vigencia: body.vigencia, dia: body.dia }];
      fechamentos.versao++;
      return responder(fechamentos);
    }
    if (url.pathname === '/rest/v1/rpc/usuario_autorizado')
      return responder(true);
    if (url.pathname === '/rest/v1/rpc/sincronizar_desktop') {
      const lote = request.postDataJSON();
      if (lote.operacao_id && !recibos.has(lote.operacao_id)) {
        const copia = structuredClone({
          financeiro_lancamentos: financeiro.lancamentos,
          financeiro_taxas_anuais: financeiro.anuais,
        });
        for (const op of lote.alteracoes) {
          const linhas = copia[op.tabela];
          const index = linhas.findIndex((r) => r.id === op.id);
          if (
            op.acao !== 'inserir' &&
            (index < 0 || linhas[index].versao !== op.versao)
          )
            return responder({ code: 'PFS01' }, 400);
          if (op.acao === 'excluir') linhas.splice(index, 1);
          else if (op.acao === 'inserir')
            linhas.push({ ...op.dados, id: op.id, versao: 1 });
          else
            linhas[index] = { ...op.dados, id: op.id, versao: op.versao + 1 };
        }
        for (const l of copia.financeiro_lancamentos.filter(
          (r) => r.tipo === 'taxa'
        ))
          if (
            copia.financeiro_taxas_anuais.some(
              (a) => a.inicio <= l.data && a.fim >= l.data
            )
          )
            return responder({ code: '23505' }, 409);
        financeiro.lancamentos = copia.financeiro_lancamentos;
        financeiro.anuais = copia.financeiro_taxas_anuais;
        recibos.add(lote.operacao_id);
        if (financeiro.perderResposta) {
          financeiro.perderResposta = false;
          return route.abort('failed');
        }
      }
      return responder({
        protocolo: 1,
        usuario_id: USER,
        operacao_id: lote.operacao_id,
        repetida: false,
        dados: {
          vendas,
          financeiro_lancamentos: financeiro.lancamentos,
          financeiro_taxas_anuais: financeiro.anuais,
        },
      });
    }
    if (url.pathname === '/rest/v1/vendas') {
      if (request.method() === 'GET') {
        if (falharListagem)
          return responder({ message: 'Consulta recusada no teste' }, 400);
        const filtros = url.searchParams.getAll('data');
        return responder(
          vendas.filter((r) =>
            filtros.every((f) =>
              f.startsWith('gte.') ? r.data >= f.slice(4) : r.data <= f.slice(4)
            )
          )
        );
      }
      if (request.method() === 'POST') {
        const dados = request.postDataJSON();
        if (vendas.some((r) => r.data === dados.data))
          return responder({ code: '23505', message: 'data duplicada' }, 409);
        const r = { ...dados, id: crypto.randomUUID(), versao: 1 };
        vendas.push(r);
        return responder([r], 201);
      }
      const id = url.searchParams.get('id').slice(3);
      const versao = Number(url.searchParams.get('versao').slice(3));
      const index = vendas.findIndex((r) => r.id === id && r.versao === versao);
      if (index < 0) return responder([]);
      if (request.method() === 'PATCH') {
        Object.assign(vendas[index], request.postDataJSON(), {
          versao: versao + 1,
        });
        return responder([vendas[index]]);
      }
      if (request.method() === 'DELETE') {
        vendas.splice(index, 1);
        return responder([{ id }]);
      }
    }
    return responder({ message: 'rota não simulada' }, 404);
  });
  await page.goto('/');
  if (process.env.CAPTURAR_WEB_DIR)
    await page.screenshot({
      path: `${process.env.CAPTURAR_WEB_DIR}/feira-login.png`,
      fullPage: true,
    });
  await page.getByLabel('E-mail').fill('exemplo@example.invalid');
  await page.getByLabel('Senha', { exact: true }).fill('senha-so-de-teste');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(
    page.getByRole('button', { name: '+ Nova venda' })
  ).toBeVisible();
  await expect(page.locator('#vazio')).toBeVisible();
  return vendas;
}

test('celular: login, cadastro, duplicidade, edição, filtro e exclusão', async ({
  page,
}) => {
  await preparar(page);
  await page.getByRole('button', { name: '+ Nova venda' }).click();
  await page.getByLabel('Data da feira').fill('2030-10-16');
  await page.getByLabel('Dinheiro', { exact: true }).fill('100,25');
  await page.getByLabel('Pix', { exact: true }).fill('20,50');
  await page.getByLabel('Cartão', { exact: true }).fill('30');
  await page.getByRole('button', { name: 'Salvar venda' }).click();
  await page.locator('#tipo').selectOption('Todas');
  await expect(page.locator('#mes')).toBeDisabled();
  await page.getByRole('button', { name: 'Aplicar', exact: true }).click();
  await expect(page.locator('#total')).toHaveText('R$ 150,75');
  if (process.env.CAPTURAR_WEB_DIR)
    await page.screenshot({
      path: `${process.env.CAPTURAR_WEB_DIR}/feira-vendas.png`,
      fullPage: true,
    });
  await expect(page.locator('#vendas li')).toHaveCount(1);
  await page.getByRole('button', { name: '+ Nova venda' }).click();
  await page.getByLabel('Data da feira').fill('2030-10-16');
  await page.getByRole('button', { name: 'Salvar venda' }).click();
  await expect(page.getByRole('alert')).toContainText('Já existe');
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await page.getByRole('button', { name: 'Editar', exact: true }).click();
  await page.getByLabel('Pix', { exact: true }).fill('40,50');
  await page.getByRole('button', { name: 'Salvar venda' }).click();
  await expect(page.locator('#total')).toHaveText('R$ 170,75');
  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Excluir', exact: true }).click();
  await expect(page.locator('#vendas li')).toHaveCount(0);
  await expect(page.locator('#total')).toHaveText('R$ 0,00');
});

test('sem internet não salva; uma alteração concorrente não é sobrescrita', async ({
  page,
  context,
}) => {
  const vendas = await preparar(page);
  await page.getByRole('button', { name: '+ Nova venda' }).click();
  await context.setOffline(true);
  await expect(
    page.getByRole('button', { name: 'Salvar venda' })
  ).toBeDisabled();
  await expect(page.locator('#rede')).toBeVisible();
  await context.setOffline(false);
  await page.getByLabel('Data da feira').fill('2030-10-16');
  await page.getByRole('button', { name: 'Salvar venda' }).click();
  await page.locator('#tipo').selectOption('Todas');
  await page.getByRole('button', { name: 'Aplicar', exact: true }).click();
  await expect(page.locator('#vendas li')).toHaveCount(1);
  await page.getByRole('button', { name: 'Editar', exact: true }).click();
  vendas[0].versao++;
  await page.getByLabel('Dinheiro', { exact: true }).fill('999');
  await page.getByRole('button', { name: 'Salvar venda' }).click();
  await expect(page.getByRole('alert')).toContainText(
    'alterado em outro acesso'
  );
  expect(vendas[0].dinheiro_centavos).toBe(0);
});

test('layout não estoura a largura, sair limpa a lista e o cache não contém dados da API', async ({
  page,
}) => {
  await preparar(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    )
  ).toBe(true);
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  const cache = await page.evaluate(async () => {
    const urls = [];
    for (const nome of await caches.keys())
      for (const r of await (await caches.open(nome)).keys()) urls.push(r.url);
    return urls;
  });
  expect(cache.some((url) => url.includes('supabase.co'))).toBe(false);
  await page.getByRole('button', { name: 'Sair', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Entrar', exact: true })
  ).toBeVisible();
  await expect(page.locator('#conteudo')).toBeHidden();
  await expect(page.locator('#vendas li')).toHaveCount(0);
});

test('ao voltar ao celular atualiza os dados, preservando formulário em edição', async ({
  page,
}) => {
  const vendas = await preparar(page);
  vendas.push({
    id: crypto.randomUUID(),
    versao: 1,
    data: '2030-10-16',
    dinheiro_centavos: 100,
    pix_centavos: 0,
    cartao_centavos: 0,
  });
  await page.locator('#tipo').selectOption('Todas');
  await page.getByRole('button', { name: 'Aplicar', exact: true }).click();
  await expect(page.locator('#total')).toHaveText('R$ 1,00');
  vendas[0].pix_centavos = 200;
  vendas[0].versao++;
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.locator('#total')).toHaveText('R$ 3,00');
  await page.getByRole('button', { name: 'Editar', exact: true }).click();
  await page.getByLabel('Pix', { exact: true }).fill('99,00');
  vendas[0].pix_centavos = 300;
  vendas[0].versao++;
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.getByLabel('Pix', { exact: true })).toHaveValue('99,00');
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.locator('#total')).toHaveText('R$ 4,00');
});

async function dataFinanceira(page, data) {
  const [ano, mes, dia] = data.split('-');
  await page.locator('#fin-data-ano').fill(ano);
  await page.locator('#fin-data-ano').dispatchEvent('change');
  await page.locator('#fin-data-mes').selectOption(String(Number(mes)));
  await page.locator('#fin-data-dia').selectOption(String(Number(dia)));
}
async function consultarFinancas(
  page,
  tipo = 'Mês',
  referencia = '2030-10-01'
) {
  await page.locator('#fin-tipo').selectOption(tipo);
  await page.locator('#fin-ano').fill(referencia.slice(0, 4));
  await page.locator('#fin-ano').dispatchEvent('change');
  if (tipo !== 'Ano') await page.locator('#fin-mes').selectOption(String(Number(referencia.slice(5, 7))));
  if (tipo === 'Semana') {
    const { limitesFinanceiros } = await import('../../src/financeiro.js');
    await page.locator('#fin-semana').selectOption(limitesFinanceiros('Semana', referencia).inicio);
  }
  await page.locator('#fin-consultar').click();
  await expect(page.locator('#fin-status')).toContainText('Dados consultados');
}
test('finanças mostra saldo, semanas e ajustes estimados sem ratear taxa anual parcial', async ({
  page,
}) => {
  const vendas = await preparar(page);
  vendas.push({
    id: crypto.randomUUID(),
    versao: 1,
    data: '2030-10-16',
    dinheiro_centavos: 10000,
    pix_centavos: 0,
    cartao_centavos: 0,
  });
  vendas.financeiro.lancamentos.push({
    id: crypto.randomUUID(),
    versao: 1,
    tipo: 'despesa',
    data: '2030-10-16',
    descricao: '<img src=x onerror=alert(1)>',
    valor_centavos: 3000,
    meio: 'Pix',
    categoria: 'Casa',
    grupo: null,
    parcela: 1,
    parcelas: 1,
  });
  vendas.financeiro.anuais.push({
    id: crypto.randomUUID(),
    versao: 1,
    ano: 2030,
    inicio: '2030-01-01',
    fim: '2030-12-31',
    valor_centavos: 500,
    natureza: 'Estimada',
    observacao: 'Ajuste fictício',
  });
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page);
  await expect(page.locator('#fin-bruto')).toHaveText('R$ 100,00');
  await expect(page.locator('#fin-taxas')).toHaveText('R$ 0,00');
  await expect(page.locator('#fin-saldo')).toHaveText('R$ 70,00');
  await expect(page.locator('#fin-aviso')).toContainText('saldo provisório');
  await expect(page.locator('#fin-aviso')).toContainText('Taxas estimadas');
  await expect(page.locator('#fin-semanas')).toContainText('R$ 30,00');
  expect(await page.locator('#fin-lancamentos img').count()).toBe(0);
  await consultarFinancas(page, 'Ano');
  await expect(page.locator('#fin-taxas')).toHaveText('R$ 5,00');
  await expect(page.locator('#fin-saldo')).toHaveText('R$ 65,00');
  await page.getByLabel('Ajuda: Saldo do período').click();
  await expect(
    page.getByText('Não é um cálculo contábil de lucro', { exact: false })
  ).toBeVisible();
  const ajuda = await page.locator('details[open] p').boundingBox();
  expect(ajuda.x).toBeGreaterThanOrEqual(0);
  expect(ajuda.x + ajuda.width).toBeLessThanOrEqual(390);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    )
  ).toBe(true);
  if (process.env.CAPTURAR_WEB_DIR)
    await page.screenshot({
      path: `${process.env.CAPTURAR_WEB_DIR}/feira-financas.png`,
      fullPage: true,
    });
  await page.getByRole('button', { name: 'Sair', exact: true }).click();
  await expect(page.locator('#fin-lancamentos li')).toHaveCount(0);
  await expect(page.locator('#fin-saldo')).toHaveText('—');
});
test('despesas parceladas: cria lote, edita e exclui somente a parcela escolhida', async ({
  page,
}) => {
  const vendas = await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page, 'Ano');
  await page.getByRole('button', { name: '+ Despesa', exact: true }).click();
  const f = page.locator('#fin-form');
  await dataFinanceira(page, '2030-10-31');
  await f.getByLabel('Descrição', { exact: true }).fill('Compra fictícia');
  await f.getByLabel('Valor de cada parcela ou lançamento').fill('123,45');
  await f.getByLabel('Meio de pagamento').selectOption('Cartão de crédito');
  await f.getByLabel('Quantidade de parcelas').fill('2');
  await f
    .getByRole('button', { name: 'Salvar lançamento', exact: true })
    .click();
  await expect(page.locator('#fin-lancamentos li')).toHaveCount(2);
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 246,90');
  const primeira = page
    .locator('#fin-lancamentos li')
    .filter({ hasText: 'Parcela 1/2' });
  await primeira.getByRole('button', { name: 'Editar', exact: true }).click();
  await expect(f.getByLabel('Quantidade de parcelas')).toBeDisabled();
  await f.getByLabel('Valor de cada parcela ou lançamento').fill('120,00');
  await f
    .getByRole('button', { name: 'Salvar lançamento', exact: true })
    .click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 243,45');
  expect(
    vendas.financeiro.lancamentos.find((r) => r.parcela === 2).valor_centavos
  ).toBe(12345);
  await primeira.getByRole('button', { name: 'Editar', exact: true }).click();
  const alterada = vendas.financeiro.lancamentos.find((r) => r.parcela === 1);
  alterada.versao++;
  alterada.valor_centavos = 22000;
  await f.getByLabel('Valor de cada parcela ou lançamento').fill('999,00');
  await f
    .getByRole('button', { name: 'Salvar lançamento', exact: true })
    .click();
  await expect(page.locator('#fin-erro-form')).toContainText(
    'mudou em outro acesso'
  );
  expect(alterada.valor_centavos).toBe(22000);
  await f.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await page
    .getByRole('button', { name: 'Atualizar finanças', exact: true })
    .click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 343,45');
  page.once('dialog', (d) => d.accept());
  await primeira.getByRole('button', { name: 'Excluir', exact: true }).click();
  await expect(page.locator('#fin-lancamentos li')).toHaveCount(1);
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 123,45');
});
test('taxa diária sobreposta é recusada; ajuste anual pode ser editado e excluído', async ({
  page,
}) => {
  await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page, 'Ano');
  await page
    .getByRole('button', { name: '+ Total histórico de taxas', exact: true })
    .click();
  const a = page.locator('#anual-form');
  await a.getByLabel('Ano do ajuste').fill('2030');
  await a.getByLabel('Início da cobertura').fill('2030-01-01');
  await a.getByLabel('Fim da cobertura').fill('2030-01-31');
  await a.getByLabel('Valor das taxas').fill('50,01');
  await a.getByLabel('Natureza').selectOption('Estimada');
  await a.getByRole('button', { name: 'Salvar ajuste', exact: true }).click();
  await expect(page.locator('#fin-taxas')).toHaveText('R$ 50,01');
  await page
    .getByRole('button', { name: '+ Taxas da maquininha', exact: true })
    .click();
  await page.locator('#taxas-ano').fill('2030');
  await page.locator('#taxas-ano').dispatchEvent('change');
  await page.locator('#taxas-mes').selectOption('1');
  await page.locator('#taxas-semana').selectOption('2030-01-14');
  await expect(page.locator('#taxas-dias input[name="2030-01-15"]')).toBeDisabled();
  await expect(page.locator('#taxas-dias')).toContainText('Incluída no histórico de 2030');
  await page.locator('#taxas-cancelar').click();
  await page
    .locator('#fin-anuais')
    .getByRole('button', { name: 'Editar', exact: true })
    .click();
  await a.getByLabel('Valor das taxas').fill('50,02');
  await a.getByRole('button', { name: 'Salvar ajuste', exact: true }).click();
  await expect(page.locator('#fin-taxas')).toHaveText('R$ 50,02');
  page.once('dialog', (d) => d.accept());
  await page
    .locator('#fin-anuais')
    .getByRole('button', { name: 'Excluir', exact: true })
    .click();
  await expect(page.locator('#fin-taxas')).toHaveText('R$ 0,00');
});
test('resposta perdida retoma a operação após recarregar sem duplicar despesa', async ({
  page,
}) => {
  const vendas = await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await page.getByRole('button', { name: '+ Despesa', exact: true }).click();
  const f = page.locator('#fin-form');
  await dataFinanceira(page, '2030-10-16');
  await f.getByLabel('Descrição', { exact: true }).fill('Teste de retomada');
  await f.getByLabel('Valor de cada parcela ou lançamento').fill('10,00');
  vendas.financeiro.perderResposta = true;
  await f
    .getByRole('button', { name: 'Salvar lançamento', exact: true })
    .click();
  await expect(page.locator('#fin-erro-form')).toContainText(
    'Não foi possível confirmar'
  );
  expect(vendas.financeiro.lancamentos).toHaveLength(1);
  await expect(f.getByLabel('Descrição', { exact: true })).toBeDisabled();
  await page.reload();
  await expect(
    page.getByRole('button', { name: 'Finanças', exact: true })
  ).toBeVisible();
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-status')).toContainText('Dados consultados');
  await consultarFinancas(page);
  await expect(page.locator('#fin-lancamentos li')).toHaveCount(1);
  expect(vendas.financeiro.lancamentos).toHaveLength(1);
  expect(
    await page.evaluate(() =>
      Object.keys(sessionStorage).some((k) =>
        k.startsWith('feira-financeiro-pendente:')
      )
    )
  ).toBe(false);
});

test('falha no armazenamento da confirmação impede enviar a despesa', async ({
  page,
}) => {
  const vendas = await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await page.getByRole('button', { name: '+ Despesa', exact: true }).click();
  const f = page.locator('#fin-form');
  await dataFinanceira(page, '2030-10-16');
  await f.getByLabel('Descrição', { exact: true }).fill('Teste sem envio');
  await f.getByLabel('Valor de cada parcela ou lançamento').fill('10,00');
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function (chave, valor) {
      if (chave.startsWith('feira-financeiro-pendente:'))
        throw new DOMException('Indisponível', 'QuotaExceededError');
      return original.call(this, chave, valor);
    };
  });
  await f
    .getByRole('button', { name: 'Salvar lançamento', exact: true })
    .click();
  await expect(page.locator('#fin-erro-form')).toContainText(
    'Permita armazenamento local'
  );
  expect(vendas.financeiro.lancamentos).toHaveLength(0);
});

test('análises: pagamentos, dias zerados e comparação independente no celular', async ({
  page,
}) => {
  const vendas = await preparar(page);
  vendas.push(
    {
      id: 'ana1',
      versao: 1,
      data: '2026-09-18',
      dinheiro_centavos: 10000,
      pix_centavos: 0,
      cartao_centavos: 0,
    },
    {
      id: 'ana2',
      versao: 1,
      data: '2026-10-16',
      dinheiro_centavos: 10000,
      pix_centavos: 2000,
      cartao_centavos: 3000,
    },
    {
      id: 'ana3',
      versao: 1,
      data: '2026-10-23',
      dinheiro_centavos: 0,
      pix_centavos: 0,
      cartao_centavos: 0,
    }
  );
  await expect(page.locator('nav.abas button')).toHaveText([
    'Vendas',
    'Análises',
    'Finanças',
  ]);
  await page.locator('#aba-analises').click();
  await page.locator('#ana-tipo').selectOption('Mês');
  await page.locator('#ana-referencia').fill('2026-10-01');
  await page
    .getByRole('button', { name: 'Consultar análises', exact: true })
    .click();
  await expect(page.locator('#ana-total')).toHaveText('R$ 150,00');
  await expect(page.locator('#ana-quantidade')).toHaveText('2');
  await expect(page.locator('#ana-media')).toHaveText('R$ 75,00');
  await expect(page.locator('#ana-pagamentos')).toContainText('20%');
  await expect(page.locator('#ana-semana tr').nth(4)).toContainText('75,00');
  await expect(page.locator('#ana-anterior')).toContainText('50%');
  for (const [p, data] of [
    ['cmp-a', '2026-09-01'],
    ['cmp-b', '2026-10-01'],
  ]) {
    await page.locator('#' + p + '-tipo').selectOption('Mês');
    await page
      .locator('#' + p + '-mes')
      .selectOption(String(Number(data.slice(5, 7))));
    await page.locator('#' + p + '-ano').selectOption(data.slice(0, 4));
  }
  await page.getByRole('button', { name: 'Comparar períodos' }).click();
  await expect(page.locator('#cmp-diferenca')).toContainText('R$ 50,00');
  await expect(page.locator('#cmp-diferenca')).toContainText('50%');
  await expect(page.locator('#cmp-b-referencia')).toBeHidden();
  await expect(page.locator('#cmp-b-mes')).toBeVisible();
  await page.locator('#cmp-b-tipo').selectOption('Data');
  await expect(page.locator('#cmp-b-mes')).toBeDisabled();
  await page.locator('#cmp-b-referencia').fill('2026-10-23');
  await page.getByRole('button', { name: 'Comparar períodos' }).click();
  await expect(page.locator('#cmp-diferenca')).toContainText('-100%');
  vendas.push(
    {
      id: 'limite1',
      versao: 1,
      data: '2026-12-09',
      dinheiro_centavos: 50000,
      pix_centavos: 0,
      cartao_centavos: 0,
    },
    {
      id: 'limite2',
      versao: 1,
      data: '2026-12-10',
      dinheiro_centavos: 1000,
      pix_centavos: 0,
      cartao_centavos: 0,
    },
    {
      id: 'limite3',
      versao: 1,
      data: '2027-01-09',
      dinheiro_centavos: 2000,
      pix_centavos: 0,
      cartao_centavos: 0,
    },
    {
      id: 'limite4',
      versao: 1,
      data: '2027-01-10',
      dinheiro_centavos: 70000,
      pix_centavos: 0,
      cartao_centavos: 0,
    }
  );
  for (const [p, mes, ano] of [
    ['cmp-a', '12', '2026'],
    ['cmp-b', '1', '2027'],
  ]) {
    await page.locator('#' + p + '-tipo').selectOption('Fechamento');
    await page.locator('#' + p + '-mes').selectOption(mes);
    await page.locator('#' + p + '-ano').selectOption(ano);
    await expect(page.locator('#' + p + '-referencia')).toBeDisabled();
  }
  await page.getByRole('button', { name: 'Comparar períodos' }).click();
  await expect(page.locator('#cmp-periodo-a')).toHaveText(
    '10/12/2026 a 09/01/2027'
  );
  await expect(page.locator('#cmp-valores tr').first()).toHaveText(
    'Total brutoR$ 30,00R$ 700,00'
  );
  await expect(page.locator('#cmp-diferenca')).toContainText('R$ 670,00');
  await page.locator('#cmp-b-tipo').selectOption('Intervalo');
  await page.locator('#cmp-b-referencia').fill('2026-12-10');
  await page.locator('#cmp-b-fim').fill('2027-01-09');
  await page.getByRole('button', { name: 'Comparar períodos' }).click();
  await expect(page.locator('#cmp-diferenca')).toContainText('Variação: 0%');
  await expect(page.locator('#cmp-a-ano')).toHaveValue('2026');

  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    )
  ).toBe(true);
  if (process.env.CAPTURAR_WEB_DIR)
    await page.screenshot({
      path: `${process.env.CAPTURAR_WEB_DIR}/feira-analises.png`,
      fullPage: true,
    });
  await page.locator('#aba-vendas').click();
  await expect(page.locator('#tipo')).toHaveValue('Fechamento');
});

test('consulta automática recebe mudanças sem botão, preserva edição e atualiza as três áreas', async ({
  page,
}) => {
  await page.clock.install();
  const vendas = await preparar(page);
  vendas.push({
    id: 'auto1',
    versao: 1,
    data: '2030-10-16',
    dinheiro_centavos: 10000,
    pix_centavos: 0,
    cartao_centavos: 0,
  });
  await page.locator('#tipo').selectOption('Todas');
  await page.getByRole('button', { name: 'Aplicar', exact: true }).click();
  await expect(page.locator('#total')).toHaveText('R$ 100,00');
  // Campo ainda não aplicado não muda a seleção que recebe atualizações.
  await page.locator('#tipo').selectOption('Ano');
  await page.locator('#ano').fill('2025');
  vendas[0].pix_centavos = 2000;
  vendas[0].versao++;
  await page.clock.fastForward(60100);
  await expect(page.locator('#total')).toHaveText('R$ 120,00');
  await expect(page.locator('#ano')).toHaveValue('2025');
  await expect(page.locator('#periodo')).toHaveText('Todas as vendas');
  await expect(page.locator('#atualizacao-web')).toContainText('Conferido às');
  await page.getByRole('button', { name: 'Editar', exact: true }).click();
  await page.getByLabel('Dinheiro', { exact: true }).fill('999');
  vendas[0].pix_centavos = 3000;
  vendas[0].versao++;
  await page.clock.fastForward(60100);
  await expect(page.getByLabel('Dinheiro', { exact: true })).toHaveValue('999');
  await expect(page.locator('#total')).toHaveText('R$ 120,00');
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await page.clock.fastForward(5100);
  await expect(page.locator('#total')).toHaveText('R$ 130,00');
  await page.locator('#aba-financas').click();
  await consultarFinancas(page);
  await expect(page.locator('#fin-bruto')).toHaveText('R$ 130,00');
  vendas[0].pix_centavos = 4000;
  vendas[0].versao++;
  await page.clock.fastForward(60100);
  await expect(page.locator('#fin-bruto')).toHaveText('R$ 140,00');
  await page.locator('#aba-analises').click();
  await page.locator('#ana-tipo').selectOption('Mês');
  await page.locator('#ana-referencia').fill('2030-10-01');
  await page
    .getByRole('button', { name: 'Consultar análises', exact: true })
    .click();
  await expect(page.locator('#ana-total')).toHaveText('R$ 140,00');
  vendas[0].pix_centavos = 5000;
  vendas[0].versao++;
  await page.clock.fastForward(60100);
  await expect(page.locator('#ana-total')).toHaveText('R$ 150,00');
  await page.locator('#sair').click();
  await expect(page.locator('#conteudo')).toBeHidden();
  await page.clock.fastForward(60100);
  await expect(page.locator('#ana-total')).toHaveText('—');
});

test('consulta lenta não aplica filtros digitados enquanto a resposta está chegando', async ({
  page,
}) => {
  await preparar(page);
  for (const [area, prefixo] of [
    ['analises', 'ana'],
    ['financas', 'fin'],
  ]) {
    let liberar;
    const espera = new Promise((resolve) => (liberar = resolve));
    const atrasar = async (route) => {
      await espera;
      await route.fallback();
    };
    await page.route('**/rest/v1/rpc/sincronizar_desktop', atrasar);
    await page.locator('#aba-' + area).click();
    await expect(page.locator('#' + prefixo + '-status')).toContainText(
      'Consultando'
    );
    if (prefixo === 'fin') {
      await page.locator('#fin-ano').fill('2001');
      await page.locator('#fin-ano').dispatchEvent('change');
    } else await page.locator('#ana-referencia').fill('2001-01-10');
    await expect(
      page.locator(prefixo === 'fin' ? '#fin-consultar' : '#ana-filtros button')
    ).toBeDisabled();
    liberar();
    await expect(page.locator('#' + prefixo + '-status')).not.toContainText(
      'Consultando'
    );
    if (prefixo === 'fin') await expect(page.locator('#fin-ano')).toHaveValue('2001');
    else await expect(page.locator('#ana-referencia')).toHaveValue('2001-01-10');
    await expect(page.locator('#' + prefixo + '-periodo')).not.toContainText(
      '2001'
    );
    await page.unroute('**/rest/v1/rpc/sincronizar_desktop', atrasar);
  }
});

test('exporta somente a seleção aplicada em CSV e Excel e mostra evolução com lacunas', async ({
  page,
}) => {
  const vendas = await preparar(page);
  vendas.push(
    {
      id: 'exp1',
      versao: 1,
      data: '2030-10-11',
      dinheiro_centavos: 10025,
      pix_centavos: 2050,
      cartao_centavos: 3000,
    },
    {
      id: 'exp2',
      versao: 1,
      data: '2030-12-13',
      dinheiro_centavos: 0,
      pix_centavos: 0,
      cartao_centavos: 0,
    }
  );
  await page.locator('#tipo').selectOption('Todas');
  await page.getByRole('button', { name: 'Aplicar', exact: true }).click();
  await expect(page.locator('#total')).toHaveText('R$ 150,75');
  // Alteração não aplicada não pode vazar para o arquivo exportado.
  await page.locator('#tipo').selectOption('Ano');
  await page.locator('#ano').fill('2001');
  for (const [id, extensao] of [
    ['exportar-csv', 'csv'],
    ['exportar-excel', 'xlsx'],
  ]) {
    const espera = page.waitForEvent('download');
    await page.locator('#' + id).click();
    const download = await espera;
    expect(download.suggestedFilename()).toBe('vendas-filtradas.' + extensao);
    const fs = await import('node:fs/promises');
    const corpo = await fs.readFile(await download.path());
    if (extensao === 'csv') {
      expect(corpo.toString('utf8')).toContain('Todas as vendas');
      expect(corpo.toString('utf8')).toContain('150,75');
    } else expect(corpo.subarray(0, 2).toString()).toBe('PK');
  }
  await page.locator('#aba-analises').click();
  await page.locator('#ana-tipo').selectOption('Todas');
  await page
    .getByRole('button', { name: 'Consultar análises', exact: true })
    .click();
  await expect(page.locator('#ana-evolucao li')).toHaveCount(3);
  await expect(page.locator('#ana-evolucao li').nth(1)).toContainText(
    'Sem registros'
  );
  await expect(page.locator('#ana-evolucao li').nth(2)).toContainText(
    'R$ 0,00 · 1 dia'
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    )
  ).toBe(true);
});

test('falha na primeira consulta não gera exportação vazia como se tivesse sido conferida', async ({
  page,
}) => {
  await preparar(page, { falharListagem: true });
  await expect(page.locator('#mensagem')).toContainText(
    'A lista não foi atualizada'
  );
  await page.locator('#exportar-csv').click();
  await expect(page.locator('#mensagem')).toHaveText(
    'Atualize a lista com sucesso antes de exportar os dados.'
  );
});

test('filtro financeiro adapta ano, mês e semanas completas sem escolher dia avulso', async ({ page }) => {
  await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page, 'Semana', '2026-01-02');
  await expect(page.locator('#fin-periodo')).toHaveText('29/12/2025 a 04/01/2026');
  await expect(page.locator('#fin-semana')).toBeVisible();
  await consultarFinancas(page, 'Mês', '2026-02-01');
  await expect(page.locator('#fin-periodo')).toHaveText('01/02/2026 a 28/02/2026');
  await expect(page.locator('#fin-semana')).toBeHidden();
  await consultarFinancas(page, 'Ano', '2025-01-01');
  await expect(page.locator('#fin-mes')).toBeHidden();
  await expect(page.locator('#fin-periodo')).toHaveText('01/01/2025 a 31/12/2025');
});

test('data da despesa permanece ao preencher os outros campos e retornar ao PWA', async ({ page }) => {
  const vendas = await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page, 'Ano', '2030-01-01');
  await page.getByRole('button', { name: '+ Despesa', exact: true }).click();
  const f = page.locator('#fin-form');
  await dataFinanceira(page, '2030-09-09');
  await f.getByLabel('Descrição', { exact: true }).fill('Teste de preservação da data');
  await f.getByLabel('Valor de cada parcela ou lançamento').fill('18,50');
  await f.getByLabel('Meio de pagamento').selectOption('Pix');
  await page.evaluate(() => {
    window.dispatchEvent(new Event('focus'));
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await expect(page.locator('#fin-data-confirmada')).toContainText('09/09/2030');
  await page.locator('#fin-salvar').click();
  await expect(page.locator('#fin-dialogo')).not.toBeVisible();
  expect(vendas.financeiro.lancamentos.at(-1).data).toBe('2030-09-09');
});

test('taxas de sexta e domingo são salvas juntas e mantêm as datas ao cruzar fechamento', async ({ page }) => {
  const vendas = await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page, 'Ano', '2026-01-01');
  await page.locator('#fin-taxa').click();
  await page.locator('#taxas-ano').fill('2026');
  await page.locator('#taxas-ano').dispatchEvent('change');
  await page.locator('#taxas-mes').selectOption('10');
  await page.locator('#taxas-semana').selectOption('2026-10-05');
  await page.locator('#taxas-dias input[name="2026-10-09"]').fill('2,00');
  await page.locator('#taxas-dias input[name="2026-10-11"]').fill('3,00');
  await page.locator('#taxas-salvar').click();
  await expect(page.locator('#taxas-dialogo')).not.toBeVisible();
  expect(vendas.financeiro.lancamentos.map(r => [r.data, r.valor_centavos])).toEqual([['2026-10-09', 200], ['2026-10-11', 300]]);
  await consultarFinancas(page, 'Fechamento', '2026-09-01');
  await expect(page.locator('#fin-taxas')).toHaveText('R$ 2,00');
  await consultarFinancas(page, 'Fechamento', '2026-10-01');
  await expect(page.locator('#fin-taxas')).toHaveText('R$ 3,00');
});

test('desktop web: comprar no dia 09 calcula próxima fatura somente ao pedir', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const vendas = await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page, 'Ano', '2026-01-01');
  await page.locator('#fin-despesa').click();
  const f = page.locator('#fin-form');
  await dataFinanceira(page, '2026-09-09');
  await f.getByLabel('Descrição', { exact: true }).fill('Compra de exemplo em 3 vezes');
  await f.getByLabel('Valor de cada parcela ou lançamento').fill('30,00');
  await f.getByLabel('Meio de pagamento').selectOption('Cartão de crédito');
  await f.getByLabel('Quantidade de parcelas').fill('3');
  await expect(page.locator('#fin-data-confirmada')).toContainText('09/09/2026');
  await page.locator('#fin-calcular-fatura').click();
  await expect(page.locator('#fin-previa')).toContainText('09/10/2026 · 09/11/2026 · 09/12/2026');
  await page.locator('#fin-salvar').click();
  await expect(page.locator('#fin-dialogo')).not.toBeVisible();
  expect(vendas.financeiro.lancamentos.map(r => r.data)).toEqual(['2026-10-09', '2026-11-09', '2026-12-09']);
});

test('fechamento futuro é compartilhado e os períodos antigos continuam iguais', async ({ page }) => {
  const dados = await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page, 'Fechamento', '2090-10-01');
  await expect(page.locator('#fin-periodo')).toHaveText('10/10/2090 a 09/11/2090');
  await page.locator('#fin-configurar-fechamento').click();
  await expect(page.locator('#fechamento-erro')).not.toContainText('Consultando');
  await page.locator('#fechamento-ano').fill('2090');
  await page.locator('#fechamento-mes').selectOption('11');
  await page.locator('#fechamento-dia').selectOption('14');
  await expect(page.locator('#fechamento-previa')).toContainText('10/10/2090 a 14/11/2090');
  await page.locator('#fechamento-salvar').click();
  await expect(page.locator('#fechamento-dialogo')).not.toBeVisible();
  await expect(page.locator('#fin-periodo')).toHaveText('10/10/2090 a 14/11/2090');
  expect(dados.fechamentos.versao).toBe(1);
  await consultarFinancas(page, 'Fechamento', '2090-09-01');
  await expect(page.locator('#fin-periodo')).toHaveText('10/09/2090 a 09/10/2090');
  await consultarFinancas(page, 'Fechamento', '2090-11-01');
  await expect(page.locator('#fin-periodo')).toHaveText('15/11/2090 a 14/12/2090');
  await page.getByRole('button', { name: 'Vendas', exact: true }).click();
  await page.locator('#tipo').selectOption('Fechamento');
  await page.locator('#ano').fill('2090'); await page.locator('#mes').selectOption('10');
  await page.getByRole('button', { name: 'Aplicar', exact: true }).click();
  await expect(page.locator('#periodo')).toHaveText('10/10/2090 a 14/11/2090');
});
