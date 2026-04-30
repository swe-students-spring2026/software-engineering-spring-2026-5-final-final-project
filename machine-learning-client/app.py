from flask import Flask, request, jsonify
from service import analyze_assignment

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    result = analyze_assignment(
        title=data.get('title', ''),
        course=data.get('course', ''),
        description=data.get('description', ''),
        due_date=data.get('due_date', '')
    )
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
    