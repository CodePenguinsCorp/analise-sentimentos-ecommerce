"""Prepara os arquivos do projeto quando o notebook é aberto no Google Colab."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

REPOSITORIO = 'https://github.com/CodePenguinsCorp/analise-sentimentos-ecommerce.git'


def preparar_ambiente(em_colab=None, raiz_colab=None):
    if em_colab is None:
        em_colab = bool(os.environ.get('COLAB_RELEASE_TAG')) or 'google.colab' in sys.modules
    raiz = Path.cwd()
    if em_colab:
        if not (raiz / 'vendor' / 'leia.py').exists():
            raiz = Path(raiz_colab or '/content') / 'analise-sentimentos-ecommerce'
            if not raiz.exists():
                resultado = subprocess.run(
                    ['git', 'clone', '--depth', '1', '--branch', 'main', REPOSITORIO, str(raiz)],
                    capture_output=True, text=True,
                )
                if resultado.returncode:
                    raise RuntimeError(
                        'Não foi possível baixar o projeto do GitHub. Verifique o acesso ao '
                        'repositório ou envie e extraia o ZIP completo no Colab.'
                    )
        if not (raiz / 'vendor' / 'leia.py').exists():
            raise RuntimeError('Pasta do projeto incompleta. Extraia o ZIP completo em uma pasta nova.')
        pacotes = {
            'requests': 'requests', 'bs4': 'beautifulsoup4', 'pandas': 'pandas',
            'langdetect': 'langdetect==1.0.9', 'matplotlib': 'matplotlib',
            'sklearn': 'scikit-learn', 'tzdata': 'tzdata',
        }
        faltantes = [pacote for modulo, pacote in pacotes.items() if importlib.util.find_spec(modulo) is None]
        if faltantes:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *faltantes])
    elif not (raiz / 'vendor' / 'leia.py').exists():
        raise RuntimeError('Abra o notebook na raiz do projeto, junto às pastas dados e vendor.')
    os.chdir(raiz)
    if str(raiz) not in sys.path:
        sys.path.insert(0, str(raiz))
    print('Ambiente pronto. Os dados serão lidos do cache incluído no projeto.')
    return raiz
