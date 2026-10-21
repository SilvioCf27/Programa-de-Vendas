import { test } from 'node:test';
import assert from 'node:assert/strict';
import { criarApi } from '../src/api.js';

test('consulta busca mais de mil registros sem truncar os totais', async () => {
  const linhas = Array.from({ length: 1203 }, (_, i) => ({ id: `venda-${i}` }));
  const intervalos = [];
  const cliente = {
    from() {
      let inicio, fim;
      const q = {
        select() {
          return q;
        },
        order() {
          return q;
        },
        gte() {
          return q;
        },
        lte() {
          return q;
        },
        range(a, b) {
          inicio = a;
          fim = b;
          intervalos.push([a, b]);
          return q;
        },
        then(resolve) {
          resolve({ data: linhas.slice(inicio, fim + 1), error: null });
        },
      };
      return q;
    },
  };
  const resultado = await criarApi(cliente).listar({
    inicio: '2030-01-01',
    fim: '2030-12-31',
  });
  assert.deepEqual(resultado, linhas);
  assert.equal(intervalos.length, 3);
});
test('falha numa página recusa a consulta inteira, sem devolver um total parcial', async () => {
  const cliente = {
    from() {
      let inicio;
      const q = {
        select() {
          return q;
        },
        order() {
          return q;
        },
        range(a) {
          inicio = a;
          return q;
        },
        then(resolve) {
          resolve(
            inicio === 0
              ? { data: Array(500).fill({ id: 'teste' }) }
              : { error: Error('falha de rede') }
          );
        },
      };
      return q;
    },
  };
  await assert.rejects(
    criarApi(cliente).listar({ inicio: null, fim: null }),
    /falha de rede/
  );
});
test('salvar uma edição exige que a versão anterior ainda exista', async () => {
  const filtros = [];
  const q = {
    eq(campo, valor) {
      filtros.push([campo, valor]);
      return q;
    },
    select() {
      return Promise.resolve({ data: [], error: null });
    },
  };
  const api = criarApi({
    from() {
      return {
        update() {
          return q;
        },
      };
    },
  });
  await assert.rejects(
    api.salvar({ pix_centavos: 100 }, { id: 'teste', versao: 3 }),
    (erro) => erro.conflito === true
  );
  assert.deepEqual(filtros, [
    ['id', 'teste'],
    ['versao', 3],
  ]);
});
