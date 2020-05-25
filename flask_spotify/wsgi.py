from app import app 

import os

if __name__ == "__main__":
    app.debug = True
    app.run(host='127.0.0.1', port=os.environ["PORT"])
