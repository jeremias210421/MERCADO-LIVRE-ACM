from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "API funcionando"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
