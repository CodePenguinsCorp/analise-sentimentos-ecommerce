"""Verificação mínima do extrator e da classificação, sem acessar a rede."""
from analise import extrair_avaliacoes, classificar, identificar_idioma

html = '''<h1>Fone teste</h1><div class="js-review" data-rating-id="123">
<span class="js-headline-original">Excelente!</span>
<div class="js-text-original" lang="pt">Som bom.<br>Não é ruim!</div>
<div class="js-text-translated">Texto traduzido duplicado</div>
<div class="review-intro"><div class="fx-rating-stars__filler" style="width: 80%"></div></div>
<span class="review-intro__author">Pessoa 01.02.2025</span></div>'''
rows = extrair_avaliacoes(html, 'https://example.org/fone', '2026-11-03T12:00:00-03:00')
assert len(rows) == 1
assert rows[0]['comentario'] == 'Som bom. Não é ruim!'
assert rows[0]['nota'] == 4
assert rows[0]['data_avaliacao'] == '2025-02-01'
assert classificar('Adorei estes fones, som excelente!')['sentimento'] == 'Positivo'
assert classificar('Produto péssimo, horrível e ruim.')['sentimento'] == 'Negativo'
assert classificar('O som não é bom.')['sentimento'] == 'Negativo'
assert classificar('O som é bom.')['sentimento'] == 'Positivo'
assert classificar('O som não é ruim.')['sentimento'] == 'Positivo'
assert classificar('Não recomendo, produto péssimo.')['sentimento'] == 'Negativo'
assert rows[0]['idioma'] == 'pt'
assert identificar_idioma('Este produto tem excelente qualidade de som e gostei muito da compra.')['idioma_detectado'] == 'pt'
assert identificar_idioma('These headphones are very comfortable and the sound quality is excellent.')['idioma_detectado'] == 'en'
assert classificar('Auscultadores.')['baixa_polaridade']
print('OK: extração, nota, data, texto original, negação e baixa polaridade.')
