A versão **1.3.0** renova o visual do Gestão da Feira e mantém seus dados e configurações.

- Cinco temas: Noite, Claro, Grafite, Areia escura e Aurora.
- Grafite com verde esmeralda e Aurora com roxo `#52057B` nas ações principais.
- Cartões com informações complementares e participação de dinheiro, Pix e cartão.
- Histórico com melhor aproveitamento da largura, abas espaçadas e rolagem discreta quando necessária.
- Textos revisados e abertura mais rápida, reutilizando os desenhos dos ícones e contornos.

[Veja as capturas e funcionalidades](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.3.0/docs/INTERFACE.md). Todas as imagens usam dados fictícios.

![Gestão da Feira no tema Grafite](https://raw.githubusercontent.com/SilvioCf27/Programa-de-Vendas/v1.3.0/docs/imagens/vendas-grafite.png)

Baixe **GestaoDaFeira-Windows-x64.zip**, extraia a pasta inteira e abra **GestaoDaFeira.exe**. Não precisa instalar Python ou VS Code. Mantenha a pasta `_internal` junto do executável.

Para atualizar, feche o programa e extraia o pacote em uma pasta separada. O banco em `%LOCALAPPDATA%\ProgramFeira`, as configurações e a sessão protegida são preservados. Não substitua seu banco pelo banco inicial do pacote e não refaça a migração para a nuvem se já a concluiu.

O pacote começa vazio para novos usuários e mantém vendas, taxas, despesas e parcelas dos usuários existentes. A sincronização com o celular e o backup no Google Drive continuam conforme as configurações salvas.

`VALIDACAO_WINDOWS.json` registra a verificação do executável no Windows; `SHA256.txt` permite conferir o download. O executável não tem assinatura digital. As instruções completas estão em `LEIA-ME.md` dentro da pasta extraída.
