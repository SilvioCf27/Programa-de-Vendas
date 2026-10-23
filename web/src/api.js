import { definirFechamentos, validarFechamentos, estadoFechamentos } from './fechamento.js';
export function criarApi(cliente) {
  async function lerFechamentos() {
    const { data, error } = await cliente.rpc('consultar_fechamentos');
    if (error?.code === 'PGRST202' && !estadoFechamentos().versao) return null;
    if (error) throw error;
    const config = validarFechamentos(data);
    definirFechamentos(config);
    return config;
  }
  return {
    fechamentos: lerFechamentos,
    async salvarFechamento(versao, vigencia, dia) {
      const { data, error } = await cliente.rpc('salvar_fechamento', { versao_esperada: versao, vigencia, dia });
      if (error) throw error;
      const config = validarFechamentos(data); definirFechamentos(config); return config;
    },
    async autorizado() {
      const { data, error } = await cliente.rpc('usuario_autorizado');
      if (error) throw error;
      return data === true;
    },
    async listar({ inicio, fim }) {
      const resultado = [];
      for (let offset = 0; ; offset += 500) {
        let q = cliente
          .from('vendas')
          .select('*')
          .order('data', { ascending: false })
          .range(offset, offset + 499);
        if (inicio) q = q.gte('data', inicio).lte('data', fim);
        const { data, error } = await q;
        if (error) throw error;
        resultado.push(...data);
        if (data.length < 500) return resultado;
      }
    },
    async financeiro() {
      const { data, error } = await cliente.rpc('sincronizar_desktop', {
        alteracoes: [],
        operacao_id: null,
      });
      if (error) throw error;
      if (
        data?.protocolo !== 1 ||
        !['vendas', 'financeiro_lancamentos', 'financeiro_taxas_anuais'].every(
          (t) => Array.isArray(data?.dados?.[t])
        )
      )
        throw Error('Resposta financeira incompleta.');
      return data.dados;
    },
    async aplicarFinanceiro(lote) {
      const { data, error } = await cliente.rpc('sincronizar_desktop', lote);
      if (error) throw error;
      if (data?.protocolo !== 1 || data.operacao_id !== lote.operacao_id)
        throw Error('Envio não confirmado.');
      return data;
    },
    async salvar(venda, anterior = null) {
      const q = anterior
        ? cliente
            .from('vendas')
            .update(venda)
            .eq('id', anterior.id)
            .eq('versao', anterior.versao)
        : cliente.from('vendas').insert(venda);
      const { data, error } = await q.select();
      if (error) throw error;
      if (data.length !== 1) throw { conflito: true };
      return data[0];
    },
    async excluir(venda) {
      const { data, error } = await cliente
        .from('vendas')
        .delete()
        .eq('id', venda.id)
        .eq('versao', venda.versao)
        .select('id');
      if (error) throw error;
      if (data.length !== 1) throw { conflito: true };
    },
  };
}
