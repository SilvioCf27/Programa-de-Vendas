"""Downloads simulados e troca/recuperação real de pastas no Windows."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

from ProgramFeira import atualizador as a

ROOT = Path(__file__).resolve().parents[1]


class AtualizadorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name)
        self.alvo = self.pasta / 'Programa com espaços'
        self.alvo.mkdir()
        (self.alvo / '_internal').mkdir()
        self.exe = self.alvo / 'GestaoDaFeira.exe'
        self.exe.write_bytes(b'versao antiga')
        self.banco = self.pasta / 'dados/vendas.db'
        self.banco.parent.mkdir()
        self.banco.write_bytes(b'dados preservados')
        self.versao = 'v999.0.0'
        self.release = {'versao': self.versao, 'assets': {n: f'https://github.com/{a.REPOSITORIO}/releases/download/{self.versao}/{n}' for n in (a.PACOTE, 'SHA256.txt', 'VALIDACAO_WINDOWS.json')}}

    def pacote(self, entradas=None):
        zip_path = self.pasta / 'origem.zip'
        with zipfile.ZipFile(zip_path, 'w') as z:
            for nome, conteudo in (entradas or {'GestaoDaFeira/GestaoDaFeira.exe': b'novo', 'GestaoDaFeira/_internal/modulo': b'recurso'}).items():
                z.writestr(nome, conteudo)
        return zip_path

    def relatorio(self):
        return {'versao': '999.0.0', 'plataforma': 'win32', 'sucesso': True, 'empacotado': True,
                'backup_seguranca': True, 'banco_isolado': True}

    def downloads(self, corrompido=False):
        zip_path = self.pacote()
        def baixar(url, destino, limite):
            if url.endswith('.zip'):
                shutil.copy2(zip_path, destino)
            elif url.endswith('SHA256.txt'):
                sha = '0' * 64 if corrompido else hashlib.sha256(zip_path.read_bytes()).hexdigest()
                Path(destino).write_text(f'{sha}  {a.PACOTE}\n')
            else:
                Path(destino).write_text(json.dumps(self.relatorio()))
        return baixar

    def test_consulta_apenas_release_estavel_completa_e_mais_nova(self):
        metadata = {'tag_name': self.versao, 'assets': [{'name': n, 'browser_download_url': u} for n, u in self.release['assets'].items()]}
        def baixar(url, destino, limite):
            self.assertEqual(url, a.API)
            Path(destino).write_text(json.dumps(metadata))
        with patch.object(a, 'baixar', baixar):
            self.assertEqual(a.consultar(), self.release)
            metadata['prerelease'] = True
            with self.assertRaises(ValueError): a.consultar()
            metadata['prerelease'] = False
            metadata['tag_name'] = 'v0.0.1'
            self.assertIsNone(a.consultar())
            metadata['tag_name'] = self.versao
            metadata['assets'].pop()
            with self.assertRaises(ValueError): a.consultar()

    def test_recusa_urls_externas_http_credenciais_e_versoes_invalidas(self):
        for url in ('http://github.com/a', 'https://github.com.evil.test/a', 'https://user@github.com/a', 'https://github.com:444/a', 'file:///tmp/a'):
            with self.subTest(url=url), self.assertRaises(ValueError): a.url_segura(url)
        for v in ('v1.2.3-beta', '1.2', None, '1.2.3;comando'):
            with self.assertRaises(ValueError): a.numero(v)
        req = a.Request('https://github.com/a')
        with self.assertRaises(ValueError):
            a._Redirecionamento().redirect_request(req, None, 302, '', {}, 'https://evil.test/pacote')

    def test_stream_limita_download_sem_content_length_e_revalida_redirecionamento(self):
        class Resposta(io.BytesIO):
            url = 'https://github.com/pacote'
            headers = {}
        from unittest.mock import Mock
        opener = Mock()
        opener.open.return_value = Resposta(b'0123456789')
        with patch.object(a, 'build_opener', return_value=opener), self.assertRaises(ValueError):
            a.baixar('https://github.com/pacote', self.pasta / 'parcial', 5)
        resposta = Resposta(b'')
        resposta.url = 'https://evil.test/pacote'
        opener.open.return_value = resposta
        with patch.object(a, 'build_opener', return_value=opener), self.assertRaises(ValueError):
            a.baixar('https://github.com/pacote', self.pasta / 'redirecionado', 5)

    def test_recusa_zip_traversal_links_caminhos_windows_e_duplicados(self):
        for nome in ('../fora', '/GestaoDaFeira/fora', 'GestaoDaFeira/../../fora', 'GestaoDaFeira/a\\b', 'GestaoDaFeira/con.txt', 'GestaoDaFeira/a:stream', 'GestaoDaFeira/a. ', 'Outro/programa.exe'):
            with self.subTest(nome=nome), self.assertRaises(ValueError):
                a.extrair(self.pacote({nome: b'perigoso'}), self.pasta / 'extraido')
        zpath = self.pasta / 'link.zip'
        with zipfile.ZipFile(zpath, 'w') as z:
            info = zipfile.ZipInfo('GestaoDaFeira/link')
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, '../../fora')
        with self.assertRaises(ValueError): a.extrair(zpath, self.pasta / 'extraido')
        with self.assertRaises(ValueError):
            a.extrair(self.pacote({'GestaoDaFeira/A': b'1', 'GestaoDaFeira/a': b'2'}), self.pasta / 'extraido')

    def test_limita_tamanho_zip_e_estrutura(self):
        with patch.object(a, 'MAX_EXTRAIDO', 1), self.assertRaises(ValueError):
            a.extrair(self.pacote(), self.pasta / 'extraido')
        with self.assertRaises(ValueError):
            a.extrair(self.pacote({'GestaoDaFeira/leia.txt': b'sem executavel'}), self.pasta / 'extraido')

    def test_prepara_testa_sem_modificar_aplicativo_dados_ou_preferencias(self):
        download = self.downloads()
        preferencias = self.banco.parent / 'preferencias.json'
        preferencias.write_bytes(b'{"tema":"aurora"}')
        def executar(args, **kwargs):
            self.assertEqual(args[1], '--verificar-pacote')
            Path(args[2]).write_text(json.dumps(self.relatorio()))
        with patch.object(a, 'baixar', download), patch.object(a.subprocess, 'run', executar):
            preparado = a.preparar(self.release, self.exe, self.banco)
        self.assertTrue((preparado['nova'] / 'GestaoDaFeira.exe').is_file())
        self.assertTrue((preparado['stage'] / 'aplicar.ps1').exists())
        self.assertEqual(self.exe.read_bytes(), b'versao antiga')
        self.assertEqual(self.banco.read_bytes(), b'dados preservados')
        self.assertEqual(preferencias.read_bytes(), b'{"tema":"aurora"}')

    def test_hash_errado_interrupcao_ou_autoteste_falho_nao_instalam(self):
        for falha in ('hash', 'download', 'autoteste'):
            with self.subTest(falha=falha):
                baixar = self.downloads(corrompido=falha == 'hash')
                if falha == 'download':
                    baixar = lambda *args: (_ for _ in ()).throw(OSError('Sem rede'))
                with patch.object(a, 'baixar', baixar), patch.object(a.subprocess, 'run', side_effect=RuntimeError('Autoteste falhou')) as rodar:
                    with self.assertRaises((ValueError, OSError, RuntimeError)):
                        a.preparar(self.release, self.exe, self.banco)
                    if falha != 'autoteste': rodar.assert_not_called()
                self.assertEqual(self.exe.read_bytes(), b'versao antiga')
                self.assertEqual(self.banco.read_bytes(), b'dados preservados')
                self.assertEqual(list(self.pasta.glob('.feira-atualizacao-*')), [])

    def test_recusa_dados_dentro_da_instalacao_e_instalacao_dentro_dos_dados(self):
        for banco in (self.alvo / 'vendas.db', self.pasta / 'vendas.db'):
            with self.assertRaises(ValueError): a.validar_destino(self.exe, banco)
        (self.alvo / '.git').mkdir()
        with self.assertRaises(ValueError): a.validar_destino(self.exe, self.banco)

    def test_nao_lanca_helper_se_backup_falhar(self):
        stage = self.pasta / '.feira-atualizacao-teste'
        stage.mkdir()
        with patch('ProgramFeira.database.armazenamento.criar_backup', side_effect=OSError('Sem espaço')), patch.object(a.subprocess, 'Popen') as abrir:
            with self.assertRaises(OSError): a.instalar({'alvo': self.alvo, 'stage': stage, 'nova': stage / 'nova/GestaoDaFeira'}, self.banco)
            abrir.assert_not_called()

    def test_recusa_relatorio_sem_protecao_ou_de_outra_versao(self):
        for campo, valor in (('versao', '1.0.0'), ('backup_seguranca', False), ('empacotado', False), ('plataforma', 'linux')):
            dados = self.relatorio()
            dados[campo] = valor
            path = self.pasta / 'relatorio.json'
            path.write_text(json.dumps(dados))
            with self.assertRaises(ValueError): a.validar_relatorio(path, self.versao)


@unittest.skipUnless(sys.platform == 'win32', 'Helper nativo requer Windows')
class TrocaWindowsTests(unittest.TestCase):
    def test_helper_troca_e_recupera_apos_falha_de_abertura(self):
        # Compila um programa mínimo do Windows, sem Tk ou banco real. Exercita
        # PowerShell, espera do processo, espaços, troca e rollback de verdade.
        with tempfile.TemporaryDirectory(prefix='feira teste ') as tmp:
            raiz = Path(tmp)
            codigo = raiz / 'Teste.cs'
            codigo.write_text(r'''
using System; using System.IO; using System.Diagnostics; using System.Threading;
class Teste {
 static void Main(string[] args) {
  string pasta = AppDomain.CurrentDomain.BaseDirectory;
  File.WriteAllText(Path.Combine(pasta,"processo.txt"), Process.GetCurrentProcess().Id.ToString());
  if(args.Length == 2) {
   string v = File.ReadAllText(Path.Combine(pasta,"versao.txt"));
   if(v == "falha") return;
   File.WriteAllText(args[1], "{\"versao\":\""+v+"\",\"pid\":"+Process.GetCurrentProcess().Id+"}");
  }
  Thread.Sleep(120000);
 }
}''')
            csc = Path(os.environ['SystemRoot']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
            binario = raiz / 'Teste.exe'
            subprocess.run([str(csc), '/nologo', '/target:exe', '/out:' + str(binario), str(codigo)], check=True, capture_output=True)
            ps = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            for falha in (False, True):
                caso = raiz / str(falha)
                alvo = caso / 'Programa com espaços'
                alvo.mkdir(parents=True)
                shutil.copy2(binario, alvo / 'GestaoDaFeira.exe')
                (alvo / 'versao.txt').write_text('1.0.0')
                stage = caso / '.feira-atualizacao-teste'
                nova = stage / 'nova/GestaoDaFeira'
                nova.mkdir(parents=True)
                shutil.copy2(binario, nova / 'GestaoDaFeira.exe')
                (nova / 'versao.txt').write_text('falha' if falha else '999.0.0')
                banco = caso / 'dados.db'
                banco.write_bytes(b'dados e configuracoes intactos')
                params = stage / 'parametros.json'
                antigo = subprocess.Popen([str(alvo / 'GestaoDaFeira.exe')])
                helper = None
                try:
                    params.write_text(json.dumps({'pid': antigo.pid, 'alvo': str(alvo), 'nova': str(nova), 'versao': '999.0.0', 'backup': 'nao toca'}), encoding='utf-8')
                    helper = subprocess.Popen([str(ps), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'ProgramFeira/assets/aplicar_atualizacao.ps1'), '-Parametros', str(params), '-SemDialogo'], cwd=stage, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    limite = time.monotonic() + 20
                    while not (stage / 'pronto').exists() and time.monotonic() < limite:
                        if helper.poll() is not None: break
                        time.sleep(.1)
                    self.assertTrue((stage / 'pronto').exists(), helper.communicate(timeout=1) if helper.poll() is not None else 'Helper não iniciou')
                    self.assertEqual((alvo / 'versao.txt').read_text(), '1.0.0')
                    antigo.terminate()
                    antigo.wait(timeout=10)
                    stdout, stderr = helper.communicate(timeout=30)
                    self.assertEqual(helper.returncode, 1 if falha else 0, (stdout, stderr, (stage / 'resultado.txt').read_text()))
                    self.assertEqual((alvo / 'versao.txt').read_text(), '1.0.0' if falha else '999.0.0')
                    self.assertEqual(banco.read_bytes(), b'dados e configuracoes intactos')
                    if falha:
                        limite = time.monotonic() + 10
                        while (alvo / 'processo.txt').read_text() == str(antigo.pid) and time.monotonic() < limite:
                            time.sleep(.1)
                        self.assertNotEqual((alvo / 'processo.txt').read_text(), str(antigo.pid), 'A versão anterior precisa reabrir')
                    if not falha:
                        self.assertEqual((Path(str(alvo) + '.anterior-teste') / 'versao.txt').read_text(), '1.0.0')
                finally:
                    if antigo.poll() is None: antigo.kill(); antigo.wait(timeout=10)
                    if helper and helper.poll() is None: helper.kill(); helper.wait(timeout=10)
                    # Encerra somente as fixtures que este teste criou.
                    for pidfile in caso.rglob('processo.txt'):
                        pid = pidfile.read_text()
                        subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True)
                    time.sleep(.3)
