export function criarApi(cliente) {
  return {
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
