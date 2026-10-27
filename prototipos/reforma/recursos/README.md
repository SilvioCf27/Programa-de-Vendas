# Recursos da revisão Noturno

Arquivos locais para a demo; nenhum recurso é baixado durante seu uso.

- `fundo-lateral.png`, `fundo-superior.png`, `logo.png` e `logo.svg`: arquivos fornecidos pelo usuário no commit `95db8f9` de `main`, respectivamente `download.png`, `download (1).png`, `download (2).png` e `download.svg`. Foram copiados sem alterar seu conteúdo. A prancha completa não é usada como imagem da interface.
- `fontes/`: Inter derivada em quatro arquivos estáticos (400, 500, 600 e 700), eixo óptico 14. Origem oficial: [Google Fonts / Inter](https://github.com/google/fonts/tree/main/ofl/inter), SHA-256 da fonte variável `29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031`. Derivadas com fontTools e família interna **Feira Inter Estudo**, sem instalar fontes no sistema. Licença SIL OFL preservada em `fontes/OFL.txt`. A alternativa é Segoe UI.
- `icones/`: seleção de [Lucide 0.468.0](https://github.com/lucide-icons/lucide/tree/0.468.0/icons), licença em `icones/LICENSE`. O código aplica as cores do tema ao renderizar os SVGs. `check-selecao.svg` deriva de `check.svg` trocando `currentColor` por `#EAF2FF`, para o estado marcado dos controles Qt.
- `SHA256.json`: identificação dos recursos distribuídos nesta revisão, não uma assinatura digital.

Os fundos são desenhados proporcionalmente e compostos sobre a cor do tema. Inter é registrada só no processo Qt. Os ícones são rasterizados na dimensão usada pela interface; as referências SVG continuam locais e escaláveis. O desenho decorativo não interfere na leitura dos arquivos de dados, pois a demo não acessa banco ou contas.
