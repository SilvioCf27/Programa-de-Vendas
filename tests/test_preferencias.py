import tempfile
import unittest
from pathlib import Path
from ProgramFeira.preferencias import carregar_tema, salvar_tema


class PreferenciasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name)

    def test_primeira_abertura_e_arquivo_invalido(self):
        self.assertEqual(carregar_tema(self.pasta), 'escuro')
        for texto in ('invalido', '[]', '{"tema":"outro"}'):
            (self.pasta / 'preferencias.json').write_text(texto)
            self.assertEqual(carregar_tema(self.pasta), 'escuro')

    def test_preferencia_persistida(self):
        for tema in ('claro', 'escuro'):
            salvar_tema(self.pasta, tema)
            self.assertEqual(carregar_tema(self.pasta), tema)
        self.assertEqual(list(self.pasta.glob('.preferencias-*')), [])

    def test_tema_invalido_preserva_preferencia(self):
        salvar_tema(self.pasta, 'claro')
        with self.assertRaises(ValueError):
            salvar_tema(self.pasta, 'outro')
        self.assertEqual(carregar_tema(self.pasta), 'claro')
