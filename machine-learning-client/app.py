from flask import Flask, request, jsonify

@app.route('/analyze', methods=['POST'])
def analyze():
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)