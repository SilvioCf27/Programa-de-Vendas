import test from 'node:test';
import assert from 'node:assert/strict';
import { criarAtualizacao } from '../src/atualizacao.js';
function preparar() {
  const tarefas = new Map();
  let id = 0;
  const estado = { disponivel: true, ocupado: false, chamadas: 0, avisos: [] };
  const relogio = {
    setTimeout(fn, ms) {
      tarefas.set(++id, { fn, ms });
      return id;
    },
    clearTimeout(id) {
      tarefas.delete(id);
    },
  };
  const agenda = criarAtualizacao({
    relogio,
    disponivel: () => estado.disponivel,
    ocupado: () => estado.ocupado,
    atualizar: async () => {
      estado.chamadas++;
      return true;
    },
    informar: (ok) => estado.avisos.push(ok),
  });
  const disparar = async () => {
    const [id, t] = tarefas.entries().next().value;
    tarefas.delete(id);
    await t.fn();
    return t.ms;
  };
  return { estado, agenda, tarefas, disparar };
}
test('consulta repetidamente a cada minuto e suspende consultas offline ou em segundo plano', async () => {
  const { estado, agenda, disparar } = preparar();
  agenda.iniciar();
  for (let i = 0; i < 3; i++) assert.equal(await disparar(), 60000);
  assert.equal(estado.chamadas, 3);
  estado.disponivel = false;
  await disparar();
  assert.equal(estado.chamadas, 3);
  estado.disponivel = true;
  await agenda.verificar();
  assert.equal(estado.chamadas, 4);
});
test('formulários e operações em curso adiam sem escrever nem sobrepor consultas', async () => {
  const { estado, agenda, disparar, tarefas } = preparar();
  agenda.iniciar();
  estado.ocupado = true;
  await disparar();
  assert.equal(estado.chamadas, 0);
  estado.ocupado = false;
  assert.equal(await disparar(), 5000);
  assert.equal(estado.chamadas, 1);
  agenda.parar();
  assert.equal(tarefas.size, 0);
});
test('logout durante requisição descarta aviso e não reinicia o agendamento', async () => {
  let concluir,
    consultas = 0;
  const avisos = [],
    tarefas = new Map();
  const agenda = criarAtualizacao({
    relogio: {
      setTimeout(fn, ms) {
        tarefas.set(1, { fn, ms });
        return 1;
      },
      clearTimeout() {
        tarefas.clear();
      },
    },
    disponivel: () => true,
    ocupado: () => false,
    atualizar: () => {
      consultas++;
      return new Promise((r) => (concluir = r));
    },
    informar: (v) => avisos.push(v),
  });
  agenda.iniciar();
  const consulta = agenda.verificar();
  await agenda.verificar();
  assert.equal(consultas, 1);
  agenda.parar();
  concluir(true);
  await consulta;
  assert.deepEqual(avisos, []);
  assert.equal(tarefas.size, 0);
});
