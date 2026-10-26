A versão **1.7.1** melhora o acompanhamento semanal no aplicativo desktop.

- **Semana atual** na tela inicial: total bruto, dias de feira e valores de dinheiro, Pix e cartão, de segunda-feira até hoje. Independe dos filtros e não inclui datas futuras.
- **Análises → Resultados por semana**: histórico semanal da seleção aplicada, com indicação de semanas parciais. Dias zerados continuam contando como feiras.
- **Configurações → Período ao abrir o programa**: fechamento atual (padrão), mês atual, ano atual ou todas as vendas. A preferência vale na próxima abertura e respeita o histórico dos fechamentos.
- Atualiza a faixa semanal após salvar ou sincronizar e, em até 30 segundos, após a virada do dia, preservando filtros e formulários em preparação.

**Se você usa a v1.7.0:** abra **Configurações → Atualizações → Verificar atualizações → Baixar e instalar**. O programa verifica o pacote, cria backup e reinicia, guardando a pasta anterior. Feche outras instâncias antes de atualizar.

Para versões anteriores à v1.7.0, baixe **GestaoDaFeira-Windows-x64.zip**, extraia a pasta inteira e abra **GestaoDaFeira.exe**, mantendo `_internal` junto dele. Seus dados locais existentes são reaproveitados. Use uma pasta local própria, separada da pasta de dados e com permissão de escrita; não requer administrador.

**Somente desktop. A PWA não foi alterada. Não exige SQL novo.**

[Guia de uso](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.7.1/docs/USO.md) · [Atualização e recuperação](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.7.1/docs/ATUALIZACOES.md)

`SHA256.txt`, `VALIDACAO_WINDOWS.json` e `VALIDACAO_ATUALIZADOR.json` acompanham a publicação. O pacote começa vazio, não inclui dados de uso e ainda não possui assinatura digital. O envio de backups ao Drive depende do cliente Google Drive; a recuperação automática troca arquivos do programa, não restaura seu banco automaticamente.
