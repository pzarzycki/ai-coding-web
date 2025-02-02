import os
from flask import Flask, make_response, render_template

app = Flask(__name__)

@app.route('/')
def home():
    # we need Browser to get always most updated version - for development purposes
    response = make_response(render_template("index.html"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return render_template('index.html')

if __name__ == '__main__':
    print(os.curdir)
    app.run(debug=True, host='127.0.0.1', port=8090, reloader_type='auto', use_reloader=True, extra_files="templates/*")
