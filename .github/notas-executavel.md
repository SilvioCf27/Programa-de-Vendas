A versão 1.2.2 coloca as funções de dados em Configurações, pela engrenagem na tela principal, com explicações breves ao passar o mouse sobre **?**. A opção de conferir a cópia passa a se chamar **Verificar integridade do backup** e informa claramente que não altera os dados em uso. Tema, exportação e Nova venda mantêm suas posições. Dados e configurações existentes são preservados.

A versão 1.2.0 acrescenta:

- Teste de recuperação de backup em pasta temporária, conferindo todas as tabelas sem alterar o banco em uso.
- Revisão das versões em conflito no PC e na nuvem, com escolha explícita, backup e nova conferência das versões antes de aplicar.
- Gráficos de evolução por mês e fechamento no desktop e na web.
- Exportação CSV/Excel no celular, seguindo a seleção aplicada em Vendas.
- Identificação da versão, diagnósticos sem mensagens ou credenciais e guia de recuperação incluído no pacote.

Esta versão inclui a conexão com a nuvem, migração conferida e sincronização de vendas, despesas, taxas e parcelas entre o PC e a versão web. No Windows, a sessão é protegida pela conta do sistema e recuperada nas próximas aberturas, sem salvar a senha. A sincronização automática continua enquanto o programa estiver aberto, conectado e sem formulário em edição.

Baixe **GestaoDaFeira-Windows-x64.zip**, extraia a pasta inteira e abra **GestaoDaFeira.exe**. Não precisa instalar Python ou VS Code. Mantenha a pasta `_internal` junto do executável.

Para atualizar, feche o programa e extraia a nova versão em uma pasta separada. O banco existente em `%LOCALAPPDATA%\ProgramFeira` e a configuração de backup no Drive são preservados. Não substitua esse banco manualmente pelo banco inicial do pacote.

O pacote acompanha um banco vazio, as fontes e a exportação Excel. Para quem já usa o aplicativo, os dados locais continuam no mesmo lugar. O executável não tem assinatura digital. Instruções completas estão no arquivo `LEIA-ME.md` dentro da pasta extraída.

`VALIDACAO_WINDOWS.json` registra o teste automático do binário no Windows; `SHA256.txt` identifica o arquivo distribuído.

Para quem já usa a nuvem pelo código-fonte, as configurações e a sessão protegida existentes são reaproveitadas. Quem ainda usa a versão 1.0.1 pode configurar em **Configurações → Conexão com a nuvem**; não substitua os dados locais nem refaça a migração se já a concluiu. A versão web também recebeu Análises, comparações de períodos e atualização automática da área visível.
