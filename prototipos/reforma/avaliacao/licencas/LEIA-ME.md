# Viabilidade de distribuição

A avaliação usa **PySide6 Essentials e Shiboken 6.10.2**. Os metadados instalados declaram `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`. Os textos LGPLv3 e GPLv3 desta pasta foram obtidos sem alterações do repositório oficial Qt for Python, tag `v6.10.2`, commit `057cda38d369d042c59fd48544398cb917540718`:

- [LGPL-3.0-only](https://github.com/pyside/pyside-setup/blob/v6.10.2/LICENSES/LGPL-3.0-only.txt)
- [GPL-3.0-only](https://github.com/pyside/pyside-setup/blob/v6.10.2/LICENSES/GPL-3.0-only.txt)

Essas cópias são referência da licença da biblioteca; **não alteram a licença do projeto Gestão da Feira**. Não foi comprada nem exigida licença comercial para os ensaios. O uso/distribuição pela opção LGPL exige cumprir seus termos.

Para uma futura release pela opção LGPL, preparar os avisos de uso, cópias das licenças, indicação das versões/fontes correspondentes e um mecanismo de bibliotecas compartilhadas que permita substituição compatível/religação nos termos aplicáveis. Não impor restrições incompatíveis à modificação da biblioteca e à depuração dessas modificações. A seção 4 da LGPL é a referência principal para o trabalho combinado. Verificar também os avisos dos módulos Qt efetivamente incluídos e das demais dependências.

Os pacotes de estudo são em modo pasta, com bibliotecas dinâmicas, mas não foram publicados como versão do aplicativo. Isso não dispensa conferir o pacote final. A futura integração continuará usando Widgets/Core/Gui/Svg, sem introduzir QtCharts ou WebEngine nesta decisão.

Tk/Tcl e Python têm suas próprias licenças permissivas; PyInstaller usa GPL com exceção para os programas empacotados. Inter e Lucide já têm OFL/ISC preservadas na pasta de recursos. Nenhum desses termos substitui a definição da licença do próprio projeto, que hoje não tem arquivo de licença na raiz. Essa definição e os avisos da distribuição devem ser acertados antes da futura publicação; não foram alterados nesta avaliação.
