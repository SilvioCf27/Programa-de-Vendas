// Consulta periódica da área visível; sem gravações ou dependência de Realtime.
export function criarAtualizacao({
  relogio = globalThis,
  disponivel,
  ocupado,
  atualizar,
  informar,
}) {
  let tarefa = null,
    ativa = false,
    executando = false,
    geracao = 0;
  function agendar(atraso) {
    if (tarefa !== null) relogio.clearTimeout(tarefa);
    tarefa = ativa ? relogio.setTimeout(verificar, atraso) : null;
  }
  async function verificar() {
    if (!ativa) return;
    if (tarefa !== null) relogio.clearTimeout(tarefa);
    tarefa = null;
    if (!disponivel()) {
      agendar(60000);
      return;
    }
    if (executando || ocupado()) {
      agendar(5000);
      return;
    }
    executando = true;
    const atual = geracao;
    try {
      const sucesso = await atualizar();
      if (ativa && atual === geracao) informar(sucesso !== false);
    } catch {
      if (ativa && atual === geracao) informar(false);
    } finally {
      executando = false;
      if (ativa && atual === geracao) agendar(60000);
    }
  }
  return {
    verificar,
    iniciar() {
      ativa = true;
      geracao++;
      agendar(60000);
    },
    parar() {
      ativa = false;
      geracao++;
      if (tarefa !== null) relogio.clearTimeout(tarefa);
      tarefa = null;
    },
  };
}
