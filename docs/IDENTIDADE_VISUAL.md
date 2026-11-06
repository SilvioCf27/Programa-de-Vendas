# Marca do Gestão da Feira

Em 06/11/2026 a PWA passou a usar a mesma barraca turquesa da interface Qt. O desenho vetorial atual do desktop foi mantido; a marca azul com lua da web e o ícone Windows antigo foram substituídos, sem alterar o layout ou as funções.

A fonte do desenho é `prototipos/reforma/recursos/logo.svg`, replicada byte a byte em `web/public/logo-feira.svg`. O cabeçalho e o favicon usam SVG. Os PNGs de 180, 192 e 512px atendem iOS/PWA; a variante maskable de 512px inclui margem para o recorte seguro do Android. O manifesto tem cor de fundo coerente com o tema noturno e URLs versionadas para os ícones. Cache da interface v10. A escolha e a velocidade de atualização do ícone instalado dependem do navegador/sistema; publicar não força a troca imediata do atalho do aparelho.

O código desktop passa a definir o ícone das janelas Qt, e o recurso ICO usado no empacotamento tem sete tamanhos nativos (16 a 256px). Essa parte exige novo executável para chegar à instalação Windows. Não foi criada tag nem substituída a release existente.

Na branch de estudo, `tools/gerar_icones.py` converte o mesmo vetor nos formatos de distribuição com PySide6 e Pillow. Não redesenha a marca, não acessa a rede e não depende de imagens geradas externamente.

Verificação: build web aprovado; 31 cenários de navegador aprovados; abertura/captura da interface Qt em Linux concluída; SVGs comparados byte a byte, dimensões dos PNGs, pixels da variante Android dentro da área segura circular e carregamento de sete tamanhos do ICO no Qt conferidos. Sem alterações em banco, credenciais ou integrações. A primeira chamada manual do verificador Qt precisou do mesmo caminho de recursos configurado pela entrada oficial; repetida com esse caminho, passou. Não é validação de pacote Windows.

[Interface PWA com a marca unificada](imagens/logo-pwa.png).
