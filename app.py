from flask import Flask, render_template, redirect, request

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_new_task', methods=['POST'])
def submit_new_task():
    form_data = request.json
    return redirect('/')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)