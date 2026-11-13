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
    if (['/rest/v1/rpc/sincronizar_desktop', '/rest/v1/rpc/sincronizar_desktop_v2'].includes(url.pathname)) {
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
        protocolo: url.pathname.endsWith('_v2') ? 2 : 1,
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
test('despesas parceladas: total exato, edição da compra pela última parcela e conflito atômico', async ({
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
  await f.getByLabel(/Valor total/).fill('123,45');
  await f.getByLabel('Meio de pagamento').selectOption('Cartão de crédito');
  await f.getByLabel('Quantidade de parcelas').fill('2');
  await f
    .getByRole('button', { name: 'Salvar compra', exact: true })
    .click();
  await expect(page.locator('#fin-lancamentos li')).toHaveCount(2);
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 123,45');
  const primeira = page
    .locator('#fin-lancamentos li')
    .filter({ hasText: 'Parcela 2/2' });
  await primeira.getByRole('button', { name: 'Editar', exact: true }).click();
  await expect(f.getByLabel('Quantidade de parcelas')).toBeEnabled();
  await expect(f.getByLabel(/Valor total/)).toHaveValue('123,45');
  await expect(page.locator('#fin-data-confirmada')).toContainText('31/10/2030');
  page.once('dialog', d => d.accept());
  await f.getByLabel(/Valor total/).fill('120,00');
  await f
    .getByRole('button', { name: 'Salvar compra', exact: true })
    .click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 120,00');
  expect(
    vendas.financeiro.lancamentos.find((r) => r.parcela === 2).valor_centavos
  ).toBe(6000);
  await primeira.getByRole('button', { name: 'Editar', exact: true }).click();
  const alterada = vendas.financeiro.lancamentos.find((r) => r.parcela === 1);
  alterada.versao++;
  alterada.valor_centavos = 22000;
  await f.getByLabel(/Valor total/).fill('999,00');
  page.once('dialog', d => d.accept());
  await f
    .getByRole('button', { name: 'Salvar compra', exact: true })
    .click();
  await expect(page.locator('#fin-erro-form')).toContainText(
    'mudou em outro acesso'
  );
  expect(alterada.valor_centavos).toBe(22000);
  await f.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await page
    .getByRole('button', { name: 'Atualizar finanças', exact: true })
    .click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 280,00');
  page.once('dialog', (d) => d.accept());
  await primeira.getByRole('button', { name: 'Excluir', exact: true }).click();
  await expect(page.locator('#fin-lancamentos li')).toHaveCount(1);
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 220,00');
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
  await f.getByLabel(/Valor total/).fill('10,00');
  vendas.financeiro.perderResposta = true;
  await f
    .getByRole('button', { name: 'Salvar compra', exact: true })
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
  await f.getByLabel(/Valor total/).fill('10,00');
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function (chave, valor) {
      if (chave.startsWith('feira-financeiro-pendente:'))
        throw new DOMException('Indisponível', 'QuotaExceededError');
      return original.call(this, chave, valor);
    };
  });
  await f
    .getByRole('button', { name: 'Salvar compra', exact: true })
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
    await page.route('**/rest/v1/rpc/sincronizar_desktop*', atrasar);
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
    await page.unroute('**/rest/v1/rpc/sincronizar_desktop*', atrasar);
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
  await f.getByLabel(/Valor total/).fill('18,50');
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

test('desktop web: comprar no dia 09 calcula próxima fatura automaticamente', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const vendas = await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page, 'Ano', '2026-01-01');
  await page.locator('#fin-despesa').click();
  const f = page.locator('#fin-form');
  await dataFinanceira(page, '2026-09-09');
  await f.getByLabel('Descrição', { exact: true }).fill('Compra de exemplo em 3 vezes');
  await f.getByLabel(/Valor total/).fill('30,00');
  await f.getByLabel('Meio de pagamento').selectOption('Cartão de crédito');
  await f.getByLabel('Quantidade de parcelas').fill('3');
  await expect(page.locator('#fin-data-confirmada')).toContainText('09/09/2026');
  await expect(page.locator('#fin-calcular-fatura')).toHaveCount(0);
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

test('compra de maio pode ser editada pela quinta parcela com filtro só de setembro', async ({ page }) => {
  const vendas = await preparar(page);
  await page.getByRole('button', { name: 'Finanças', exact: true }).click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page, 'Mês', '2030-09-01');
  await page.locator('#fin-despesa').click();
  const f = page.locator('#fin-form');
  await dataFinanceira(page, '2030-05-08');
  await f.getByLabel('Descrição', { exact: true }).fill('Compra antiga de exemplo');
  await f.getByLabel(/Valor total/).fill('100,01');
  await f.getByLabel('Meio de pagamento').selectOption('Cartão de crédito');
  await f.getByLabel('Quantidade de parcelas').fill('5');
  await page.locator('#fin-salvar').click();
  await expect(page.locator('#fin-lancamentos li')).toHaveCount(1);
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 20,01');
  const ids = vendas.financeiro.lancamentos.map(r => r.id);
  await page.locator('#fin-lancamentos').getByRole('button', {name:'Editar', exact:true}).click();
  await expect(f.getByLabel(/Valor total/)).toHaveValue('100,01');
  await expect(page.locator('#fin-data-confirmada')).toContainText('08/05/2030');
  await f.getByLabel(/Valor total/).fill('150,00');
  await f.getByLabel('Descrição', { exact:true }).fill('Compra antiga corrigida');
  page.once('dialog', d => d.accept());
  await page.locator('#fin-salvar').click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 30,00');
  expect(vendas.financeiro.lancamentos.map(r => r.id)).toEqual(ids);
  expect(vendas.financeiro.lancamentos.map(r => r.valor_centavos)).toEqual([3000,3000,3000,3000,3000]);
  expect(vendas.financeiro.lancamentos.every(r => r.descricao === 'Compra antiga corrigida')).toBeTruthy();
  await page.locator('#fin-lancamentos').getByRole('button', {name:'Editar', exact:true}).click();
  await f.getByLabel('Quantidade de parcelas').fill('3');
  page.once('dialog', async d => { expect(d.message()).toContain('últimas 2 parcelas'); await d.accept(); });
  await page.locator('#fin-salvar').click();
  await expect(page.locator('#fin-lancamentos li')).toHaveCount(0);
  expect(vendas.financeiro.lancamentos.map(r=>r.id)).toEqual(ids.slice(0,3));
  expect(vendas.financeiro.lancamentos.map(r=>r.valor_centavos)).toEqual([5000,5000,5000]);
});

test('Regressão do fechamento: compra em 09/10 fica no fechamento de outubro e edição não a adia novamente', async ({page})=>{
  const dados=await preparar(page);
  await page.locator('#aba-financas').click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page,'Fechamento','2026-10-01');
  await page.locator('#fin-despesa').click();
  const f=page.locator('#fin-form');
  await dataFinanceira(page,'2026-10-09');
  await f.getByLabel('Descrição',{exact:true}).fill('Compra no fechamento (exemplo)');
  await f.getByLabel(/Valor total/).fill('13');
  await f.getByLabel('Meio de pagamento').selectOption('Cartão de crédito');
  await expect(page.locator('#fin-previa')).toContainText('09/11/2026');
  await page.locator('#fin-salvar').click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 13,00');
  await page.locator('#fin-lancamentos').getByRole('button',{name:'Editar',exact:true}).click();
  await expect(page.locator('#fin-data-confirmada')).toContainText('09/10/2026');
  await f.getByLabel('Descrição',{exact:true}).fill('Compra conferida');
  await page.locator('#fin-salvar').click();
  await expect(page.locator('#fin-lancamentos')).toContainText('Compra conferida');
  expect(dados.financeiro.lancamentos[0].data).toBe('2026-11-09');
  expect(dados.financeiro.lancamentos[0].data_compra).toBe('2026-10-09');
  await consultarFinancas(page,'Fechamento','2026-09-01');
  await expect(page.locator('#fin-lancamentos li')).toHaveCount(0);
});

test('registro antigo preserva a fatura e só converte quando a compra original é informada', async ({page})=>{
  const dados=await preparar(page);
  dados.financeiro.lancamentos.push({id:crypto.randomUUID(),versao:1,tipo:'despesa',data:'2026-11-09',data_compra:null,descricao:'Registro antigo',valor_centavos:1300,meio:'Cartão de crédito',categoria:'Casa',grupo:null,parcela:1,parcelas:1});
  await page.locator('#aba-financas').click();
  await expect(page.locator('#fin-dados')).toBeVisible();
  await consultarFinancas(page,'Fechamento','2026-10-01');
  const editar=()=>page.locator('#fin-lancamentos').getByRole('button',{name:'Editar',exact:true}).click();
  await editar();
  const f=page.locator('#fin-form');
  await expect(f.locator('[name=origem_data]')).toHaveValue('fatura');
  await f.getByLabel('Descrição',{exact:true}).fill('Antigo conferido');
  await page.locator('#fin-salvar').click();
  await expect(page.locator('#fin-dialogo')).not.toBeVisible();
  expect(dados.financeiro.lancamentos[0].data).toBe('2026-11-09');
  await editar();
  await f.locator('[name=origem_data]').selectOption('compra');
  await expect(page.locator('#fin-data-ano')).toHaveValue('');
  await dataFinanceira(page,'2026-10-09');
  await page.locator('#fin-salvar').click();
  await expect(page.locator('#fin-dialogo')).not.toBeVisible();
  expect(dados.financeiro.lancamentos[0].data_compra).toBe('2026-10-09');
  expect(dados.financeiro.lancamentos[0].data).toBe('2026-11-09');
});

test.describe('resumos semanais e preferência de abertura', () => {
  test.use({ timezoneId: 'America/Sao_Paulo' });
  const linhaSemana = (data, dinheiro = 0, pix = 0, cartao = 0) => ({
    id: crypto.randomUUID(), user_id: USER, data, versao: 1,
    dinheiro_centavos: dinheiro, pix_centavos: pix, cartao_centavos: cartao,
  });
  test('semana independe dos filtros, inclui zero, exclui futuro e histórico respeita Análises', async ({page}) => {
    await page.clock.install({time: new Date('2026-10-25T15:00:00-03:00')});
    const vendas = await preparar(page);
    vendas.push(linhaSemana('2025-10-10',10000), linhaSemana('2026-10-19'), linhaSemana('2026-10-23',1010,2020,3030), linhaSemana('2026-10-25',500), linhaSemana('2026-10-26',700));
    await page.locator('#atualizar').click();
    await expect(page.locator('#total')).toHaveText('R$ 72,60');
    await expect(page.locator('#semana-total')).toHaveText('R$ 65,60');
    await expect(page.locator('#semana-dias')).toContainText('3 dias de feira');
    await expect(page.locator('#semana-dinheiro')).toHaveText('R$ 15,10');
    if (process.env.CAPTURAR_WEB_DIR) await page.screenshot({path:`${process.env.CAPTURAR_WEB_DIR}/feira-semana-atual.png`, fullPage:true});
    await page.locator('#tipo').selectOption('Ano'); await page.locator('#ano').fill('2025');
    await page.locator('#filtros button').click();
    await expect(page.locator('#total')).toHaveText('R$ 100,00');
    await expect(page.locator('#semana-total')).toHaveText('R$ 65,60');
    await page.setViewportSize({width:320,height:844});
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.locator('#aba-analises').click();
    await page.locator('#ana-tipo').selectOption('Todas'); await page.locator('#ana-filtros button').click();
    await expect(page.locator('#ana-semanas tr')).toHaveCount(3);
    await expect(page.locator('#ana-semanas')).toContainText('19/10/2026 a 25/10/2026');
    await expect(page.locator('#ana-semanas')).toContainText('R$ 65,60');
    if (process.env.CAPTURAR_WEB_DIR) await page.screenshot({path:`${process.env.CAPTURAR_WEB_DIR}/feira-historico-semanal.png`, fullPage:true});
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.locator('#ana-tipo').selectOption('Ano'); await page.locator('#ana-referencia').fill('2025-01-01');
    await page.locator('#ana-filtros button').click();
    await expect(page.locator('#ana-semanas tr')).toHaveCount(1);
    await expect(page.locator('#ana-semanas')).toContainText('R$ 100,00');
    await page.locator('#sair').click();
    await expect(page.locator('#semana-total')).toHaveText('—');
    await expect(page.locator('#ana-semanas tr')).toHaveCount(0);
  });
  test('preferência vale na próxima abertura, não muda consulta atual e trata bloqueio do armazenamento', async ({page}) => {
    await page.clock.install({time:new Date('2026-10-25T15:00:00-03:00')});
    await preparar(page);
    await page.locator('.preferencias-web summary').click();
    await page.locator('#periodo-inicial').selectOption('Ano atual');
    await expect(page.locator('#preferencia-status')).toContainText('Salvo');
    await expect(page.locator('#tipo')).toHaveValue('Fechamento');
    await page.reload(); await expect(page.locator('#conteudo')).toBeVisible();
    await expect(page.locator('#tipo')).toHaveValue('Ano');
    await expect(page.locator('#periodo')).toHaveText('01/01/2026 a 31/12/2026');
    await expect(page.locator('#ana-tipo')).toHaveValue('Ano');
    await page.locator('.preferencias-web summary').click();
    await page.evaluate(() => {
      const salvar = Storage.prototype.setItem;
      Storage.prototype.setItem = function(k,v) { if(k === 'feira-periodo-inicial') throw Error('bloqueado'); return salvar.call(this,k,v); };
    });
    await page.locator('#periodo-inicial').selectOption('Mês atual');
    await expect(page.locator('#preferencia-status')).toContainText('não permitiu salvar');
    await expect(page.locator('#tipo')).toHaveValue('Ano');
    expect(await page.evaluate(() => localStorage.getItem('feira-periodo-inicial'))).toBe('Ano atual');
  });
  test('domingo vira segunda sem perder formulário ou filtro em preparação', async ({page}) => {
    await page.clock.install({time:new Date('2026-10-25T23:59:40-03:00')});
    const vendas = await preparar(page);
    vendas.push(linhaSemana('2026-10-25',500),linhaSemana('2026-10-26',700),linhaSemana('2026-10-30',900));
    await page.locator('#atualizar').click();
    await expect(page.locator('#semana-total')).toHaveText('R$ 5,00');
    await page.locator('#ano').fill('2025');
    await page.locator('#nova').click();
    await page.getByLabel('Dinheiro', {exact:true}).fill('123,45');
    await page.clock.fastForward(31000);
    await expect(page.locator('#semana-total')).toHaveText('—');
    await expect(page.getByLabel('Dinheiro', {exact:true})).toHaveValue('123,45');
    await page.getByRole('button',{name:'Cancelar',exact:true}).click();
    await page.clock.fastForward(30100);
    await expect(page.locator('#semana-total')).toHaveText('R$ 7,00');
    await expect(page.locator('#semana-dias')).toContainText('1 dia de feira');
    await expect(page.locator('#semana-intervalo')).toContainText('26/10/2026 a 01/11/2026');
    await expect(page.locator('#ano')).toHaveValue('2025');
    await expect(page.locator('#periodo')).toHaveText('10/10/2026 a 09/11/2026');
    await expect(page.locator('#total')).toHaveText('R$ 21,00');
  });
});

for (const largura of [320, 390, 1280]) {
  test(`revisão visual: áreas e ajudas acessíveis em ${largura}px`, async ({ page }) => {
    await page.setViewportSize({ width: largura, height: 900 });
    await preparar(page);
    for (const area of ['vendas', 'analises', 'financas']) {
      await page.locator(`#aba-${area}`).click();
      await expect(page.locator(`#area-${area}`)).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const ajuda = page.locator(`#area-${area} .ajuda-inline`).first();
      await ajuda.locator('summary').focus();
      await page.keyboard.press('Enter');
      await expect(ajuda).toHaveAttribute('open', '');
      await expect(ajuda.locator('p')).toBeVisible();
      await ajuda.locator('summary').click();
      if (process.env.CAPTURAR_WEB_DIR && largura === 390)
        await page.screenshot({ path: `${process.env.CAPTURAR_WEB_DIR}/revisao-${area}.png`, fullPage: true });
    }
  });
}

test('histórico: paginação, busca local, filtro semanal e exportação mantêm escopos distintos', async ({ page }) => {
  const dados = await preparar(page);
  for (let i = 1; i <= 25; i++) dados.push({ id: String(i), data: `2026-10-${String(i).padStart(2, '0')}`, dinheiro_centavos: i === 23 ? 12345 : 0, pix_centavos: 0, cartao_centavos: 0, versao: 1 });
  await page.locator('#tipo').selectOption('Todas');
  await page.getByRole('button', { name: 'Aplicar', exact: true }).click();
  await expect(page.locator('#quantidade')).toHaveText('25');
  await expect(page.locator('#vendas li')).toHaveCount(12);
  await expect(page.locator('#historico-pagina')).toHaveText('Página 1 de 3');
  await page.locator('#historico-proxima').click();
  await expect(page.locator('#historico-pagina')).toHaveText('Página 2 de 3');
  await page.locator('#atualizar').click();
  await expect(page.locator('#historico-pagina')).toHaveText('Página 2 de 3');
  await page.locator('#busca-vendas').fill('123,45');
  await expect(page.locator('#vendas li')).toHaveCount(1);
  await expect(page.locator('#total')).toHaveText('R$ 123,45');
  await expect(page.locator('#quantidade')).toHaveText('25');
  const download = page.waitForEvent('download');
  await page.locator('#exportar-csv').click();
  const arquivo = await download;
  const fs = await import('node:fs/promises');
  const csv = await fs.readFile(await arquivo.path(), 'utf8');
  expect(csv).toContain('01/10/2026');
  expect(csv).toContain('"Registros / dias de feira";"25"');
  await page.locator('#busca-vendas').fill('nada');
  await expect(page.locator('#vazio')).toHaveText('Nenhuma venda encontrada nesta busca.');
  await page.locator('#busca-vendas').fill('');
  await page.locator('[name="dia-semana"][value="6"]').check();
  await page.locator('#atualizar').click();
  await expect(page.locator('#quantidade')).toHaveText('25');
  await page.getByRole('button', { name: 'Aplicar', exact: true }).click();
  await expect(page.locator('#quantidade')).toHaveText('4');
  await expect(page.locator('#vendas li')).toHaveCount(4);
  await expect(page.locator('#total')).toHaveText('R$ 0,00');
  await expect(page.locator('#periodo')).toContainText('Domingo');
  await page.locator('[name="dia-semana"][value="6"]').uncheck();
  await page.locator('[name="dia-semana"][value="4"]').check();
  await page.locator('#atualizar').click();
  await expect(page.locator('#quantidade')).toHaveText('4');
  await expect(page.locator('#total')).toHaveText('R$ 0,00');
  await page.getByRole('button', { name: 'Aplicar', exact: true }).click();
  await expect(page.locator('#total')).toHaveText('R$ 123,45');
  await page.locator('#busca-vendas').fill('sexta');
  await page.locator('#sair').click();
  await expect(page.locator('#vendas li')).toHaveCount(0);
  await expect(page.locator('#busca-vendas')).toHaveValue('');
  await expect(page.locator('[name="dia-semana"]:checked')).toHaveCount(0);
});


test('histórico: editar e excluir na última página usa o registro correto e ajusta a navegação', async ({ page }) => {
  const dados = await preparar(page);
  for (let i = 1; i <= 13; i++) dados.push({ id: String(i), data: `2030-10-${String(i).padStart(2, '0')}`, dinheiro_centavos: 0, pix_centavos: 0, cartao_centavos: 0, versao: 1 });
  await page.locator('#tipo').selectOption('Todas');
  await page.getByRole('button', { name: 'Aplicar', exact: true }).click();
  await page.locator('#historico-proxima').click();
  await expect(page.locator('#vendas li')).toHaveCount(1);
  await expect(page.locator('#vendas li')).toContainText('01/10/2030');
  await page.locator('#vendas').getByRole('button', { name: 'Editar', exact: true }).click();
  await expect(page.getByLabel('Data da feira')).toHaveValue('2030-10-01');
  await page.getByLabel('Pix', { exact: true }).fill('1,50');
  await page.getByRole('button', { name: 'Salvar venda' }).click();
  await expect(page.locator('#historico-pagina')).toHaveText('Página 2 de 2');
  await expect(page.locator('#vendas li')).toContainText('R$ 1,50');
  if (process.env.CAPTURAR_WEB_DIR) {
    await page.locator('#area-vendas .historico').scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${process.env.CAPTURAR_WEB_DIR}/historico-pagina.png` });
    await page.locator('#filtros').scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${process.env.CAPTURAR_WEB_DIR}/filtro-dias.png` });
  }
  page.once('dialog', dialog => dialog.accept());
  await page.locator('#vendas').getByRole('button', { name: 'Excluir', exact: true }).click();
  await expect(page.locator('#quantidade')).toHaveText('12');
  await expect(page.locator('#historico-paginacao')).toBeHidden();
  await expect(page.locator('#vendas li')).toHaveCount(12);
  expect(dados.some(r => r.data === '2030-10-01')).toBe(false);
});

test('finanças: busca, cronologia da compra e filtro de despesas por pagamento', async ({ page }) => {
  const dados = await preparar(page);
  dados.push({ id: 'v', data: '2026-11-01', dinheiro_centavos: 50000, pix_centavos: 0, cartao_centavos: 0, versao: 1 });
  const r = (id, tipo, meio, valor, compra = null, data = '2026-11-09') => ({ id, tipo, meio, data, data_compra: compra, descricao: id, valor_centavos: valor, categoria: 'Casa', parcela: 1, parcelas: 1, versao: 1 });
  dados.financeiro.lancamentos.push(r('Mercado terça', 'despesa', 'Cartão de crédito', 30000, '2026-10-20'), { ...r('Compra antiga', 'despesa', 'Cartão de crédito', 5000, '2026-09-01'), created_at: '2099-12-31' }, r('Dinheiro', 'despesa', 'Dinheiro', 40000, null, '2026-11-01'), r('Legado', 'despesa', 'Cartão de crédito', 100), r('Taxa', 'taxa', 'Outro', 1000));
  await page.locator('#aba-financas').click();
  await consultarFinancas(page, 'Mês', '2026-11-01');
  const linhas = page.locator('#fin-lancamentos li');
  await expect(linhas).toHaveCount(5);
  await expect(linhas.nth(1)).toContainText('Despesa em 01/11/2026');
  await expect(linhas.nth(2)).toContainText('Compra em 20/10/2026');
  await expect(linhas.nth(2)).toContainText('Fatura em 09/11/2026');
  await expect(linhas.nth(4)).toContainText('Compra: data não informada');
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 751,00');
  for (const termo of ['20/10/2026', '300,00', '300.00', 'mercado']) {
    await page.locator('#fin-busca').fill(termo);
    await expect(linhas).toHaveCount(1);
    await expect(linhas).toContainText('Mercado terça');
    await expect(page.locator('#fin-despesas')).toHaveText('R$ 751,00');
  }
  await page.locator('#fin-busca').fill('terca');
  await expect(linhas).toHaveCount(2);
  await page.locator('#fin-busca').fill('');
  if (process.env.CAPTURAR_WEB_DIR) {
    await page.locator('#fin-busca').evaluate(e => { e.blur(); window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 50); });
    await page.screenshot({ path: `${process.env.CAPTURAR_WEB_DIR}/financas-compra-busca.png` });
  }
  await page.locator('#fin-meio').selectOption('Cartão de crédito');
  await page.locator('#fin-atualizar').click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 751,00');
  await page.locator('#fin-consultar').click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 351,00');
  await expect(page.locator('#fin-bruto')).toHaveText('R$ 500,00');
  await expect(page.locator('#fin-taxas')).toHaveText('R$ 10,00');
  await expect(page.locator('#fin-saldo')).toHaveText('R$ 139,00');
  await expect(page.locator('#fin-aviso')).toContainText('não representa todas as despesas');
  await page.locator('#fin-busca').fill('inexistente');
  await expect(linhas).toHaveCount(0);
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 351,00');
  await page.locator('#fin-busca').fill('');
  await page.locator('#fin-meio').selectOption('Dinheiro');
  await page.locator('#fin-consultar').click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 400,00');
  if (process.env.CAPTURAR_WEB_DIR) {
    await page.locator('#fin-filtros').scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${process.env.CAPTURAR_WEB_DIR}/financas-meio.png` });
  }
  await page.locator('#fin-meio').selectOption('Todos');
  await page.locator('#fin-consultar').click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 751,00');
  await page.locator('#fin-busca').fill('mercado');
  await page.locator('#sair').click();
  await expect(page.locator('#fin-busca')).toHaveValue('');
  await expect(page.locator('#fin-meio')).toHaveValue('Todos');
});

test('exportação financeira gera JSON/CSV do histórico ou consulta sem aplicar busca nem filtros pendentes', async ({ page }) => {
  const dados = await preparar(page);
  const l = (id, data, meio) => ({ id, tipo: 'despesa', data, data_compra: meio === 'Cartão de crédito' ? '2026-09-09' : null, descricao: id, valor_centavos: 1001, meio, categoria: 'Casa', grupo: 'g', parcela: 1, parcelas: 2, versao: 3, user_id: USER });
  dados.financeiro.lancamentos.push(l('outubro', '2026-10-09', 'Cartão de crédito'), l('novembro', '2026-11-09', 'Cartão de crédito'), l('dinheiro', '2026-11-02', 'Dinheiro'));
  await page.locator('#aba-financas').click();
  await consultarFinancas(page, 'Mês', '2026-11-01');
  await page.locator('#fin-meio').selectOption('Cartão de crédito');
  await page.locator('#fin-consultar').click();
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 10,01');
  await page.locator('#fin-busca').fill('inexistente');
  await expect(page.locator('#fin-lancamentos li')).toHaveCount(0);
  await page.locator('#fin-meio').selectOption('Dinheiro');
  await page.locator('.exportacao-financeira > summary').click();
  const fs = await import('node:fs/promises');
  const download = async (botao) => {
    const aguardando = page.waitForEvent('download');
    await page.locator(botao).click();
    const arquivo = await aguardando;
    return fs.readFile(await arquivo.path(), 'utf8');
  };
  const completo = JSON.parse(await download('#fin-exportar-json'));
  expect(completo.escopo).toBe('historico_completo');
  expect(completo.financeiro_lancamentos).toHaveLength(3);
  expect(completo.financeiro_lancamentos[0].user_id).toBeUndefined();
  expect(completo.consultado_em).toBeTruthy();
  await page.locator('#fin-exportar-escopo').selectOption('consulta_aplicada');
  const consulta = JSON.parse(await download('#fin-exportar-json'));
  expect(consulta.consulta.meio).toBe('Cartão de crédito');
  expect(consulta.financeiro_lancamentos.map(l => l.id)).toEqual(['novembro']);
  const csv = await download('#fin-exportar-csv');
  expect(csv).toContain('"novembro"'); expect(csv).toContain('"10,01"');
  expect(csv).not.toContain('"outubro"'); expect(csv).not.toContain('"dinheiro"');
  await expect(page.locator('#fin-despesas')).toHaveText('R$ 10,01');
  if (process.env.CAPTURAR_WEB_DIR) {
    await page.locator('.exportacao-financeira').scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${process.env.CAPTURAR_WEB_DIR}/exportacao-financeira.png` });
  }
  await page.locator('#sair').click();
  await expect(page.locator('#fin-exportar-json')).toBeDisabled();
});

async function prepararPlanoCorrecao(page) {
  const dados = await preparar(page);
  const uuid = i => `10000000-0000-4000-8000-${String(i).padStart(12, '0')}`;
  const rows = [1,2,3,4].map(i => ({ id: uuid(i), versao:1, tipo:'despesa', data:i%2?'2026-10-09':'2026-11-09', data_compra:null, descricao:'Compra fictícia', valor_centavos:100, meio:'Cartão de crédito', categoria:'Casa', grupo:uuid(i<=2?10:11), parcela:i%2?1:2, parcelas:2 }));
  dados.financeiro.lancamentos.push(...rows, {...rows[0],id:uuid(99),grupo:null,parcela:1,parcelas:1,meio:'Dinheiro',descricao:'Preservada',valor_centavos:900});
  const campos = ['tipo','data','data_compra','descricao','valor_centavos','meio','categoria','grupo','parcela','parcelas'];
  const selecionar = r => Object.fromEntries(campos.map(k=>[k,r[k]]));
  const plano = { formato:'gestao-da-feira-correcoes',versao_formato:1,verificacoes:rows.map(r=>({id:r.id,versao:r.versao,campos:selecionar(r)})),alteracoes:rows.map((r,i)=>({tabela:'financeiro_lancamentos',acao:i<2?'editar':'excluir',id:r.id,versao:r.versao,dados:i<2?selecionar(r):null})) };
  await page.locator('#aba-financas').click();
  await consultarFinancas(page,'Mês','2026-11-01');
  await page.locator('#fin-correcoes > summary').click();
  await page.locator('#fin-correcoes-arquivo').setInputFiles({name:'plano.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(plano))});
  return {dados,plano,uuid};
}

test('correções: prévia exige cópia e confirmação e recusa reaplicação',async({page})=>{
  const {dados,plano,uuid}=await prepararPlanoCorrecao(page);
  await expect(page.locator('#fin-correcoes-aplicar')).toBeDisabled();
  await page.locator('#fin-correcoes-conferir').click();
  await expect(page.locator('#fin-correcoes-status')).toContainText('2 exclusões e 2 atualizações');
  expect(dados.financeiro.lancamentos).toHaveLength(5);
  await expect(page.locator('#fin-correcoes-guardada')).toBeDisabled();
  const download = page.waitForEvent('download');
  await page.locator('#fin-correcoes-copia').click();
  const arquivo=await download;
  const fs=await import('node:fs/promises');
  const copia=JSON.parse(await fs.readFile(await arquivo.path(),'utf8'));
  expect(copia.financeiro_lancamentos).toHaveLength(5);
  await page.locator('#fin-correcoes-guardada').check();
  if (process.env.CAPTURAR_WEB_DIR) {
    await page.locator('#fin-correcoes').evaluate(e => window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 15));
    await page.screenshot({path:`${process.env.CAPTURAR_WEB_DIR}/correcoes-financeiras.png`});
  }
  const cancelado = new Promise(resolve => page.once('dialog', async d => { await d.dismiss(); resolve(); }));
  await page.locator('#fin-correcoes-aplicar').click();
  await cancelado;
  await expect(page.locator('#fin-correcoes-aplicar')).toBeEnabled();
  expect(dados.financeiro.lancamentos).toHaveLength(5);
  page.once('dialog',d=>d.accept());
  await page.locator('#fin-correcoes-aplicar').click();
  await expect.poll(()=>dados.financeiro.lancamentos.length).toBe(3);
  expect(dados.financeiro.lancamentos.map(r=>r.id).sort()).toEqual([uuid(1),uuid(2),uuid(99)].sort());
  expect(dados.financeiro.lancamentos.find(r=>r.id===uuid(99)).valor_centavos).toBe(900);
  await page.locator('#fin-correcoes-arquivo').setInputFiles({name:'plano.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(plano))});
  await page.locator('#fin-correcoes-conferir').click();
  await expect(page.locator('#fin-correcoes-status')).toContainText('Plano não conferido');
  await expect(page.locator('#fin-correcoes-aplicar')).toBeDisabled();
});

test('correções: mudança após prévia bloqueia o lote inteiro antes de enviar',async({page})=>{
  const {dados}=await prepararPlanoCorrecao(page);
  await page.locator('#fin-correcoes-conferir').click();
  const download=page.waitForEvent('download');
  await page.locator('#fin-correcoes-copia').click();await download;
  await page.locator('#fin-correcoes-guardada').check();
  dados.financeiro.lancamentos[0].versao++;
  await page.locator('#fin-correcoes-aplicar').click();
  await expect(page.locator('#fin-correcoes-status')).toContainText('Os registros mudaram');
  expect(dados.financeiro.lancamentos).toHaveLength(5);
  await expect(page.locator('#fin-correcoes-aplicar')).toBeDisabled();
});

test('correções: resposta perdida retoma o mesmo recibo sem repetir exclusões',async({page})=>{
  const {dados}=await prepararPlanoCorrecao(page);
  await page.locator('#fin-correcoes-conferir').click();
  const download=page.waitForEvent('download');
  await page.locator('#fin-correcoes-copia').click();await download;
  await page.locator('#fin-correcoes-guardada').check();
  dados.financeiro.perderResposta=true;
  page.once('dialog',d=>d.accept());
  await page.locator('#fin-correcoes-aplicar').click();
  await expect(page.locator('#fin-status')).toContainText('Não foi possível confirmar');
  expect(dados.financeiro.lancamentos).toHaveLength(3);
  const versoes=dados.financeiro.lancamentos.map(r=>r.versao);
  await page.locator('#fin-atualizar').click();
  await expect(page.locator('#fin-status')).toContainText('Dados consultados');
  expect(dados.financeiro.lancamentos).toHaveLength(3);
  expect(dados.financeiro.lancamentos.map(r=>r.versao)).toEqual(versoes);
});

test('correções v2: inclui parcela faltante, calcula 18 parcelas e recusa a segunda aplicação',async({page})=>{
  const dados=await preparar(page);
  const uuid=i=>`20000000-0000-4000-8000-${String(i).padStart(12,'0')}`;
  const grupo=uuid(99),campos=['tipo','data','data_compra','descricao','valor_centavos','meio','categoria','grupo','parcela','parcelas'];
  const base={tipo:'despesa',data_compra:'2030-03-12',descricao:'Compra em dezoito parcelas',valor_centavos:1000,meio:'Cartão de crédito',categoria:'Casa',grupo,parcelas:18};
  const rows=Array.from({length:17},(_,i)=>{const parcela=i+2,m=2030*12+3+parcela-1;return {id:uuid(parcela),versao:1,...base,parcela,valor_centavos:parcela===18?1001:1000,data:`${Math.floor(m/12)}-${String(m%12+1).padStart(2,'0')}-09`};});
  dados.financeiro.lancamentos.push(...rows);
  const selecionar=r=>Object.fromEntries(campos.map(k=>[k,r[k]]));
  const plano={formato:'gestao-da-feira-correcoes',versao_formato:2,faturas:[{grupo,data_compra:'2030-03-12',total_centavos:18001,parcelas:18}],
    verificacoes:[...rows.map(r=>({id:r.id,versao:r.versao,campos:selecionar(r)})),{id:uuid(1),versao:null,campos:null}],
    alteracoes:[...rows.map(r=>({tabela:'financeiro_lancamentos',acao:'editar',id:r.id,versao:r.versao,dados:selecionar(r)})),{tabela:'financeiro_lancamentos',acao:'inserir',id:uuid(1),versao:null,dados:{...base,parcela:1,data:'2030-04-09',valor_centavos:1000}}]};
  await page.locator('#aba-financas').click();await consultarFinancas(page,'Ano','2030-01-01');
  await page.locator('#fin-correcoes > summary').click();
  const arquivo={name:'plano-v2.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(plano))};
  await page.locator('#fin-correcoes-arquivo').setInputFiles(arquivo);
  await page.locator('#fin-correcoes-conferir').click();
  await expect(page.locator('#fin-correcoes-status')).toContainText('1 parcela faltante');
  await expect(page.locator('#fin-correcoes-previa')).toContainText('Incluir parcela faltante');
  const baixar=page.waitForEvent('download');await page.locator('#fin-correcoes-copia').click();await baixar;
  await page.locator('#fin-correcoes-guardada').check();page.once('dialog',d=>d.accept());
  await page.locator('#fin-correcoes-aplicar').click();
  await expect.poll(()=>dados.financeiro.lancamentos.length).toBe(18);
  expect(dados.financeiro.lancamentos.reduce((s,r)=>s+r.valor_centavos,0)).toBe(18001);
  expect(dados.financeiro.lancamentos.find(r=>r.parcela===1).data).toBe('2030-04-09');
  await page.locator('#fin-correcoes-arquivo').setInputFiles(arquivo);await page.locator('#fin-correcoes-conferir').click();
  await expect(page.locator('#fin-correcoes-status')).toContainText('Plano não conferido');
});

test('correções v3: inclui compra da fatura com cópia, preserva Pix e recusa reaplicação',async({page})=>{
  const dados=await preparar(page);
  const id='30000000-0000-4000-8000-000000000001';
  const pix={id:'30000000-0000-4000-8000-000000000002',versao:1,tipo:'despesa',data:'2031-03-16',data_compra:null,descricao:'Pix fictício',valor_centavos:200,meio:'Pix',categoria:'Casa',grupo:null,parcela:1,parcelas:1};
  dados.financeiro.lancamentos.push(pix);
  const novo={...pix,data:'2031-04-09',data_compra:'2031-03-16',descricao:'Compra fictícia no cartão',meio:'Cartão de crédito'};
  delete novo.id;delete novo.versao;
  const plano={formato:'gestao-da-feira-correcoes',versao_formato:3,totais_preservados:[],
    verificacoes:[{id,versao:null,campos:null}],alteracoes:[{tabela:'financeiro_lancamentos',acao:'inserir',id,versao:null,dados:novo}],
    conciliacoes:[{referencia:'Fatura fictícia',inicio:'2031-03-10',fim:'2031-04-09',total_centavos:200,completa:true,movimentos:[{id,data_compra:novo.data_compra,valor_centavos:200,parcela:1,parcelas:1}]}]};
  await page.locator('#aba-financas').click();await consultarFinancas(page,'Ano','2031-01-01');
  await page.locator('#fin-correcoes > summary').click();
  const arquivo={name:'plano-v3.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(plano))};
  await page.locator('#fin-correcoes-arquivo').setInputFiles(arquivo);await page.locator('#fin-correcoes-conferir').click();
  await expect(page.locator('#fin-correcoes-previa')).toContainText('Fatura completa');
  await expect(page.locator('#fin-correcoes-previa')).toContainText('Incluir despesa conferida');
  await expect(page.locator('#fin-correcoes-aplicar')).toBeDisabled();
  expect(dados.financeiro.lancamentos).toHaveLength(1);
  const baixar=page.waitForEvent('download');await page.locator('#fin-correcoes-copia').click();await baixar;
  await page.locator('#fin-correcoes-guardada').check();page.once('dialog',d=>d.accept());await page.locator('#fin-correcoes-aplicar').click();
  await expect.poll(()=>dados.financeiro.lancamentos.length).toBe(2);
  expect(dados.financeiro.lancamentos.find(r=>r.id===pix.id)).toEqual(pix);
  await page.locator('#fin-correcoes-arquivo').setInputFiles(arquivo);await page.locator('#fin-correcoes-conferir').click();
  await expect(page.locator('#fin-correcoes-status')).toContainText('Plano não conferido');
});
