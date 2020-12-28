from main import app

import os

if __name__ == "__main__":
    app.debug = True
    # TODO: remove debug
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['SERVER_NAME'] = "localhost:5000"
    app.run(host='0.0.0.0', port=os.environ["PORT"], debug=True)
    #app.run(debug=True)
