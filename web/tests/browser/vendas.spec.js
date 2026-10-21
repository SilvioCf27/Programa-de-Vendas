import { test, expect } from '@playwright/test';

const USER = '11111111-1111-4111-8111-111111111111';
function token() {
  const codificar = (obj) =>
    Buffer.from(JSON.stringify(obj)).toString('base64url');
  return `${codificar({ alg: 'HS256', typ: 'JWT' })}.${codificar({ sub: USER, role: 'authenticated', exp: Math.floor(Date.now() / 1000) + 3600 })}.teste`;
}
async function preparar(page) {
  const vendas = [];
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
