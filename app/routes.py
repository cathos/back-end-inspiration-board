import requests
import os
from flask import Blueprint, request, jsonify, make_response, abort
from app import db
from app.models.board import Board
from app.models.card import Card
from sqlalchemy import exc

# # Helper Functions

def error_message(message, status_code):
    abort(make_response(jsonify(dict(details=message)), status_code))

def get_record_by_id(id, cls):
    '''
    cls is model name (Board or Card)
    '''
    try: 
        id = int(id)
    except ValueError:
        error_message(f"Invalid {cls.__name__.lower()} id {id}", 400)
    
    record = cls.query.get(id)

    if record:
        return record
    
    error_message(f"No {cls.__name__.lower()} with id {id} found", 404)

# # Boards Routes

boards_bp = Blueprint("boards_bp", __name__, url_prefix="/boards")

# # POST /boards
@boards_bp.route("", methods=["POST"])
def create_board():
    try:
        request_body = request.get_json()
        new_board = Board(
            title=request_body["title"], 
            owner=request_body["owner"]
            )

        db.session.add(new_board)
        db.session.commit()

        return make_response(jsonify({"board created!":new_board.title}), 201)

    except KeyError:
        error_message(f"Invalid data", 400)

# # GET /boards
@boards_bp.route("", methods=["GET"])
def read_all_boards():
    boards = Board.query.all()

    boards_response = []
    for board in boards:
        boards_response.append(board.to_dict())
    
    return make_response(jsonify(boards_response), 200)

# # GET /boards/<board_id>
@boards_bp.route("/<board_id>", methods=["GET"])
def get_single_board(board_id):
    board = get_record_by_id(board_id, Board)
    return jsonify({"board":board.to_dict()})

# # PUT /boards/<board_id>
@boards_bp.route("/<board_id>", methods=["PUT"])
def replace_board_by_id(board_id):
    request_body = request.get_json()
    board = get_record_by_id(board_id, Board)

    try: 
        board.title = request_body["title"]
        board.owner = request_body["owner"]
    except KeyError as error:
        error_message(f"Missing key: {error}", 400)

    db.session.commit()

    return jsonify({"board": board.to_dict()})    

# # DELETE /boards/<board_id>
@boards_bp.route("/<board_id>", methods=["DELETE"])
def delete_board_by_id(board_id):
    board = get_record_by_id(board_id, Board)
    board_dict = board.to_dict()
    for card in board.cards:
        delete_card_by_id(card.card_id)

    db.session.delete(board)
    db.session.commit()

    return jsonify({'details': f'Board {board_id} \'{board_dict["title"]}\' successfully deleted'})

# # Cards Routes

cards_bp = Blueprint("cards_bp", __name__, url_prefix="/cards")

# # POST /cards/<board_id>
@cards_bp.route("/<board_id>", methods=["POST"])
def create_card(board_id):
    try:
        request_body = request.get_json()
        new_card = Card(
            message=request_body["message"], 
            board_id=board_id,
            )

        db.session.add(new_card)
        db.session.commit()

        board = get_record_by_id(board_id, Board)

        token = os.environ.get("SLACK_TOKEN")
        payload = {"channel":"orange-purple", "text":f"New card \'{new_card.message}\' added to Inspiration Board \'{board.title}\'!"}
        header = {"Authorization":f"Bearer {token}"}
    
        requests.post("https://slack.com/api/chat.postMessage", params=payload, headers=header)

        return make_response(jsonify({"card created!":new_card.message}), 201)

    except KeyError:
        error_message(f"Invalid data", 400)

    except exc.DataError:
        error_message(f"Message exceeds 40 character limit", 400)

# # GET /cards/<board_id>
@cards_bp.route("/<board_id>", methods=["GET"])
def get_cards(board_id):
    cards = Card.query.filter(Card.board_id == board_id)
    cards_list = [card.to_dict() for card in cards]

    return jsonify(cards_list)

# # PATCH /cards/<card_id>/increase_likes_count
@cards_bp.route("/<card_id>/increase_likes_count", methods=["PATCH"])
def card_increase_likes_count(card_id):
    card = get_record_by_id(card_id, Card)
    card.likes_count += 1

    db.session.commit()
    
    return jsonify({'details': f'Card {card_id} \'{card.message}\' successfully liked'})

# # PATCH /cards/<card_id>/decrease_likes_count
@cards_bp.route("/<card_id>/decrease_likes_count", methods=["PATCH"])
def card_decrease_likes_count(card_id):
    card = get_record_by_id(card_id, Card)
    card.likes_count -= 1

    db.session.commit()
    
    return jsonify({'details': f'Card {card_id} \'{card.message}\' successfully unliked'})

# # DELETE /cards/<card_id>
@cards_bp.route("/<card_id>", methods=["DELETE"])
def delete_card_by_id(card_id):
    card = get_record_by_id(card_id, Card)
    card_dict = card.to_dict()

    db.session.delete(card)
    db.session.commit()

    return jsonify({'details': f'Card {card_id} \'{card_dict["message"]}\' successfully deleted'})
