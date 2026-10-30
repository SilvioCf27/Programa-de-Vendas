# Primeira rodada Windows do pacote Qt — reprovada

Aplicação `a1c20583b6bce8299d1126a49bb81826cf0036d1`, execução [41054098828](https://github.com/SilvioCf27/Programa-de-Vendas/actions/runs/41054098828).

- Qt: 185/185 aprovados, incluindo DPAPI nativa.
- Versão estável: 202/202 aprovados.
- Protótipos: 30/31 aprovados. A demo Tkinter esperava pelo menos cinco linhas visíveis; a resolução padrão da VM não permitiu essa altura.
- Pacote e transição não executados: a etapa anterior falhou. Nenhuma release publicada por esta rodada.

A preparação/restauração de resolução já usada em `reforma-vendas-windows.yml` foi incorporada ao workflow de pacote. As fontes Python, recursos, especificações e dependências permanecem idênticos à revisão desta execução. A repetição pode reutilizar apenas as duas suítes integralmente aprovadas, após conferir igualdade das fontes, Python e SQLite; ela executa novamente os protótipos, R01–R06, compilação, smoke e transição/rollback. Os relatórios reutilizados registram sua origem explícita. Mudança de fonte ou runtime invalida o reaproveitamento e exige rodar todas as suítes.
