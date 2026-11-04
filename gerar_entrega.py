"""Gera notebook executado, gráficos e relatório HTML a partir da coleta local."""
from pathlib import Path
import ast
import base64
import html
import json
import textwrap
import zipfile
import importlib.metadata
from string import Template

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat as nbf
from nbclient import NotebookClient
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

import analise as a

BASE = a.BASE
IDENTIFICACAO = '**Instituição:** Católica de Santa Catarina\n\n**Disciplina:** Ciência de Dados\n\n**Professor:** Claudinei Dias (Ney)\n\n**Integrantes:** André Schultz; José Henrique Brühmüller; Lucas Monich Nunes.'
OUT = BASE / 'resultados'
OUT.mkdir(exist_ok=True)
brutas = pd.read_csv(BASE / 'dados' / 'avaliacoes_brutas.csv')
df, resumo, matriz, m = a.analisar(brutas)
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':11, 'axes.spines.top':False, 'axes.spines.right':False})
cores = ['#187864', '#bd4b43']

def salvar(fig, nome):
    fig.savefig(OUT / nome, dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
cont = df.sentimento.value_counts().reindex(['Positivo','Negativo'], fill_value=0)
bars = axes[0].bar(cont.index, cont.values, color=cores, width=.55)
axes[0].bar_label(bars, labels=[f'{n} ({n/len(df):.1%})' for n in cont.values], padding=5)
axes[0].set_ylim(0, max(cont.values)*1.2)
axes[0].set_ylabel('Comentários classificados')
axes[0].set_title('Sentimento do texto | amostra coletada')
resumo[['positivos','negativos']].rename(columns={'positivos':'Positivo','negativos':'Negativo'}).plot.barh(stacked=True, color=cores, ax=axes[1])
axes[1].set_ylabel('')
axes[1].set_xlabel('Número de comentários')
axes[1].set_title('Comparação entre produtos')
fig.tight_layout()
salvar(fig, 'sentimentos.png')

fig, ax = plt.subplots(figsize=(6, 4.7))
ax.imshow(matriz.values, cmap='Blues')
ax.set_xticks([0,1], ['Negativo','Positivo'])
ax.set_yticks([0,1], ['Negativo (1–2 estrelas)','Positivo (4–5 estrelas)'])
ax.set_xlabel('Previsto pelo texto (LeIA)')
ax.set_ylabel('Referência aproximada pelas estrelas')
ax.set_title('Concordância com as estrelas\nNão equivale a validação humana')
for (i,j), v in __import__('numpy').ndenumerate(matriz.values):
    ax.text(j,i,str(v),ha='center',va='center',color='white' if v>matriz.values.max()/2 else '#172333',fontsize=18)
salvar(fig, 'matriz_estrelas.png')

# Frequência documental: cada termo conta no máximo uma vez por comentário.
neg = df.loc[df.sentimento.eq('Negativo'), 'comentario']
if len(neg):
    vec = CountVectorizer(stop_words='a o os as um uma de do da dos das e ou que para por com no na nos nas em se ao aos eu me meu minha muito mais este estes esta estas sao foi ser tem como mas nao'.split(), binary=True, min_df=1)
    X = vec.fit_transform(neg)
    termos = pd.Series(X.sum(axis=0).A1, index=vec.get_feature_names_out()).sort_values(ascending=False).head(15)
    termos.rename_axis('termo').rename('comentarios_negativos_com_termo').to_csv(OUT/'termos_negativos.csv', encoding='utf-8-sig')
    fig,ax=plt.subplots(figsize=(8,5))
    termos.sort_values().plot.barh(ax=ax, color='#bd4b43')
    ax.set_xlabel('Comentários negativos que mencionam o termo')
    ax.set_title('Termos frequentes nos textos classificados como negativos\nMenção não determina sentimento sobre o aspecto')
    salvar(fig, 'termos_negativos.png')

temas = {'Som':r'\b(?:som|audio|áudio|graves?|agudos?|frequências?|frequencias?|sonor\w*)\b',
         'Conforto':r'\b(?:confort\w*|desconfort\w*|orelhas?|almofadas?|apert\w*|pesad\w*)\b',
         'Construção e durabilidade':r'\b(?:constru\w*|dur\w*|cabo|cabos|plástico|plastico|quebr\w*|desgast\w*)\b',
         'Preço e valor':r'\b(?:preço|preços|preco|precos|barat\w*|caro|caros|valor|custo)\b'}
tema_rows=[]
for tema,rx in temas.items():
    menciona=df.comentario.str.contains(rx,case=False,regex=True)
    tema_rows.append({'tema':tema,'comentarios_com_mencao':int(menciona.sum()),'em_textos_negativos':int((menciona & df.sentimento.eq('Negativo')).sum())})
temas_df=pd.DataFrame(tema_rows)
temas_df.to_csv(OUT/'temas.csv',index=False,encoding='utf-8-sig')

inicio = pd.to_datetime(df.data_avaliacao).min().strftime('%d/%m/%Y')
fim = pd.to_datetime(df.data_avaliacao).max().strftime('%d/%m/%Y')
data_coleta = pd.to_datetime(df.coletado_em,utc=True).min().tz_convert('America/Sao_Paulo').strftime('%d/%m/%Y')
melhor=resumo.percentual_positivo.idxmax()
pct=100*m['positivos']/m['n_validas']

metodo = """Foram escolhidos três fones da Thomann Portuguesa: Superlux HD-681, Audio-Technica
ATH-M50X e beyerdynamic DT-770 Pro 80 Ohm. Coletaram-se as páginas disponíveis no filtro
português (reviewlang[]=6), ordenadas por data (order=latest), com limite de dez páginas
por produto e parada na última página incompleta. Há 67, 31 e 42 avaliações brutas,
respectivamente, totalizando 140 em 16 páginas HTML. São avaliações originais, sem tradução.

A extração usa requests e BeautifulSoup, intervalo de 1,5 s entre downloads, cache,
URLs, horários e hashes SHA-256. Reexecuções usam os HTMLs incluídos, sem novos downloads.
Não há login, APIs internas nem contorno de bloqueios.

O filtro do site também retornou textos em inglês. Por isso, além do atributo pt no HTML,
exigiu-se identificação pt pelo langdetect com valor >= 0,8 e semente fixa 0. Este valor é um
escore interno do detector, sem calibração como garantia de idioma. A regra conservadora
pode excluir comentários curtos em português. As decisões estão em dados/auditoria_idioma.csv.
Removeram-se espaços repetidos, vazios e duplicatas por produto/ID ou texto normalizado.

O sentimento é calculado pelo LeIA (Léxico para Inferência Adaptada), adaptação do VADER
ao português. Não se treinou um classificador supervisionado. Foram fixados o código,
os léxicos e a licença MIT do LeIA na pasta vendor, com referência ao commit original.
Há uma correção explícita na integração: a entrada lexical nao (-1,2) foi removida para
permitir sua atuação como operador de negação. Antes disso, a frase de teste com som não bom
recebia resultado positivo. Testes cobrem essa regressão e a leitura dos arquivos em UTF-8.
As demais regras do LeIA foram preservadas. A correção não elimina outras limitações do modelo.

O título e o comentário alimentam o modelo; estrelas nunca são entrada. O texto com acentos
fica preservado no CSV, embora o LeIA normalize acentos internamente. Preservam-se caixa,
pontuação e negações na entrada. O compound varia entre -1 e +1 e não é uma probabilidade.

Para a saída binária solicitada, compound >= 0 é Positivo e compound < 0 é Negativo.
Resultados com |compound| < 0,05 são sinalizados como baixa polaridade, incluindo zero,
atribuído a Positivo por convenção. Não são evidência firme de satisfação.

Na comparação auxiliar, 4–5 estrelas são referência positiva e 1–2, negativa. Três estrelas
ficam fora da comparação. Esses rótulos são fracos: notas e tom do texto podem divergir.
A matriz mede concordância com as estrelas e não acurácia validada por anotadores humanos.
O léxico também falha em expressões, negações complexas e termos técnicos de áudio."""

conclusoes = f'''A amostra contém **{m['n_validas']} comentários válidos**, sendo **{m['positivos']} positivos
({pct:.1f}%)** e **{m['negativos']} negativos ({100-pct:.1f}%)**. Foram excluídos
{m['n_excluidas_idioma']} registros pelo critério adicional de idioma; a base bruta tem {m['n_brutas']} registros. Há {m['baixa_polaridade']} textos de baixa polaridade.

O maior percentual positivo observado foi o de **{melhor}**
({resumo.loc[melhor,'percentual_positivo']:.1f}%, n={resumo.loc[melhor,'avaliacoes']:.0f}).
Esse resultado descreve a janela coletada; não demonstra superioridade do produto.
O número de comentários e o período coberto devem acompanhar qualquer comparação.

Na referência de {m['referencia_n']} avaliações de 1–2 ou 4–5 estrelas,
a concordância foi **{m['concordancia_estrelas']:.1%}**, com {m['divergencias']} divergências.
Quantidade de referências negativas nessa comparação: {m['referencia_negativos']};
o desbalanceamento exige examinar a matriz e impede tratar a concordância global como prova de qualidade.

A leitura exploratória dos comentários 4508250 e 4336883 do Superlux mostra elogios ao som
acompanhados de desconforto depois de horas de uso, mesmo com quatro estrelas.
No ATH-M50X, o comentário 4955954 também cita o peso como limitador do tempo de uso.
São exemplos que sugerem investigar ergonomia e duração das sessões, sem medir a
prevalência de cada problema na população de compradores.

Há falsos negativos plausíveis: o comentário 3505487 elogia a definição das frequências
graves, mas o classificador retorna negativo. O léxico pode interpretar termos técnicos
como palavras de polaridade. Já o 2730701 recomenda o produto e nega haver aspectos
negativos, mas também recebe classificação negativa. Esses casos mostram que os
percentuais calculados não devem ser usados diretamente como taxa de insatisfação.

Como referência de desbalanceamento, prever sempre Positivo concordaria com
{(m['referencia_n']-m['referencia_negativos'])/m['referencia_n']:.1%} das estrelas elegíveis.
Essa referência supera a concordância do LeIA nesta amostra; o modelo lexical não está
validado para decisões sobre reclamações. A presença de apenas uma referência negativa
também impede conclusões robustas sobre sua capacidade de reconhecer insatisfação.

As tabelas de temas e termos ajudam a priorizar a leitura: som, conforto, construção/durabilidade
e preço podem aparecer tanto em elogios quanto em reclamações. As contagens de menções não são
uma análise de sentimento por aspecto e os temas podem se sobrepor.

Como ação prática, recomenda-se revisar primeiro as divergências com as estrelas e os textos de
baixa polaridade. Depois, categorizar manualmente as reclamações de conforto, peso e construção
antes de propor melhorias, devoluções ou mudanças na descrição do produto.

Esta é uma amostra por conveniência, limitada ao português e às páginas disponíveis no momento.
Não é uma estimativa representativa de todos os compradores, das vendas ou do mercado.
Comentários de várias datas podem aparecer nas páginas mais recentes; não há inferência causal.
Uma evolução seria construir uma amostra anotada por duas pessoas e medir precisão, recall e F1
por classe em dados independentes, comparando LeIA com Naive Bayes ou outro modelo.'''

fontes = '''- Loja e páginas de avaliações: https://www.thomann.pt/superlux_hd681_reviews.htm ; https://www.thomann.pt/audio_technica_ath_m50_x_reviews.htm ; https://www.thomann.pt/beyerdynamic_dt770_pro80_ohm_reviews.htm
- Regras consultadas: https://www.thomann.pt/robots.txt (cópia na pasta dados/html).
- LeIA: Rafael J. A. Almeida (2018). https://github.com/rafjaa/LeIA (commit fixado em vendor/ORIGEM.md).
- VADER, base original do LeIA: Hutto, C. J.; Gilbert, E. (2014). *VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text*. ICWSM. https://github.com/cjhutto/vaderSentiment
- langdetect: https://pypi.org/project/langdetect/
- BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- Material de apoio fornecido: “Aula 05 — Data Scraping com BeautifulSoup”, Renato Vimieiro (2017), e “Análise de sentimentos — Utilizando Python para construir e treinar modelos de machine learning”, Wheslley Rimar Bezerra. Foram usados como referências didáticas; os exercícios e procedimentos do material não substituem o pedido do usuário. Aqui foi escolhida uma abordagem lexical, com avaliação auxiliar por estrelas, em vez de reproduzir o treino supervisionado do PDF.'''

md = f'''# Web scraping e análise de sentimentos em produtos de e-commerce

{IDENTIFICACAO}

**Loja:** Thomann Portuguesa | **Coleta:** {data_coleta} (America/Sao_Paulo)
**Datas dos comentários na amostra:** {inicio} a {fim}.

## Objetivo
Coletar produtos e seus comentários em um e-commerce, classificar o sentimento em Positivo/Negativo e apresentar resultados e insights verificáveis.

## Método
{metodo}

## Resultados por produto
```text
{resumo.round(3).to_string()}
```

![Distribuição de sentimentos](sentimentos.png)

![Comparação com as estrelas](matriz_estrelas.png)

## Temas mencionados
```text
{temas_df.to_string(index=False)}
```

![Termos nos comentários negativos](termos_negativos.png)

## Insights e limitações
{conclusoes}

## Fontes
{fontes}
'''
(OUT/'RELATORIO.md').write_text(md,encoding='utf-8')

def paragrafos(txt):
    return ''.join('<p>'+html.escape(p.strip()).replace('\n',' ')+'</p>' for p in txt.split('\n\n'))

def imagem(nome):
    b64=base64.b64encode((OUT/nome).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b64}" alt="{nome}">'

cards=''.join(f'<div class="card"><strong>{v}</strong><span>{k}</span></div>' for k,v in [('Comentários',m['n_validas']),('Positivos',f'{pct:.1f}%'),('Negativos',f'{100-pct:.1f}%'),('Baixa polaridade',m['baixa_polaridade'])])
documento=f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Análise de sentimentos | Thomann</title><style>
body{{font:17px/1.6 system-ui,sans-serif;color:#233044;background:#edf2f3;margin:0}}main{{max-width:1080px;margin:auto;padding:48px 30px;background:white}}
h1{{font-size:40px;line-height:1.15;color:#133c42}}h2{{margin-top:40px;color:#185951}}.eyebrow{{color:#187864;letter-spacing:2px;font-size:13px;font-weight:bold}}
.cards{{display:flex;gap:16px;flex-wrap:wrap}}.card{{flex:1;background:#edf5f2;padding:20px;min-width:130px}}.card strong{{display:block;font-size:32px;color:#185951}}.card span{{font-size:14px}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:10px;border-bottom:1px solid #dde4e6;text-align:left}}th{{background:#edf5f2}}.scroll{{overflow:auto}}img{{width:100%;height:auto;margin:15px 0}}
.note{{border-left:4px solid #c59145;background:#fff6e9;padding:16px}}a{{color:#187864}}footer{{font-size:13px;margin-top:40px;overflow-wrap:anywhere}}
</style><main><div class="eyebrow">CIÊNCIA DE DADOS · ESTUDO APLICADO</div><h1>O que os comentários dizem<br>sobre três fones de ouvido?</h1>
{paragrafos(IDENTIFICACAO.replace('**', ''))}
<p>Web scraping e análise de sentimentos · Thomann Portuguesa · Coleta em {data_coleta}</p><div class="cards">{cards}</div>
<p class="note">Resultados da amostra coletada. A classificação é automática; a comparação com estrelas usa rótulos aproximados, sem validação humana.</p>
<h2>Resultados</h2>{imagem('sentimentos.png')}<div class="scroll">{resumo.round(3).to_html()}</div>
<p>Datas dos comentários na amostra: {inicio} a {fim}. Filtro português, com verificação adicional do idioma e exclusão de casos incertos.</p>
<h2>Como a análise foi feita</h2>{paragrafos(metodo)}
<h2>Comparação com as notas</h2>{imagem('matriz_estrelas.png')}
<h2>O que merece investigação</h2><div class="scroll">{temas_df.to_html(index=False)}</div>{imagem('termos_negativos.png')}
<h2>Insights e limitações</h2>{paragrafos(conclusoes.replace('**',''))}
<footer><h2>Fontes e rastreabilidade</h2>{paragrafos(fontes)}<p>Os CSVs, páginas HTML, horários e hashes estão na pasta dados. O notebook reproduz as etapas com o cache local.</p></footer></main></html>'''
(OUT/'RELATORIO.html').write_text(documento,encoding='utf-8')

# O código do extrator fica visível no notebook e funciona sem importar analise.py.
source=(BASE/'analise.py').read_text(encoding='utf-8')
tree=ast.parse(source)
functions={n.name:ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
imports=source[:source.index('\ndef classificar')].replace('Path(__file__).resolve().parent','Path.cwd()')
cells=[]
def markdown(t):cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(t).strip()))
def code(t):cells.append(nbf.v4.new_code_cell(textwrap.dedent(t).strip()))
markdown(f'''# Análise de sentimentos em produtos de e-commerce

Atividade de Ciência de Dados.

{IDENTIFICACAO}

**Objetivo:** coletar produtos e comentários, identificar sentimento Positivo/Negativo e apresentar insights.

Coleta: **{data_coleta}**. Entrega com dados reais coletados e resultados executados.
No Colab, escolha **Ambiente de execução > Executar tudo**: a primeira célula baixa os arquivos do projeto quando necessário e instala dependências ausentes.
Localmente, abra este notebook na raiz do projeto. Após obter os arquivos, as células usam o cache HTML incluído para reproduzir a coleta sem acessar a loja.
Não há treinamento nesta abordagem; LeIA é uma linha de base lexical para português, com limitações demonstradas nesta amostra.''')
markdown('## Preparação do ambiente\nNo Colab, esta célula obtém os arquivos complementares do repositório público. Localmente, verifica a pasta de execução. O código não modifica o repositório remoto.')
code((BASE / 'preparar_notebook.py').read_text(encoding='utf-8') + '\n\npreparar_ambiente()')
markdown('## 1. Escolha da loja, amostragem e método\n'+metodo)
code(imports)
markdown('## 2. Extração do HTML com BeautifulSoup\nCada bloco `.js-review` contém título, texto original, idioma e estrelas. A data é extraída sem exportar o nome do autor para o CSV. A nota vem da largura percentual das estrelas preenchidas.')
code(functions['extrair_avaliacoes'])
markdown('## 3. Coleta, cache e rastreabilidade\nAs URLs incluem produto, página, ordenação e idioma. O manifesto guarda horário e SHA-256 de cada HTML. Com o cache completo, esta etapa apenas reprocessa arquivos locais. Para uma nova coleta independente, use uma cópia desta pasta sem o diretório `dados/html`; preserve a coleta entregue.')
code(functions['coletar'])
code('brutas = coletar(paginas=10)\nprint("Registros brutos:", len(brutas))\nbrutas[["produto", "review_id", "nota", "idioma", "data_avaliacao"]].head()')
markdown('## 4. Classificação e limpeza\nPreservamos o texto original para não apagar as pistas que LeIA utiliza. A classificação usa somente título e comentário. `baixa_polaridade` sinaliza resultados próximos de zero; o desempate em zero é positivo por convenção binária.')
code(functions['classificar']+'\n\n'+functions['analisar'])
code('df, resumo, matriz, metricas = analisar(brutas)\nassert not df.duplicated(["produto", "review_id"]).any()\nassert df.sentimento.isin(["Positivo", "Negativo"]).all()\nassert df.score.between(-1, 1).all()\nassert df.idioma.eq("pt").all()\nassert df.nota.between(1, 5).all()\nprint(json.dumps(metricas, indent=2, ensure_ascii=False))\nresumo.round(3)')
markdown('## 5. Distribuição de sentimentos e comparação por produto')
plot_source = Path(__file__).read_text(encoding='utf-8')
plot_source = plot_source[plot_source.index('plt.rcParams.update'):plot_source.index('\ntemas =')]
code('import matplotlib.pyplot as plt\nfrom sklearn.feature_extraction.text import CountVectorizer\nfrom IPython.display import display, Image\nOUT = BASE / "resultados"\nOUT.mkdir(exist_ok=True)\nm = metricas\n'+plot_source+'\ndisplay(Image(filename=str(OUT / "sentimentos.png")))')
markdown('## 6. Comparação com estrelas (referência fraca)\nLinhas: referência por estrelas; colunas: classificação pelo texto. Três estrelas ficam fora desta comparação. Esses resultados não são uma acurácia validada por anotadores.')
code('display(matriz)\ndisplay(Image(filename=str(BASE / "resultados" / "matriz_estrelas.png")))')
markdown('## 7. Exemplos verificáveis\nA tabela contém comentários negativos e divergências para inspeção. O texto completo, ID e URL estão no CSV; a tabela abaixo mostra trechos de até 180 caracteres.')
code('exemplos = pd.concat([df[df.sentimento.eq("Negativo")].head(6), df[df.divergencia].head(6)]).drop_duplicates(["produto", "review_id"])\nexemplos = exemplos.assign(trecho=exemplos.comentario.str[:180])\nexemplos[["produto", "review_id", "nota", "score", "sentimento", "trecho"]]')
markdown('## 8. Temas e frequência documental\nOs temas usam expressões explícitas; o mesmo comentário pode mencionar vários temas. A coluna em_textos_negativos descreve a polaridade global do comentário, sem inferir sentimento sobre cada aspecto.')
code('import warnings\nwith warnings.catch_warnings():\n    warnings.simplefilter("ignore", UserWarning)\n    temas = '+repr(temas)+'\n    temas_resultado = []\n    for tema, rx in temas.items():\n        menciona = df.comentario.str.contains(rx, case=False, regex=True)\n        temas_resultado.append({"tema": tema, "comentarios_com_mencao": int(menciona.sum()), "em_textos_negativos": int((menciona & df.sentimento.eq("Negativo")).sum())})\ndisplay(pd.DataFrame(temas_resultado))\ndisplay(Image(filename=str(BASE / "resultados" / "termos_negativos.png")))')
markdown('## 9. Insights e limitações\n'+conclusoes)
markdown('## 10. Referências\n'+fontes)
nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.13'}})
nbpath=BASE/'Analise_Sentimentos_Ecommerce.ipynb'
nbf.write(nb,nbpath)
NotebookClient(nb,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(BASE)}}).execute()
nbf.write(nb,nbpath)

deps=['requests','beautifulsoup4','pandas','langdetect','matplotlib','scikit-learn','nbformat','nbclient','ipykernel','tzdata']
(BASE/'requirements.txt').write_text('\n'.join(f'{p}=={importlib.metadata.version(p)}' for p in deps)+'\n',encoding='utf-8')
linhas = ['| Produto | Comentários | Positivos | Negativos | % positivo |', '|---|---:|---:|---:|---:|']
for produto, row in resumo.iterrows():
    percentual = f"{row['percentual_positivo']:.1f}%".replace('.', ',')
    linhas.append(f"| {produto} | {int(row['avaliacoes'])} | {int(row['positivos'])} | {int(row['negativos'])} | {percentual} |")
texto_readme = Template((BASE / 'docs' / 'README.template.md').read_text(encoding='utf-8')).substitute(
    data_coleta=data_coleta, n_brutas=m['n_brutas'], n_excluidas=m['n_excluidas_idioma'],
    n_validas=m['n_validas'], baixa_polaridade=m['baixa_polaridade'], positivos=m['positivos'],
    negativos=m['negativos'], resumo_produtos='\n'.join(linhas), referencia_n=m['referencia_n'],
    referencia_negativos=m['referencia_negativos'],
    concordancia=f"{m['concordancia_estrelas']:.1%}".replace('.', ','),
    baseline=f"{(m['referencia_n']-m['referencia_negativos'])/m['referencia_n']:.1%}".replace('.', ','),
)
(BASE / 'README.md').write_text(texto_readme, encoding='utf-8')

with zipfile.ZipFile(BASE.parent/'Analise_Sentimentos_Ecommerce_PT.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in BASE.rglob('*'):
        if p.is_file() and not any(x in p.parts for x in ['__pycache__', '.git', '.venv']):
            z.write(p, Path(BASE.name)/p.relative_to(BASE))
print('Entrega gerada:',nbpath)
print(json.dumps(m,indent=2))
