import logging
import os

from app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=debug, use_reloader=debug)
