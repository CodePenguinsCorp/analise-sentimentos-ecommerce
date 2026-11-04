# Análise de sentimentos em produtos de e-commerce

Atividade de Ciência de Dados: web scraping de produtos e classificação de comentários em português como positivos ou negativos.

[![Abrir no Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/CodePenguinsCorp/analise-sentimentos-ecommerce/blob/main/Analise_Sentimentos_Ecommerce.ipynb)

**Instituição:** Católica de Santa Catarina

**Disciplina:** Ciência de Dados

**Professor:** Claudinei Dias (Ney)

**Integrantes:** André Schultz; José Henrique Brühmüller; Lucas Monich Nunes; Matheus Büsemayer.

## Trabalho principal

Abra **[Analise_Sentimentos_Ecommerce.ipynb](Analise_Sentimentos_Ecommerce.ipynb)**. O notebook contém a documentação acadêmica, o código Python e as saídas da execução, incluindo gráficos, tabelas, exemplos e conclusões.

**Problema:** coletar avaliações de produtos de um e-commerce e identificar seu sentimento pelo texto, apresentando resultados e oportunidades de melhoria.

## Dados e metodologia

- Fonte: [Thomann Portuguesa](https://www.thomann.pt/), com avaliações originais, sem tradução, de três fones de ouvido.
- Coleta em **$data_coleta**, em 16 páginas: **$n_brutas avaliações brutas**.
- Filtro de português da loja (`reviewlang[]=6`), ordenação por data (`order=latest`), até dez páginas por produto e parada na página incompleta.
- Coleta com requests e BeautifulSoup; intervalo de 1,5 s entre downloads, cache HTML, URLs, horários e hashes SHA-256 no [manifesto](dados/manifesto.json).
- Verificação adicional com langdetect, semente 0: **$n_excluidas registros excluídos**, por outro idioma ou identificação incerta. Essa regra conservadora também pode excluir textos curtos em português.
- **$n_validas comentários analisados** após verificar idioma, vazios e duplicatas.
- Método: **LeIA**, adaptação lexical do VADER ao português. A entrada é o título e o comentário; as estrelas ficam fora da classificação.
- Saída binária: compound >= 0 é Positivo; compound < 0 é Negativo. Os **$baixa_polaridade casos com |compound| < 0,05** são sinalizados para revisão. O escore não é uma probabilidade.
- O notebook documenta a correção da entrada lexical `nao`, a comparação auxiliar com estrelas e os limites do método. Não houve treinamento supervisionado.

## Resultados da execução

$resumo_produtos

No total, o modelo classificou **$positivos comentários como positivos** e **$negativos como negativos**.

![Distribuição de sentimentos e comparação entre produtos](resultados/sentimentos.png)

Os exemplos examinados indicam que elogios ao som podem coexistir com queixas de conforto, peso e uso prolongado, inclusive com notas de quatro ou cinco estrelas.

**Limitação importante:** há erros lexicais demonstrados no relatório, inclusive em termos técnicos de áudio e negações complexas. A concordância com estrelas foi **$concordancia** em $referencia_n avaliações elegíveis; prever sempre positivo concordaria com **$baseline**. As estrelas são rótulos fracos e há apenas $referencia_negativos referência negativa nessa comparação. Não houve validação por anotadores humanos. Os percentuais não são uma taxa comprovada de insatisfação ou uma comparação definitiva de qualidade dos produtos.

## Executar no Google Colab

1. Clique no botão **Abrir no Colab** no início desta página ou use o [link direto](https://colab.research.google.com/github/CodePenguinsCorp/analise-sentimentos-ecommerce/blob/main/Analise_Sentimentos_Ecommerce.ipynb).
2. No Colab, escolha **Ambiente de execução > Executar tudo**.
3. A primeira célula prepara o projeto: baixa os arquivos do GitHub quando necessário e instala as dependências ausentes. O notebook usa o cache da coleta incluído, sem precisar acessar novamente a loja.
4. Confira os gráficos, a matriz de comparação, os exemplos e as conclusões. Os CSVs e gráficos são recriados na pasta `resultados/` e em `dados/` da sessão.

Se preferir enviar o notebook manualmente, use **Arquivo > Abrir notebook > Upload**. Envie também o ZIP completo do projeto e extraia seu conteúdo na sessão caso o download do GitHub não esteja disponível. O notebook depende dos léxicos em `vendor/` e das páginas em `dados/html/`.

## Executar localmente

Em um terminal, na pasta do projeto, com Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ipykernel install --user --name sentimentos-atividade --display-name "Sentimentos - Atividade"
.\.venv\Scripts\python.exe verificar.py
```

Abra o notebook no VS Code ou em outro editor com suporte a Jupyter e selecione o kernel **Sentimentos - Atividade**. Execute todas as células em ordem. As versões de referência estão registradas em `requirements.txt`.

Para recriar também os relatórios HTML/Markdown e o pacote completo:

```powershell
.\.venv\Scripts\python.exe gerar_entrega.py
```

## Arquivos

| Arquivo/pasta | Conteúdo |
|---|---|
| `Analise_Sentimentos_Ecommerce.ipynb` | Trabalho completo, executável e com resultados salvos. |
| `preparar_notebook.py` | Preparação do projeto no Colab; código incorporado à primeira célula. |
| `analise.py` | Coleta, extração, verificação do idioma, classificação e agregações. |
| `verificar.py` | Verificações locais do extrator, idioma, negações e baixa polaridade. |
| `gerar_entrega.py` | Geração do notebook executado, gráficos, relatórios e ZIP. |
| `dados/html/` | Snapshot das páginas e seus metadados. |
| `dados/manifesto.json` | URLs, horários, contagens e hashes SHA-256. |
| `dados/avaliacoes_brutas.csv` | Avaliações extraídas antes da verificação de idioma e limpeza. |
| `dados/avaliacoes_classificadas.csv` | Textos, notas, sentimento, escore e sinalizadores. |
| `dados/auditoria_idioma.csv` | Decisões de inclusão e exclusão pelo idioma. |
| `dados/resumo_produtos.csv` | Resultados agregados por produto. |
| `dados/matriz_estrelas.csv` | Comparação auxiliar entre classificação e estrelas. |
| `resultados/RELATORIO.md` | Relatório para leitura no GitHub. |
| `resultados/RELATORIO.html` | Relatório autossuficiente: baixe e abra no navegador. |
| `resultados/*.png` | Gráficos gerados pelo notebook. |
| `vendor/` | LeIA e léxicos, com licença e origem documentadas. |

As exportações são recriadas durante a execução. Preserve o snapshot entregue se realizar uma nova coleta.

## Acesso ao projeto

- **Repositório:** [CodePenguinsCorp/analise-sentimentos-ecommerce](https://github.com/CodePenguinsCorp/analise-sentimentos-ecommerce)
- **Notebook:** [Analise_Sentimentos_Ecommerce.ipynb](https://github.com/CodePenguinsCorp/analise-sentimentos-ecommerce/blob/main/Analise_Sentimentos_Ecommerce.ipynb)
- **Executar no Colab:** [Abrir o notebook](https://colab.research.google.com/github/CodePenguinsCorp/analise-sentimentos-ecommerce/blob/main/Analise_Sentimentos_Ecommerce.ipynb)
- **Relatório:** [Resultados e insights](resultados/RELATORIO.md)
- **Entrega completa:** [Baixar o ZIP do repositório](https://github.com/CodePenguinsCorp/analise-sentimentos-ecommerce/archive/refs/heads/main.zip)

O GitHub apresenta o notebook com as saídas salvas. O link do Colab permite abrir uma cópia para execução. Repositórios privados exigem acesso autorizado; o download automático no Colab usa o acesso público do GitHub.

## Referências

- **Thomann Portuguesa.** Avaliações de clientes dos produtos Superlux HD-681, Audio-Technica ATH-M50X e beyerdynamic DT-770 Pro 80 Ohm. URLs e datas específicas no [manifesto](dados/manifesto.json).
- **ALMEIDA, Rafael J. A.** LeIA — Léxico para Inferência Adaptada. 2018. [Repositório original](https://github.com/rafjaa/LeIA). Código e léxicos fixados em um commit, com licença MIT e adaptações documentadas em [vendor/ORIGEM.md](vendor/ORIGEM.md).
- **HUTTO, C. J.; GILBERT, E.** VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text. ICWSM, 2014.
- [BeautifulSoup — documentação](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) e [langdetect](https://pypi.org/project/langdetect/).
- Materiais de apoio da atividade: *Aula 05 — Data Scraping com BeautifulSoup*, Renato Vimieiro, 2017; e *Análise de sentimentos — Utilizando Python para construir e treinar modelos de machine learning*, Wheslley Rimar Bezerra.

Os comentários e as páginas continuam sujeitos aos direitos de seus autores e da fonte. A licença do LeIA não licencia as avaliações. Este estudo didático não tem vínculo com a loja ou os fabricantes.
