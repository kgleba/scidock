import spacy
from flask import Flask, abort, jsonify, request
from keybert import KeyBERT
from keybert.backend._onnx import ONNXBackend

app = Flask(__name__)

nlp = spacy.load('en_core_web_sm')
keybert = KeyBERT(
    model=ONNXBackend('all-MiniLM-L6-v2/model.onnx', 'all-MiniLM-L6-v2/tokenizer.json')
)


@app.route('/extract_names', methods=['POST'])
def extract_names():
    query = request.json.get('query')
    if query is None:
        abort(400)

    doc = nlp(query)
    names = filter(lambda entity: entity.label_ == 'PERSON', doc.ents)
    names = [entity.text for entity in names]

    return jsonify(names)


@app.route('/extract_keywords', methods=['POST'])
def extract_keywords():
    query = request.json.get('query')
    n_samples = request.json.get('n_samples', 5)

    if query is None:
        abort(400)

    keywords = keybert.extract_keywords(query, use_mmr=True, stop_words='english', top_n=n_samples)
    return jsonify([keyword[0] for keyword in keywords])


@app.route('/remove_stop_words', methods=['POST'])
def remove_stop_words():
    query = request.json.get('query')
    if query is None:
        abort(400)

    return jsonify(
        ' '.join(token.lemma_ for token in nlp(query) if not token.is_stop and not token.is_punct)
    )


@app.route('/edition', methods=['GET'])
def get_edition():
    return {'name': 'tiny', 'nlp_model': 'en_core_web_sm', 'keyword_model': 'all-MiniLM-L6-v2'}


if __name__ == '__main__':
    app.run('0.0.0.0', 7234)  # noqa: S104
