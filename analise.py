"""Web scraping e análise de sentimentos de avaliações de fones na Thomann."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlencode, urlparse
from urllib.robotparser import RobotFileParser
import hashlib
import json
import re
import time

import requests
from bs4 import BeautifulSoup
import pandas as pd
from langdetect import detect_langs, DetectorFactory, LangDetectException
from vendor.leia import SentimentIntensityAnalyzer

BASE = Path(__file__).resolve().parent
PRODUTOS = ['superlux_hd681', 'audio_technica_ath_m50_x', 'beyerdynamic_dt770_pro80_ohm']
AGENTE = 'EstudoAcademicoSentimentos/1.0'
LEIA = SentimentIntensityAnalyzer()
# No léxico original, "nao" tem peso -1,2 e impede a regra de negação das palavras seguintes.
# Removemos essa entrada para que o termo funcione como operador de negação.
LEIA.lexicon.pop("nao", None)
DetectorFactory.seed = 0


def identificar_idioma(texto):
    try:
        resultado = detect_langs(texto)[0]
        return dict(idioma_detectado=resultado.lang, confianca_idioma=resultado.prob)
    except LangDetectException:
        return dict(idioma_detectado='indeterminado', confianca_idioma=0.0)


def classificar(texto):
    score = LEIA.polarity_scores(texto)['compound']
    return dict(score=score, sentimento='Positivo' if score >= 0 else 'Negativo',
                baixa_polaridade=abs(score) < 0.05)


def extrair_avaliacoes(html, url, coletado_em):
    soup = BeautifulSoup(html, 'html.parser')
    produto = soup.h1.get_text(' ', strip=True)
    rows = []
    for item in soup.select('.js-review'):
        corpo = item.select_one('.js-text-original')
        titulo = item.select_one('.js-headline-original')
        estrelas = item.select_one('.review-intro .fx-rating-stars__filler')
        autor_data = item.select_one('.review-intro__author')
        if corpo is None:
            continue
        nota = None
        if estrelas:
            pct = re.search(r'width:\s*([\d.]+)%', estrelas.get('style', ''))
            if pct:
                nota = float(pct[1]) / 20
        data = re.search(r'\b(\d{2}\.\d{2}\.\d{4})\b', autor_data.get_text() if autor_data else '')
        rows.append(dict(produto=produto, review_id=item.get('data-rating-id'),
                         titulo=titulo.get_text(' ', strip=True) if titulo else '',
                         comentario=corpo.get_text(' ', strip=True), idioma=corpo.get('lang', ''),
                         nota=nota, data_avaliacao=datetime.strptime(data[1], '%d.%m.%Y').date().isoformat() if data else None,
                         url_origem=url, coletado_em=coletado_em))
    return rows


def coletar(paginas=10):
    """Cache e pausa de 1,5 s; sem login, APIs internas ou contorno de bloqueios."""
    cache = BASE / 'dados' / 'html'
    cache.mkdir(parents=True, exist_ok=True)
    sessao = requests.Session()
    sessao.headers['User-Agent'] = AGENTE
    dominio = 'https://www.thomann.pt'
    robots_path = cache / 'robots.txt'
    if not robots_path.exists():
        r = sessao.get(dominio + '/robots.txt', timeout=40)
        r.raise_for_status()
        robots_path.write_text(r.text, encoding='utf-8')
    robots = RobotFileParser()
    robots.parse(robots_path.read_text(encoding='utf-8').splitlines())
    registros, manifesto = [], []
    for slug in PRODUTOS:
        ids_vistos = set()
        for pagina in range(1, paginas + 1):
            url = f'{dominio}/{slug}_reviews.htm?' + urlencode({'page': pagina, 'order': 'latest', 'reviewlang[]': 6})
            if not robots.can_fetch(AGENTE, url):
                raise RuntimeError(f'Coleta interrompida pelo robots.txt: {url}')
            arquivo = cache / f'{slug}_{pagina:02}.html'
            meta = arquivo.with_suffix('.json')
            if not arquivo.exists():
                time.sleep(1.5)
                r = sessao.get(url, timeout=40)
                r.raise_for_status()
                if urlparse(r.url).netloc != urlparse(url).netloc:
                    raise RuntimeError('Redirecionamento para outro domínio; revisar antes de continuar.')
                html = r.content.decode('utf-8')
                rows = extrair_avaliacoes(html, url, '')
                if not rows:
                    raise RuntimeError(f'Nenhuma avaliação: possível alteração do HTML em {url}')
                arquivo.write_text(html, encoding='utf-8')
                meta.write_text(json.dumps(dict(url=url, coletado_em=datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),
                                               sha256=hashlib.sha256(arquivo.read_bytes()).hexdigest()), indent=2), encoding='utf-8')
            info = json.loads(meta.read_text(encoding='utf-8'))
            html = arquivo.read_text(encoding='utf-8')
            assert hashlib.sha256(arquivo.read_bytes()).hexdigest() == info['sha256'], 'Cache alterado'
            rows = extrair_avaliacoes(html, info['url'], info['coletado_em'])
            novos = {x['review_id'] for x in rows} - ids_vistos
            if not novos:
                break  # Detecta última página ou servidor ignorando a paginação.
            ids_vistos.update(novos)
            registros.extend(rows)
            manifesto.append(dict(arquivo=arquivo.name, **info, n_extraidas=len(rows)))
            print(f'{slug}: página {pagina}, {len(rows)} avaliações', flush=True)
            if len(rows) < 10:
                break
    df = pd.DataFrame(registros)
    df.to_csv(BASE / 'dados' / 'avaliacoes_brutas.csv', index=False, encoding='utf-8-sig')
    (BASE / 'dados' / 'manifesto.json').write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding='utf-8')
    return df


def analisar(brutas):
    df = brutas.copy()
    df['comentario'] = df.comentario.fillna('').str.replace(r'\s+', ' ', regex=True).str.strip()
    n_inicial = len(df)
    idiomas = pd.DataFrame(df.comentario.map(identificar_idioma).tolist())
    df = pd.concat([df.reset_index(drop=True), idiomas], axis=1)
    df['incluir_idioma'] = df.idioma.eq('pt') & df.idioma_detectado.eq('pt') & df.confianca_idioma.ge(0.8)
    df.to_csv(BASE / 'dados' / 'auditoria_idioma.csv', index=False, encoding='utf-8-sig')
    n_excluidas_idioma = int((~df.incluir_idioma).sum())
    df = df[df.incluir_idioma & df.comentario.ne('')].copy()
    df = df.drop_duplicates(['produto', 'review_id'])
    df['texto_normalizado'] = (df.titulo.fillna('') + ' ' + df.comentario).str.lower().str.replace(r'\s+', ' ', regex=True).str.strip()
    df = df.drop_duplicates(['produto', 'texto_normalizado']).reset_index(drop=True)
    df['texto_analisado'] = df.titulo.fillna('') + '. ' + df.comentario
    scores = pd.DataFrame(df.texto_analisado.map(classificar).tolist())
    df = pd.concat([df, scores], axis=1)
    df['referencia_estrelas'] = df.nota.map(lambda x: 'Positivo' if x >= 4 else ('Negativo' if x <= 2 else 'Sem referência'))
    df['divergencia'] = df.referencia_estrelas.ne('Sem referência') & df.sentimento.ne(df.referencia_estrelas)
    df.to_csv(BASE / 'dados' / 'avaliacoes_classificadas.csv', index=False, encoding='utf-8-sig')
    resumo = df.groupby('produto').agg(avaliacoes=('score', 'size'), positivos=('sentimento', lambda x: x.eq('Positivo').sum()),
        negativos=('sentimento', lambda x: x.eq('Negativo').sum()), nota_media=('nota', 'mean'), score_medio=('score', 'mean'))
    resumo['percentual_positivo'] = 100 * resumo.positivos / resumo.avaliacoes
    resumo.to_csv(BASE / 'dados' / 'resumo_produtos.csv', encoding='utf-8-sig')
    ref = df[df.referencia_estrelas.ne('Sem referência')]
    matriz = pd.crosstab(ref.referencia_estrelas, ref.sentimento).reindex(index=['Negativo', 'Positivo'], columns=['Negativo', 'Positivo'], fill_value=0)
    matriz.to_csv(BASE / 'dados' / 'matriz_estrelas.csv', encoding='utf-8-sig')
    metricas = dict(n_brutas=n_inicial, n_validas=len(df), n_removidas=n_inicial-len(df),
        n_excluidas_idioma=n_excluidas_idioma,
        positivos=int(df.sentimento.eq('Positivo').sum()), negativos=int(df.sentimento.eq('Negativo').sum()),
        baixa_polaridade=int(df.baixa_polaridade.sum()), referencia_n=len(ref),
        referencia_negativos=int(ref.referencia_estrelas.eq('Negativo').sum()),
        concordancia_estrelas=float(ref.sentimento.eq(ref.referencia_estrelas).mean()), divergencias=int(df.divergencia.sum()))
    (BASE / 'dados' / 'metricas.json').write_text(json.dumps(metricas, indent=2), encoding='utf-8')
    return df, resumo, matriz, metricas


if __name__ == '__main__':
    df, resumo, matriz, metricas = analisar(coletar())
    print(resumo.to_string())
    print(json.dumps(metricas, indent=2))
