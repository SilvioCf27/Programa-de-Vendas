# Regressão local após o diagnóstico do preparador

Execução em 30/10/2026 na branch `reforma/estudo-interface`, base `f4139aa`, com a correção local de `preparar_validacao.py` e seus quatro testes ainda não commitados. Python 3.13.16, SQLite 3.53.1 e PySide6 6.10.2. Somente dados fictícios e diretórios temporários; sem acesso ao Supabase ou Drive.

| Verificação | Resultado |
| --- | --- |
| [Qt, perfil e entrada de validação](qt.json) | 171 executados, 169 aprovados, dois DPAPI ignorados por exigir Windows |
| [Versão estável](estavel.json) | 202 executados, 200 aprovados, dois testes nativos Windows ignorados |
| [Protótipos](prototipos.json) | 31 executados e aprovados |
| [Revisão R01–R06](revisao.json) | Seis cenários conformes; não é aprovação geral da etapa |

As suítes foram executadas com `reforma_desktop/validar.py --suite <suite> --saida <arquivo.json>`, para `reforma_desktop/tests`, `tests` e `prototipos/reforma`. A revisão usou `reforma_desktop/avaliacao/revisar_etapa4.py --saida <arquivo.json> --exigir-conformidade`. `git diff --check` passou.

A [primeira tentativa](tentativa-sem-display) das suítes estável e protótipos falhou por ausência de servidor gráfico em `DISPLAY=:99`. Esses resultados foram preservados e não constituem aprovação. Após iniciar Xvfb em `:101`, confirmar que Tk abre e manter seu processo durante as suítes, ambas passaram. O Xvfb dessa repetição foi encerrado ao terminar. A suíte Qt usou a plataforma offscreen dos testes existentes.

O contrato HTTPS usa servidor fictício em loopback, inclusive nos testes da entrada online. Não comprova Auth, SQL, RLS, concorrência ou integração PC/PWA no projeto real.

## Sequência preservada

A Etapa 6 continua aberta. A próxima conferência externa prevista em `VALIDACAO_ONLINE.md` é Auth/SQL/RLS e fluxos em projeto separado autorizado. Os testes manuais Windows ficam pendentes, assim como Drive, DPI/acessibilidade, pacote Qt e atualização 1.7.1 → 2.0 com recuperação. A PWA segue na Etapa 7. Não houve publicação nem alteração da branch main.
