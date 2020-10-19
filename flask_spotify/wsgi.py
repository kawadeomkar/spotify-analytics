from app import app 

import os

if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0', port=os.environ["PORT"])
