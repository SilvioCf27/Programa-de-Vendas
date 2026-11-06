/** Texto completo preservado; ajuda nativa funciona por toque e teclado. */
export function organizarAjudas(documento = document) {
  for (const [seletor, titulo] of [
    ['.exportacao-web + p.nota', 'O que será exportado?'],
    ['.historico > p.nota', 'Sobre os valores das vendas'],
    ['#area-analises > p.introducao', 'Como funciona esta consulta?'],
    ['#area-financas > p.introducao', 'Como o saldo é calculado?'],
  ]) {
    const texto = documento.querySelector(seletor);
    if (!texto || texto.parentElement.classList.contains('ajuda-inline')) continue;
    const ajuda = documento.createElement('details');
    ajuda.className = 'ajuda-inline';
    const resumo = documento.createElement('summary');
    resumo.textContent = titulo;
    texto.replaceWith(ajuda);
    ajuda.append(resumo, texto);
  }
}
