A versão **1.7.0** acrescenta atualizações pelo próprio aplicativo Windows.

- **Configurações → Atualizações** consulta releases estáveis do repositório oficial.
- O programa pode avisar ao abrir; o download e a instalação exigem sua confirmação.
- Confere o SHA-256, recusa caminhos perigosos e testa o executável novo com dados temporários antes da troca.
- Cria backup local e, se configurado, na pasta do Drive antes de reiniciar. As cópias remotas dependem do cliente Drive.
- Preserva dados e preferências, mantém o caminho dos atalhos e guarda a pasta anterior. Se a nova versão não confirmar a abertura, tenta recuperar a anterior.
- A publicação exige um ensaio no Windows com dois binários reais e dados fictícios, além do teste de recuperação após falha.

**Esta primeira atualização ainda precisa ser baixada e extraída manualmente**, pois as versões anteriores não contêm o atualizador. Depois, use a nova opção nas configurações.

Baixe **GestaoDaFeira-Windows-x64.zip**, extraia a pasta inteira e abra **GestaoDaFeira.exe**, mantendo `_internal` junto dele. Use uma pasta local própria com permissão de escrita, fora da pasta de dados, de unidades virtuais e do repositório. Não é necessário executar como administrador. Seus registros existentes continuam na pasta local de dados.

**Não exige SQL novo.** As funções financeiras, de sincronização e de proteção dos backups continuam disponíveis.

[Como atualizar e recuperar](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.7.0/docs/ATUALIZACOES.md) · [Segurança e limites](https://github.com/SilvioCf27/Programa-de-Vendas/blob/v1.7.0/docs/SEGURANCA.md)

O download inclui `SHA256.txt`, `VALIDACAO_WINDOWS.json` e `VALIDACAO_ATUALIZADOR.json`. O pacote público começa vazio e não contém seus dados. Ainda não possui assinatura digital: o hash verifica integridade, e a confiança na conta/publicação GitHub continua necessária. O atualizador não é antivírus nem restaura seu banco automaticamente ao recuperar arquivos do programa.
