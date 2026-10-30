# Candidata Qt — validação local de 30/10/2026

Base de aplicação `f4139aa`, mais as alterações locais de produção/empacotamento, incluindo a correção do preparador. Estes relatórios não são evidências de execução Windows nem de publicação. Python 3.13.16, SQLite 3.53.1, PySide6 6.10.2 e PyInstaller 6.16.0.

| Verificação executada | Resultado |
| --- | --- |
| [Suíte Qt completa](qt.json) | 181 executados, 179 aprovados, dois DPAPI Windows ignorados |
| [Versão estável](estavel.json) | 202 executados, 200 aprovados, dois testes Windows ignorados |
| [Protótipos](prototipos.json) | 31/31 aprovados |
| [Revisão direcionada](revisao.json) | R01–R06 conformes |
| [Executável Linux real](BINARIO_LINUX.json) | Smoke aprovado, `empacotado: true`, sem HTTP, dados temporários |
| Contraprovas adicionais de publicação | Quatro testes aprovados, sem publicar nem executar binário Windows |

Após os ajustes finais de textos/controles, repetidos os 13 testes da entrada online local e os cinco de produção. O smoke do binário foi repetido fora do checkout, em `/tmp`, após reconstruir a distribuição final. `git diff --check` e leitura YAML dos workflows sem erros.

A primeira versão do pacote falhou porque os componentes compartilhados importados pelo nome curto procuravam SVGs em `recursos/` na raiz interna. A especificação passou a incluir os recursos também nesse caminho; o binário reconstruído passou na verificação funcional. O diretório do executável Linux tem aproximadamente 195 MiB; o limite do ZIP Windows será conferido no build nativo, não inferido deste tamanho.

Os contratos HTTPS foram executados apenas em loopback com credenciais fictícias. Nenhum Supabase, Drive ou dado pessoal foi acessado. Os testes manuais Windows foram adiados pelo usuário. Pacote Windows, transição 1.7.1 → 2.0, rollback nativo e publicação continuam exigindo seus resultados próprios.
