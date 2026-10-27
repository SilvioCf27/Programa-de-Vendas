# Segunda rodada — comparação com as referências

A primeira revisão aplicou a identidade, mas simplificou elementos que definiam a aparência das imagens. Esta rodada compara as telas separadamente e aproxima esses elementos sem copiar erros de cálculo ou textos da imagem.

| Elemento da referência | Diferença da primeira demo | Ajuste desta rodada |
| --- | --- | --- |
| Barra lateral com feira iluminada | Muito escura, navegação e ícones pequenos | Foto mais visível, barra mais larga e navegação com ícones maiores |
| Cartões de Vendas | Sem rodapés nem barras; contornos muito vivos | Notas calculadas, percentuais e barras de pagamento; bordas suavizadas e valores claros |
| Semana atual | Painel uniforme sem fotografia | Faixa própria com fotografia lateral, recorte proporcional, transição escura e borda verde |
| Comparação e participação | Uma linha de texto reunia tudo | Dois painéis, período anterior identificado e gráfico de participação |
| Filtros de Vendas | Campos verticais altos | Rótulos ao lado dos campos, mantendo a seleção real demonstrada e aviso de consulta pendente |
| Painéis gerais | Superfícies azuis muito uniformes | Gradientes escuros discretos, alinhados à paleta confirmada |
| Títulos e ícones | Predomínio de texto e ícones soltos pequenos | Ícones maiores em blocos de cor e cabeçalhos consistentes |
| Ações por linha | Botões pouco distintos | Editar azul e excluir vermelho, mantendo rótulos acessíveis e confirmação |
| Recortes da lista financeira | Combo em outra linha | Botões Todas/Despesas/Taxas/Parcelas, preservando totais do período completo |
| Acessos inferiores de Finanças | Botões pequenos sem hierarquia | Cartões com ícone, título, breve explicação e seta |
| Análises | Títulos pouco distintos do conteúdo | Cabeçalhos com ícones e contraste coerente com as outras telas |

## Adaptações mantidas conscientemente

- Fundo, logotipo e fonte usam os recursos individuais enviados, que diferem um pouco da prancha gerada. Não é uma captura da imagem de referência colocada atrás dos controles.
- Os filtros mantêm seletores adaptativos e comportamento demonstrativo coerente. Não copiamos controles redundantes da imagem.
- Datas, totais e gráficos derivam dos exemplos. “Falta cobrir” mantém a explicação correta.
- A data da compra não é repetida a partir da fatura nos exemplos. Taxas, fechamento e demais acessos continuam disponíveis.
- Não duplicamos o valor de saldo na faixa secundária de Finanças nem o acesso de exportação na barra lateral.
- Análises mostra a seleção aplicada em Vendas com um caminho para alterá-la. A comparação A/B continua independente.
- O detalhamento da semana permanece identificando recortes parciais, mesmo que a referência não mostre esse aviso.
- Esta rodada não cria os formulários reais de cadastro, edição, exportação ou configuração. Eles continuam sinalizados como prévias.

## Limites

A fidelidade ainda precisa da avaliação do usuário na demo, especialmente no Windows e em sua escala de exibição. A foto é decorativa e os campos são controles reais, por isso o resultado não será idêntico pixel a pixel à imagem gerada. Refinar a aparência não conclui a integração nem decide sozinho a ferramenta final.

As capturas atualizadas estão em [Noturno](NOTURNO.md). Para abrir localmente, a instalação dos requisitos deve usar o mesmo Python da execução; atualizar o Git não instala PySide6.

## Complemento após o Read.txt completo

A rodada mais recente acrescenta os refinamentos específicos de hierarquia e gráficos descritos no [relatório de aplicação do documento](RELATORIO_READ.md). A galeria Noturno foi atualizada e não representa mais somente a primeira rodada descrita na tabela acima.
