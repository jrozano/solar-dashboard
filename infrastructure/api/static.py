from flask import Blueprint, current_app

frontend_bp = Blueprint('frontend', __name__)


@frontend_bp.route('/')
def index():
    # serve the app-level static `index.html` configured in the app factory
    return current_app.send_static_file('index.html')
