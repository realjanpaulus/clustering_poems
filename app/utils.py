from html import unescape
from IPython.core.display import HTML
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re


from scipy.cluster.hierarchy import dendrogram
import seaborn as sns
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn import metrics
import spacy
from stop_words import get_stop_words
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator


# ================== #
# corpus processing  #
# ================== # 

def add_epoch_division(corpus, epochs, epoch_exceptions=[], add_years=0):
	""" Divide poems in DataFrame into epochs by dictionary.
		Epochs exceptions will be skipped.
		To add or reduce the end of an epoch, set 'add_years'.
	"""
	df = corpus.copy()
	epochs_d = {}
	
	for epoch, v in epochs.items():
		if epoch not in epoch_exceptions:
			epochs_d[epoch] = list(range(epochs[epoch]["b"], epochs[epoch]["e"] + add_years))
	
	df["epoch"] = df.apply(lambda row: get_epoch(row.year, epochs_d), axis=1)
	return df

def replace_poets(text):
	""" Unify poet spelling
	"""
	text = re.sub('Abschatz, Hans Assmann von', 'Abschatz, Hans Aßmann von', text)
	text = re.sub('Czepko, Daniel von', 'Czepko von Reigersfeld, Daniel', text)
	text = re.sub('Goethe, Johann Wolfgang', 'Goethe, Johann Wolfgang von', text)
	text = re.sub('Hoffmannswaldau, Christian Hoffmann von', 'Hofmann von Hofmannswaldau, Christian', text)
	text = re.sub('Hofmannswaldau, Christian Hofmann von', 'Hofmann von Hofmannswaldau, Christian', text)
	text = re.sub('Karsch, Anna Luise', 'Karsch, Anna Louisa', text)
	text = re.sub('Kosegarten, Gotthard Ludwig', 'Kosegarten, Ludwig Gotthard', text)
	text = re.sub('Stieler, Kaspar', 'Stieler, Kaspar von', text)
	text = re.sub('Zachariä, Justus Friedrich Wilhelm', 'Zachariae, Justus Friedrich Wilhelm', text)
	text = re.sub('Zinzendorf, Nicolaus Ludwig von', 'Zinzendorf, Nikolaus Ludwig von', text)
	
	return text

def merge_corpus_poets(corpus, min_count=6):
	""" Merge poems in corpus by poet. Epoch with the most entries will be chosen.
	"""
	
	# remove poets with less than min_count
	df = corpus.copy()
	poets = [k for k, v in dict(df.poet.value_counts()).items() if v >= min_count]
	df = df[df.poet.isin(poets)]
	df["poet"] = df.poet.apply(replace_poets)
	
	
	new_poems = {}
	

	# fill dictionary 'new_poems' with a summarized poem of all poems of a poet within 
	# an epoch, with the corresponding epoch, the mean of the publication years, 
	# the poets name and an id.
	# Skip poet with no name (N.N.)
	c = 0
	for poet in list(np.unique(df.poet)):
		if poet != "N. N.,":
			pcorpus = df[df.poet == poet]
			for e in pcorpus.epoch.unique():
				ecorpus = pcorpus[pcorpus.epoch == e]
				s = " ".join(ecorpus.poem)
				year = int(ecorpus.year.mean())
				new_poems[c] = [c, poet, s, year, e]
				c += 1
		

	mod_c = pd.DataFrame.from_dict(new_poems).T
	mod_c.columns = ["id", "poet", "poem", "year", "epoch"]

	return mod_c


def normalize_characters(text):
	""" The original code from Thomas Haider was copied and slightly modified,
		for the original code see:
		https://github.com/tnhaider/poetry-corpus-building/blob/master/extract_dta_poems.py
	"""
	text = re.sub('<[^>]*>', '', text)
	text = re.sub('ſ', 's', text)
	if text.startswith("b'"):
		text = text[2:-1]
	text = re.sub('&#223;', 'ß', text)
	text = re.sub('&#383;', 's', text)
	text = re.sub('u&#868;', 'ü', text)
	text = re.sub('a&#868;', 'ä', text)
	text = re.sub('o&#868;', 'ö', text)
	text = re.sub('&#246;', 'ö', text)
	text = re.sub('&#224;', 'a', text) # quam with agrave
	text = re.sub('&#772;', 'm', text) # Combining Macron in kom772t
	text = re.sub('&#8217;', "'", text)
	text = re.sub('&#42843;', "r", text) # small rotunda
	text = re.sub('&#244;', "o", text) # o with circumflex (ocr)
	text = re.sub('&#230;', "ae", text) 
	text = re.sub('&#8229;', '.', text) # Two Dot Leader ... used as 'lieber A.'
	text = re.sub('Jch', 'Ich', text)
	text = re.sub('Jst', 'Ist', text)
	text = re.sub('JCh', 'Ich', text)
	text = re.sub('jch', 'ich', text)
	text = re.sub('Jn', 'In', text)
	text = re.sub('Bey', 'Bei', text)
	text = re.sub('bey', 'bei', text)
	text = re.sub('seyn', 'sein', text)
	text = re.sub('Seyn', 'Sein', text)
	text = re.sub('kan', 'kann', text)
	text = re.sub('kannn', 'kann', text)
	text = re.sub('Kannn', 'kann', text)
	text = re.sub('Kan', 'Kann', text)
	text = re.sub('DJe', 'Die', text)
	text = re.sub('Wje', 'Wie', text)
	text = re.sub('¬', '-', text) # negation sign
	text = re.sub('Jn', 'In', text)
	text = text.encode("utf-8", 'replace')
	#text = text.decode("utf-8", 'replace')
	text = re.sub(b'o\xcd\xa4', b'\xc3\xb6', text) # ö
	text = re.sub(b'u\xcd\xa4', b'\xc3\xbc', text) # ü
	text = re.sub(b'a\xcd\xa4', b'\xc3\xa4', text) # ä
	text = re.sub(b'&#771;', b'\xcc\x83', text) # Tilde
	text = re.sub(b'&#8222;', b'\xe2\x80\x9d', text) # Lower Quot Mark
	text = re.sub(b'\xea\x9d\x9b', b'r', text) # small Rotunda
	text = re.sub(b'\xea\x9d\x9a', b'R', text) # big Rotunda
	text = text.decode('utf-8')
	ftl = text[:2] # check if first two letters are capitalized
	try:
		if ftl == ftl[:2].upper():
			text = ftl[0] + ftl[1].lower() + text[2:]
	except IndexError:
		pass
	return text


def text_cleaning(corpus):
	""" Applies character normalization to the corpus. 
	"""
	df = corpus.copy()
	df["poem"] = df.poem.apply(unescape)

	def remove_b(s):
		regex = re.compile("b'(.*?)'")
		return re.sub(regex, r"\1", s)

	df["poem"] = df["poem"].apply(remove_b)
	df["poem"] = df["poem"].apply(normalize_characters)

	return df



def random_downsampling(corpus, 
						class_col = "epoch", 
						max_value = 1000):
	""" Reduces all instances of all classes to a certain maximum value.
	"""   

	classes = list(corpus.epoch.unique())
	
	if len(classes) >= 2:
		corpus_1 = corpus[corpus[class_col] == classes[0]]
		corpus_2 = corpus[corpus[class_col] == classes[1]]
		corpus_1 = corpus_1.sample(max_value)
		corpus_2 = corpus_2.sample(max_value)
		return pd.concat([corpus_1, corpus_2], axis=0)

	elif len(classes) == 3:

		corpus_1 = corpus[corpus[class_col] == classes[0]]
		corpus_2 = corpus[corpus[class_col] == classes[1]]
		corpus_3 = corpus[corpus[class_col] == classes[2]]
		corpus_1 = corpus_1.sample(max_value)
		corpus_2 = corpus_2.sample(max_value)
		corpus_3 = corpus_3.sample(max_value)

		return pd.concat([corpus_1, corpus_2, corpus_3], axis=0)

	elif len(classes) == 4:

		corpus_1 = corpus[corpus[class_col] == classes[0]]
		corpus_2 = corpus[corpus[class_col] == classes[1]]
		corpus_3 = corpus[corpus[class_col] == classes[2]]
		corpus_4 = corpus[corpus[class_col] == classes[3]]
		corpus_1 = corpus_1.sample(max_value)
		corpus_2 = corpus_2.sample(max_value)
		corpus_3 = corpus_3.sample(max_value)
		corpus_4 = corpus_4.sample(max_value)

		return pd.concat([corpus_1, corpus_2, corpus_3, corpus_4], axis=0)

	else:
		print(f"Class count of {len(classes)} is too high, no downsampling was performed.")
		return corpus


# ==========
# clustering
# ==========

def generate_wordcloud(top_words, pos_remove=False, img_name = ""):
	plt.rcParams['figure.dpi']= 300

	# Create and generate a word cloud image:
	wordcloud = WordCloud(width=600,
						  height=300,
						  background_color="white").generate_from_frequencies(top_words)

	# Display the generated image:
	plt.figure(figsize=(8,8))
	plt.imshow(wordcloud, interpolation='bilinear')
	#plt.tight_layout(pad=0)
	plt.axis("off")
	
	if pos_remove:
		plt.savefig(f"../results/figures/wc{img_name}_top_n_words_pos_remove")
	else:
		plt.savefig(f"../results/figures/wc{img_name}_top_n_words")
	plt.show()

def get_epoch(year, epochs):
	epoch = ""
	for k, v in epochs.items():
		if year in v:
			epoch = k
			break
	return epoch

def get_json_dict(filename):
   with open(filename) as f_in:
	   return(json.load(f_in))

def linkage_matrix(model):
	counts = np.zeros(model.children_.shape[0])
	n_samples = len(model.labels_)
	for i, merge in enumerate(model.children_):
		current_count = 0
		for child_idx in merge:
			if child_idx < n_samples:
				current_count += 1  # leaf node
			else:
				current_count += counts[child_idx - n_samples]
		counts[i] = current_count

	return np.column_stack([model.children_, 
							model.distances_,
							counts]).astype(float)

def plot_dendrogram(model, **kwargs):
	# Create linkage matrix and then plot the dendrogram

	# create the counts of samples under each node
	lm = linkage_matrix(model)

	# Plot the corresponding dendrogram
	dendrogram(lm, **kwargs)

def purity_score(y_true, y_pred):
	# compute contingency matrix (also called confusion matrix)
	contingency_matrix = metrics.cluster.contingency_matrix(y_true, y_pred)
	return np.sum(np.amax(contingency_matrix, axis=0)) / np.sum(contingency_matrix)


def get_top_n_words(column, n = None, stopwords = "", pos_remove = False):
	""" Get the top n words of a text column.
	"""
	texts = list(column)
	if pos_remove:
		texts = remove_pos(texts)
	
	vectorizer = TfidfVectorizer(max_features=None, stop_words=stopwords)
	vector = vectorizer.fit_transform(texts)
	sum_words = vector.sum(axis=0) 
	words_freq = [(word, sum_words[0, idx]) for word, idx in vectorizer.vocabulary_.items()]
	words_freq = sorted(words_freq, key = lambda x: x[1], reverse=True)
	return words_freq[:n]


def remove_noise_poet(corpus, noise_pids, min_n=50):
	""" Removes noisy poets from corpus.
	"""
	df = corpus.copy()
	noise_df = corpus[corpus.pid.isin(noise_pids)]
	noise_poets = dict(noise_df.poet.value_counts())
	poets = [k for k, v in noise_poets.items() if v >= min_n]
	df = df[df.poet.isin(poets) == False]
	return df

def remove_pos(lst, used_pos = ["VERB", "ADJ", "NOUN"]):
	""" Remove every part of speach except the specified exceptions.
	"""
	nlp = spacy.load('de')
	new_lst = []
	for s in lst:
		posstr = nlp(s)
		new_string = ""
		for token in posstr:  
			if token.pos_ in used_pos:
				new_string = new_string + token.text + " "
		new_lst.append(new_string)
		
	return new_lst
	

def wordcloud_epochs(df, epochs, n = 100, pos_remove = False):
	
	top_words_dict = {}
	
	for k, v in epochs.items():
		print(k)
		corpus = df[(df.year >= v[0]) & (df.year <= v[1])]
		stopwords = get_stop_words("de")
		top_words = dict(get_top_n_words(corpus["poem"], n=n, stopwords=stopwords, pos_remove = pos_remove))
		top_words_dict[k] = top_words
		generate_wordcloud(top_words, pos_remove, img_name = k)
		
	return top_words_dict


# =====
# others
# =====


def clear_json(jsonpath):
	""" Clears an json file.
	"""
	with open(jsonpath, "w+") as f:
		json.dump({}, f)


def hide_code():
	"""Hide jupyter notebook code cells."""
	toggle_code_str = """
	<form action="javascript:code_toggle()"><input type="submit" id="toggleButton" value="Show/Hide Code Cell"></form>
	"""

	toggle_code_prepare_str = """
	<script>
	function code_toggle() {
		if ($('div.cell.code_cell.rendered.selected div.input').css('display')!='none'){
			$('div.cell.code_cell.rendered.selected div.input').hide();
		} else {
			$('div.cell.code_cell.rendered.selected div.input').show();
		}
	}
	</script>"""
	display(HTML(toggle_code_prepare_str + toggle_code_str))