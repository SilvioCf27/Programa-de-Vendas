A versão **1.5.0** ajusta o parcelamento de compras no desktop e no PWA.

- Informe sempre o **valor total da compra**. O programa divide esse total pela quantidade de parcelas, sem acrescentar juros.
- Os centavos são distribuídos para manter a soma exata. R$ 100,00 em 3 vezes gera R$ 33,33, R$ 33,33 e R$ 33,34.
- Editar qualquer parcela abre a **compra inteira**, com total, primeira data e quantidade. Salvar atualiza todo o histórico da compra, inclusive meses anteriores.
- As parcelas mantidas conservam suas identificações. Alterar a quantidade redistribui o total informado.
- Textos, prévias e ajuda foram revisados para diferenciar o total da compra do valor calculado de cada lançamento.
- Valores existentes são preservados na atualização. O total mostrado ao editar é a soma das parcelas já cadastradas; confira-o antes de salvar.

Excluir continua removendo somente a parcela selecionada. Um grupo incompleto é bloqueado para edição, evitando recriar cobranças removidas. Uma edição da compra é gravada por inteiro ou recusada por inteiro.

**Não é necessário executar SQL novo nem migrar os dados novamente.** O SQL 005 acompanha o pacote apenas para quem ainda não habilitou a configuração compartilhada do fechamento da versão anterior.

[Guia de finanças](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.5.0/docs/FINANCAS.md)

Baixe **GestaoDaFeira-Windows-x64.zip**, extraia a pasta inteira e abra **GestaoDaFeira.exe**. Mantenha `_internal` junto dele. Não requer instalar Python ou VS Code.

Feche o programa antes de atualizar. Dados e configurações continuam na pasta de dados existente; não substitua seu banco pelo banco inicial do pacote. O pacote público começa vazio e não contém dados pessoais.

`VALIDACAO_WINDOWS.json` registra os testes do executável no Windows e `SHA256.txt` permite conferir o download. O executável não possui assinatura digital.
