from flask import Flask, render_template, request, flash, url_for, redirect, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import os
import requests
from dotenv import load_dotenv, find_dotenv
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin

#########################################################################
#   APP AND DB SETUP/CONFIG
#########################################################################
load_dotenv(find_dotenv())
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.secret_key = os.getenv("SECRET_KEY")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
Session(app)


#########################################################################
#   DATABASE STUFF
#########################################################################
# creates a table of users
class Person(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    wins = db.Column(db.Integer, unique=False, nullable=False)

    def __repr__(self) -> str:
        return f"Person with username: {self.username} has {self.wins} wins."

    def __init__(self, username, wins):
        self.username = username
        self.wins = wins


# create tables
with app.app_context():
    db.create_all()

#########################################################################
#   GAME LOGIC/API INTEGRATION
#########################################################################

DECK_URL = "https://www.deckofcardsapi.com/api/deck"


# returns the deck id of a newly shuffled deck
def init_deck(deck_count=6):
    NEW_DECK_PATH = f"/new/shuffle/?deck_count={deck_count}"
    deck_response = requests.get(DECK_URL + NEW_DECK_PATH)
    return deck_response.json()['deck_id']


# draws a specified amount of cards from the deck
# with the deck id provided
def draw_card(deckId, draw=1):
    DRAW_CARDS_PATH = f"/{deckId}/draw/?count={draw}"
    draw_response = requests.get(DECK_URL + DRAW_CARDS_PATH)
    # returns a list containing the card(s) drawn
    return draw_response.json()['cards']


# returns all cards to the deck
def return_cards(deckId):
    RETURN_PATH = f"/{deckId}/return/"
    requests.get(DECK_URL + RETURN_PATH)


# creates a new game of blackjack
def init_game():
    # create new deck
    deck_id = init_deck()
    # initialize player and dealer hands
    player = draw_card(deck_id, 2)
    dealer = draw_card(deck_id, 2)
    return deck_id, player, dealer


# calculates total of a hand
def get_hand_total(hand):
    total = 0
    ace_check = False
    for card in hand:
        if card['value'] == 'KING' or card['value'] == 'QUEEN' or card['value'] == 'JACK':
            total += 10
        elif card['value'] == 'ACE':
            total += 11
            ace_check = True
        else:
            total += int(card['value'])
    if total > 21 and ace_check == True:
        total -= 10
    return total

# determines if the dealer should hit or stand
# depending on the score of their hand
def stand(hand):
    stand = True
    if get_hand_total(hand) <= 15:
        stand = False
    return stand


#########################################################################
#   FLASK STUFF
#########################################################################

# sets the current user
@login_manager.user_loader
def load_user(user_id):
    return Person.query.get(int(user_id))


# verifies if a user is valid or not
def validateUser(username):
    valid = db.session.query(Person.username).filter_by(username=username).scalar()
    return valid


# HOME PAGE
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


# LOGIN PAGE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.args.get("username"):
        username = request.args.get("username")
        if validateUser(username):
            user = Person.query.filter_by(username=username).first()
            login_user(user) 
            return redirect(url_for('index'))
        else:
            flash(f"User with username: {username} not found")
    return render_template('login.html')


# SIGNUP PAGE
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if not request.form['username']:
            flash("Please enter a unique username")
        else:
            username = request.form['username']
            if not validateUser(username):
                user = Person(username, 0)
                db.session.add(user)
                db.session.commit()
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash("That username is already in use. Please enter a new one.")
    return render_template("signup.html")


# LOGOUT FUNCTION
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# NEW GAME ROUTE
@app.route('/newgame')
@login_required
def newgame():
    session['deckId'], session['player'], session['dealer'] = init_game()
    return redirect(url_for('table'))

# GAME PAGE
@app.route('/table', methods=['GET', 'POST'])
@login_required
def table():

    deckId = session['deckId']
    player = session['player']
    dealer = session['dealer']
    gameover = False
    playerWins = False
    playerDraws = False

    if request.method == 'POST':
        if 'add' in request.form:
            player.append(draw_card(deckId)[0])
            session['player'] = player
            if not stand(dealer) and get_hand_total(player) <= 21:
                dealer.append(draw_card(deckId)[0])
                session['dealer'] = dealer
        if 'stay' in request.form:
            gameover = True

    playerTotal = get_hand_total(player)
    dealerTotal = get_hand_total(dealer)

    if (dealerTotal > 21 or playerTotal > 21) or gameover:
        gameover = True
        if playerTotal <= 21 and (playerTotal > dealerTotal or dealerTotal > 21):
            current_user.wins += 1
            db.session.commit()
            playerWins = True
        elif dealerTotal == playerTotal and playerTotal <= 21:
            playerDraws = True

    num_player_wins = current_user.wins

    return render_template('table.html',
                            deckId=deckId,
                            player=player,
                            dealer=dealer,
                            gameover=gameover,
                            playerWins=playerWins,
                            playerDraws=playerDraws,
                            num_player_wins=num_player_wins)


#app.run()