# Tipografia de Gestão da Feira

Fontes redistribuídas sob a SIL Open Font License 1.1. Os textos integrais estão
em `Inter/OFL.txt` e `PlusJakartaSans/OFL.txt`. Os créditos originais permanecem
nos arquivos e nas licenças.

- Origem Inter: https://github.com/google/fonts/tree/main/ofl/inter
- Origem Plus Jakarta Sans: https://github.com/google/fonts/tree/main/ofl/plusjakartasans
- Entradas oficiais (download HTTPS com verificação TLS):
  - https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf
  - https://raw.githubusercontent.com/google/fonts/main/ofl/plusjakartasans/PlusJakartaSans%5Bwght%5D.ttf
- SHA-256 das fontes variáveis usadas:
  - Inter: `29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031`
  - Plus Jakarta Sans: `89b3fb38aa0d275d7a731d0d817a4f1622b316b4d7fbdedcf02ee9099ff68bc8`

As cópias distribuídas são derivações estáticas com pesos 400 e 600, geradas
com `fontTools.varLib.instancer`. Seus nomes internos são **Feira Text** e
**Feira Display**, para distinguir as versões modificadas das originais.
Feira Text usa os algarismos tabulares fornecidos pela Inter, mesmo quando o
renderizador não permite selecionar esse recurso OpenType na interface.

Para reproduzir: baixe as duas entradas com os nomes `Inter.ttf` e
`PlusJakartaSans.ttf` numa pasta temporária e execute
`python tools/gerar_fontes.py /pasta/temporaria`. O script verifica os hashes
antes de gerar os arquivos; requer fonttools apenas para essa operação.

O programa carrega estas fontes de forma privada no Windows, sem instalá-las.
Se o carregamento não for suportado, usa uma família instalada equivalente.
Nenhuma dependência de fonte nem acesso à internet é necessário em tempo de uso.
