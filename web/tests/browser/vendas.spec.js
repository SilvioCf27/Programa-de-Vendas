import { test, expect } from '@playwright/test';

const USER = '11111111-1111-4111-8111-111111111111';
function token() {
  const codificar = (obj) =>
    Buffer.from(JSON.stringify(obj)).toString('base64url');
  return `${codificar({ alg: 'HS256', typ: 'JWT' })}.${codificar({ sub: USER, role: 'authenticated', exp: Math.floor(Date.now() / 1000) + 3600 })}.teste`;
}
async function preparar(page) {
  const vendas = [];
  const financeiro = { lancamentos: [], anuais: [] };
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

async function consultarFinancas(
  page,
  tipo = 'Mês',
  referencia = '2030-10-01'
) {
  await page.locator('#fin-tipo').selectOption(tipo);
  await page.locator('#fin-referencia').fill(referencia);
  await page.locator('#fin-filtros button').click();
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
  await f.getByLabel('Data de pagamento ou vencimento').fill('2030-10-31');
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
    .getByRole('button', { name: '+ Ajuste anual', exact: true })
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
    .getByRole('button', { name: '+ Taxa diária', exact: true })
    .click();
  const f = page.locator('#fin-form');
  await f.getByLabel('Data de pagamento ou vencimento').fill('2030-01-15');
  await f.getByLabel('Descrição', { exact: true }).fill('Taxa fictícia');
  await f.getByLabel('Valor de cada parcela ou lançamento').fill('1,00');
  await f
    .getByRole('button', { name: 'Salvar lançamento', exact: true })
    .click();
  await expect(page.locator('#fin-erro-form')).toContainText('ajuste anual');
  await f.getByRole('button', { name: 'Cancelar', exact: true }).click();
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
  await f.getByLabel('Data de pagamento ou vencimento').fill('2030-10-16');
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
  await f.getByLabel('Data de pagamento ou vencimento').fill('2030-10-16');
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
