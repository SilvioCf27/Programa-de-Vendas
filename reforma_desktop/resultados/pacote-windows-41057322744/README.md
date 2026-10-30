# Desktop 2.0.0 publicado — pacote e transição aprovados

Revisão do binário: `3f1b953febcdbe175b32e6159896f313cc815986`. [Execução Windows 41057322744](https://github.com/SilvioCf27/Programa-de-Vendas/actions/runs/41057322744). Python 3.13.16, SQLite 3.50.4, Qt 6.10.2. Somente dados temporários fictícios e TLS loopback; sem Supabase/Drive ou dados pessoais.

| Verificação | Resultado |
| --- | --- |
| Qt | 185/185 aprovados, incluindo DPAPI nativa |
| Versão estável | 202/202 aprovados |
| Protótipos | 31/31 aprovados após preparar a resolução da VM |
| R01–R06 | Seis cenários conformes |
| Pacote Qt Windows | Binário real aprovado: navegação, cadastro, parcelas, Excel e backup defensivo |
| Referência 1.7.1 | Compilada da tag original e aprovada no próprio smoke |
| Troca 1.7.1 → 2.0 | Reinício e recibo 2.0 confirmados; tabelas e configurações preservadas |
| Falha deliberada de abertura | Rollback e reabertura da 1.7.1 confirmados; dados e configurações preservados |
| Resolução da VM | Restaurada ao terminar |

Qt e estável foram reaproveitados da execução 41054098828 somente após conferir igualdade das fontes, dependências, Python e SQLite. Cada JSON registra a origem e a revisão equivalente. O testador da transição é executado em cada rodada e não integra esse cache. Protótipos, revisão, compilação, smoke e troca/rollback foram executados nesta rodada. Não há falhas, erros ou testes ignorados nas suítes Windows aprovadas.

`codigo_helper: 1` no diagnóstico final refere-se ao cenário de falha **provocada** para testar rollback; era o resultado exigido. `sucesso: true` e os dois cenários em `VALIDACAO_ATUALIZADOR.json` registram as aprovações.

As rodadas reprovadas 41054098828 (altura da tela), 41056084865 e 41056652971 (limpeza do processo em caminho curto 8.3) foram preservadas. A correção de limpeza resolve os caminhos e aguarda a saída dos processos criados pelo ensaio; não ignora falhas de preservação nem de recuperação.

## Distribuição

A [publicação 41057915253](https://github.com/SilvioCf27/Programa-de-Vendas/actions/runs/41057915253) conferiu a revisão, os relatórios nativos e o SHA-256 e publicou **o mesmo ZIP aprovado**, sem recompilar. A [release v2.0.0](https://github.com/SilvioCf27/Programa-de-Vendas/releases/tag/v2.0.0) é a estável mais recente. Os quatro arquivos públicos foram baixados; o hash do ZIP coincide com o checksum e com o relatório de transição. [Recibo da conferência](CONFERENCIA_PUBLICACAO.json).

A versão 1.7.1 pode atualizar por Configurações → Atualizações. O runtime do pacote inclui Python/SQLite; o Python 3.11 instalado separadamente pelo usuário não é usado pelo executável.

**Pendentes:** teste manual no Windows do usuário, DPI/acessibilidade completos, Auth/SQL/RLS e PC/PWA/Drive reais. A liberação para o usuário testar a atualização foi solicitada sem esperar esses ensaios manuais; eles não foram marcados como aprovados. Main, SQL, PWA, contas externas e dados pessoais não foram modificados.
