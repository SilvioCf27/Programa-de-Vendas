"""Configuração e fechamento com backup, sem bloquear o loop gráfico."""
import queue
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ProgramFeira import backup_drive as drive
from ProgramFeira.interface.visual import CORES


class BackupDrive:
    def __init__(self, janela, banco):
        self.janela, self.banco = janela, banco
        self.ocupado = False
        janela.protocol('WM_DELETE_WINDOW', self.fechar)

    def configurar(self):
        if self.ocupado:
            return
        popup = tk.Toplevel(self.janela)
        popup.title('Backup no Google Drive')
        popup.configure(background=CORES['fundo'])
        popup.transient(self.janela)
        corpo = ttk.Frame(popup, padding=20)
        corpo.pack(fill='both', expand=True)
        corpo.columnconfigure(0, weight=1)
        ttk.Label(corpo, text='Proteja seus dados no Google Drive', style='Title.TLabel').grid(row=0, column=0, columnspan=2, sticky='w')
        texto = ('Instale e conecte o Google Drive para computador. Escolha uma pasta dentro do seu Drive, preferencialmente disponível off-line.\n\nO programa grava uma cópia verificada ao fechar e mantém as 7 versões mais recentes, além do arquivo "último". O banco em uso continua local.\n\nA mensagem de sucesso confirma o arquivo na pasta. Confira no Google Drive se o envio à nuvem terminou; sem conexão, a sincronização poderá ficar pendente.')
        ttk.Label(corpo, text=texto, wraplength=550, justify='left').grid(row=1, column=0, columnspan=2, sticky='w', pady=14)
        try:
            dados = drive.carregar_config(self.banco.parent)
        except ValueError as erro:
            dados = {}
            messagebox.showwarning('Reconfigurar backup', str(erro), parent=popup)
        caminho = tk.StringVar(value=dados.get('pasta', ''))
        ttk.Entry(corpo, textvariable=caminho, width=65).grid(row=2, column=0, sticky='ew')
        def escolher():
            pasta = filedialog.askdirectory(parent=popup, title='Escolher pasta sincronizada pelo Google Drive', mustexist=True)
            if pasta:
                caminho.set(pasta)
        ttk.Button(corpo, text='Escolher...', command=escolher).grid(row=2, column=1, padx=(8, 0))
        try:
            ultima = datetime.fromisoformat(dados['ultimo_backup']).astimezone().strftime('%d/%m/%Y às %H:%M')
        except (KeyError, ValueError, TypeError):
            ultima = 'nenhuma registrada'
        status = tk.StringVar(value='Última cópia na pasta: ' + ultima + '\nA sincronização remota não é verificada pelo aplicativo.')
        ttk.Label(corpo, textvariable=status, wraplength=550, style='Muted.TLabel').grid(row=3, column=0, columnspan=2, sticky='w', pady=12)
        def salvar():
            try:
                drive.configurar(self.banco, caminho.get())
                status.set('Backup ao fechar ativado. Use “Fazer cópia agora” para testar a pasta selecionada.')
            except (ValueError, OSError) as erro:
                messagebox.showerror('Configuração não salva', str(erro), parent=popup)
        def desativar():
            try:
                drive.desativar(self.banco)
                caminho.set('')
                status.set('Backup na pasta do Drive desativado. As cópias existentes e os backups locais foram preservados.')
            except OSError as erro:
                messagebox.showerror('Configuração não salva', str(erro), parent=popup)
        acoes = ttk.Frame(corpo)
        acoes.grid(row=4, column=0, columnspan=2, sticky='ew')
        ttk.Button(acoes, text='Salvar configuração', command=salvar, style='Primary.TButton').pack(side='left')
        ttk.Button(acoes, text='Fazer cópia agora', command=lambda: self.iniciar(False, popup)).pack(side='left', padx=8)
        ttk.Button(acoes, text='Desativar', command=desativar).pack(side='left')
        ttk.Button(acoes, text='Fechar', command=popup.destroy).pack(side='right', padx=(8, 0))
        popup.bind('<Escape>', lambda e: popup.destroy())
        popup.update_idletasks()
        x = max(0, self.janela.winfo_rootx() + (self.janela.winfo_width() - popup.winfo_reqwidth()) // 2)
        y = max(0, self.janela.winfo_rooty() + (self.janela.winfo_height() - popup.winfo_reqheight()) // 2)
        popup.geometry(f'+{x}+{y}')
        return popup

    def fechar(self):
        self.iniciar(True)

    def iniciar(self, fechar=False, parent=None):
        if self.ocupado:
            return
        parent = parent or self.janela
        try:
            dados = drive.carregar_config(self.banco.parent)
            if not dados.get('pasta'):
                if fechar:
                    self.janela.destroy()
                else:
                    messagebox.showinfo('Configurar backup', 'Salve a configuração de uma pasta antes de criar a cópia.', parent=parent)
                return
        except ValueError as erro:
            self._falha(erro, fechar, parent)
            return
        self.ocupado = True
        progresso = tk.Toplevel(self.janela)
        progresso.title('Criando backup')
        progresso.transient(self.janela)
        progresso.protocol('WM_DELETE_WINDOW', lambda: None)
        ttk.Label(progresso, text='Criando e verificando a cópia do banco...\nAguarde antes de fechar o programa.', padding=24).pack()
        progresso.grab_set()
        resultados = queue.Queue()
        def trabalhar():
            try:
                resultados.put((True, drive.executar(self.banco, dados)))
            except Exception as erro:
                resultados.put((False, erro))
        threading.Thread(target=trabalhar, daemon=True).start()
        def acompanhar():
            try:
                sucesso, resultado = resultados.get_nowait()
            except queue.Empty:
                self.janela.after(100, acompanhar)
                return
            progresso.grab_release()
            progresso.destroy()
            self.ocupado = False
            destino_mensagem = parent if parent.winfo_exists() else self.janela
            if not sucesso:
                self._falha(resultado, fechar, destino_mensagem)
                return
            avisos = resultado['avisos']
            if avisos:
                messagebox.showwarning('Cópia criada com observações', '\n'.join(avisos), parent=destino_mensagem)
            if fechar:
                self.janela.destroy()
            else:
                messagebox.showinfo('Cópia verificada na pasta', f"Arquivo: {resultado['arquivo']}\n\nConfira no Google Drive se a sincronização com a nuvem foi concluída.", parent=destino_mensagem)
        self.janela.after(100, acompanhar)

    def _falha(self, erro, fechar, parent):
        texto = f'Não foi possível concluir a cópia na pasta do Drive.\n{erro}\n\nOs dados continuam no banco local. Verifique a pasta, o espaço disponível e o Google Drive.'
        if fechar:
            if messagebox.askyesno('Backup não concluído', texto + '\n\nFechar mesmo assim? Escolha Não para continuar no programa e tentar novamente.', parent=parent):
                self.janela.destroy()
        else:
            messagebox.showerror('Backup não concluído', texto, parent=parent)
