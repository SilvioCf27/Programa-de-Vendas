# Gestão da Feira para Windows

## Abrir sem Python ou VS Code

1. Baixe `GestaoDaFeira-Windows-x64.zip` na seção Releases do repositório: https://github.com/SilvioCf27/Programa-de-Vendas/releases/latest . Escolha esse arquivo, não o arquivo “Source code”.
2. Clique com o botão direito no ZIP e escolha **Extrair tudo**.
3. Abra a pasta `GestaoDaFeira` extraída e dê dois cliques em **GestaoDaFeira.exe**.

Mantenha a pasta inteira. A pasta `_internal` contém Python, Tcl/Tk, bibliotecas, fontes e um banco inicial vazio. Não execute de dentro do ZIP nem mova somente o `.exe`. É possível criar um atalho para o executável na área de trabalho. Não requer instalação como administrador.

O pacote é para **Windows 10/11 x64**. Não há assinatura digital: o Windows pode mostrar um aviso de editor desconhecido. Confira que o arquivo veio do repositório acima. O arquivo `SHA256.txt`, disponível junto do ZIP, permite conferir a integridade do download.

## Versão 1.6.2

Esta atualização de segurança recusa backups com objetos SQL inesperados e
pastas redirecionadas por links/junctions. A restauração usa uma cópia temporária
local, com limites de análise, antes de substituir o banco em uso.
O pacote inclui Python 3.13 e exige SQLite 3.50.2 ou mais recente na análise de backups.
Não exige SQL novo. Veja [SEGURANCA.md](SEGURANCA.md) para o escopo e os limites.

No cartão de crédito, informe a **data da compra**. A primeira fatura é calculada
automaticamente; compras no dia do fechamento entram na fatura seguinte.
As duas datas são guardadas separadamente e sincronizadas entre PC e PWA.

Execute `SQL_006_DATAS_COMPRAS.sql`, incluído no pacote, no SQL Editor do mesmo
projeto Supabase. Não refaça a migração dos dados. Registros antigos continuam
com as faturas existentes até você informar a data original conscientemente.
Os valores já conferidos e os centavos são preservados em edições de descrição.
Leia [FINANCAS.md](FINANCAS.md) para os exemplos e cuidados na atualização.

## Recursos da versão 1.2.0

Acrescenta **Verificar integridade do backup**, revisão explícita de conflitos na
conexão com a nuvem, evolução das vendas e identificação da versão. O ensaio de
recuperação não substitui os dados em uso. Os guias `RECUPERACAO.md`, `USO.md` e
`CELULAR.md` acompanham o pacote. Dados e configurações da versão 1.1 são reaproveitados.

## Integração com a nuvem

Inclui conexão com a nuvem, conferência e migração, sincronização bidirecional de
vendas e finanças e recuperação da sessão protegida no Windows. Depois do login
inicial, a opção automática consulta a nuvem a cada minuto e agenda o envio após
salvar no PC. A senha não é salva. **Desconectar** remove a sessão deste computador.

Se já usava essas funções pelo VS Code, basta abrir o novo executável: ele usa a
mesma pasta de dados e configurações. Não é necessário migrar novamente. Para
configurar do início, consulte [CELULAR.md](CELULAR.md). A nuvem requer internet;
as funções locais e os backups continuam disponíveis sem conexão.

## Seus dados e atualizações

O programa continua usando `%LOCALAPPDATA%\ProgramFeira\vendas.db`, o mesmo banco usado ao executar pelo VS Code. Vendas, taxas, despesas, parcelas, tema e configuração de backup existentes são preservados. Se `PROGRAMFEIRA_DATA_DIR` estiver definido, esse caminho personalizado continua tendo prioridade.

Em um computador sem banco local, o programa cria um banco vazio e prepara a estrutura financeira. Os dados de uso posteriores ficam sempre fora da pasta do executável. Taxas e despesas já cadastradas no banco local são preservadas.

Para atualizar, feche todas as instâncias do programa e extraia o novo pacote em outra pasta. Abra o novo `.exe` e confira os registros. Não misture arquivos de duas versões e não substitua o banco da pasta de dados pelo arquivo que acompanha o pacote. Depois da conferência, é possível remover a pasta antiga do programa; preserve a pasta local de dados e os backups. Não use o VS Code e o executável ao mesmo tempo para editar o mesmo banco.

`git pull` atualiza o código do repositório, mas não transforma um executável já gerado em uma nova versão. Para usar uma alteração no executável, baixe o novo pacote ou gere-o novamente. O backup no Drive continua funcionando conforme a configuração já salva. Trocar de computador exige restaurar o banco e configurar novamente o Drive.

A cópia portátil não inclui o Google Drive para computador: ele deve continuar instalado e conectado para sincronizar a pasta de backup. A exportação Excel já está incluída; não requer instalar openpyxl ou ter Excel instalado para gerar os arquivos.

## Se não abrir

Erros na abertura geram uma mensagem e, quando a pasta de dados permite escrita, um registro em `%LOCALAPPDATA%\ProgramFeira\logs\inicializacao.log`. Envie a última mensagem do arquivo para investigar. Se houver caminho personalizado de dados, o registro fica na subpasta `logs` desse caminho.

## Gerar a distribuição localmente

Esta seção é apenas para quem gera o pacote. Para executar um pacote pronto, Python não é necessário.

No Windows, instale **Python 3.11 x64 com Tcl/Tk e o Python Launcher**. Atualize o repositório, feche o programa e dê dois cliques em `gerar_executavel.cmd`. A primeira geração precisa de internet para baixar as dependências. O script cria um ambiente separado `.venv-build`, executa os testes, gera o programa e testa o próprio binário com dados temporários. Não usa seu banco pessoal.

O resultado fica em `dist/GestaoDaFeira-Windows-x64.zip`. A distribuição inclui apenas um banco inicial vazio. Os testes do pacote usam dados temporários e não levam suas vendas para o executável.

Também é possível executar em um ambiente de desenvolvimento já preparado:

```powershell
py -3.11 -m pip install -r requirements-build.txt
py -3.11 -m unittest discover -s tests -v
py -3.11 tools/gerar_executavel.py
```

## Geração pelo GitHub

A automação **Executavel Windows**, na aba Actions, gera o pacote em um Windows x64, executa os testes e verifica cadastro, despesas, backup, fontes e exportação CSV/Excel dentro do executável, com um banco temporário. Um pacote reprovado não é publicado.

Em atualizações da branch `main`, o ZIP aprovado aparece em **Artifacts → GestaoDaFeira-Windows-x64** da execução correspondente; pode ser necessário estar conectado ao GitHub para baixar. Esse download contém o ZIP do programa e os relatórios. Em tags de versão `v*`, a automação também publica o ZIP em Releases, após a aprovação dos testes. A execução manual está disponível em **Actions → Executavel Windows → Run workflow**.

Após publicar uma versão, a automação baixa novamente o ZIP e os relatórios,
confere o SHA-256 e a versão testada e registra o resultado na tag anotada
`validacao/vX.Y.Z`. Esse registro só aparece depois da conferência do download.
