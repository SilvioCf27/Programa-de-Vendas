# Certificado do servidor de contrato

`servidor-loopback-cert.pem` e `servidor-loopback-chave-apenas-testes.pem` foram gerados exclusivamente para a suíte local, sem associação com contas ou serviços. A chave está deliberadamente publicada: não é uma credencial do aplicativo e não pode ser usada fora dos testes.

O servidor escuta somente `127.0.0.1` em porta aleatória. O roteamento de socket da suíte impede saída externa e mantém o hostname fictício `contrato-qt.supabase.co` para verificar TLS/SNI. O opener de teste confia somente no certificado incluído, com validação de cadeia e hostname habilitada. Há uma contraprova com a confiança normal, que recusa o certificado antes de enviar credenciais HTTP. O cliente e a confiança TLS da aplicação não foram alterados.

Validade: 28/10/2026 a 25/10/2036. Regenerar o par somente para a suíte quando necessário; nunca instalar esse certificado na confiança do Windows nem em um projeto Supabase.
