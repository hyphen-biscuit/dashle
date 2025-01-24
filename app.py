from flask import Flask, render_template, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone

import requests
import random
import os
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Define the absolute path for the database file
database_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database/words.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'

db = SQLAlchemy(app)

ENDPOINT = 'https://api.datamuse.com/words'

class Word(db.Model):
    __tablename__ = 'words'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(7), nullable=False)
    frequency = db.Column(db.Float, nullable=True)

class UpdateTracker(db.Model):
    __tablename__ = 'update_tracker'
    id = db.Column(db.Integer, primary_key=True)
    last_updated = db.Column(db.DateTime, nullable=False)

import requests
import re
import string

ENDPOINT = 'https://api.datamuse.com/words'

def get_seven_letter_words(max_results=100000):
    all_words = []  # List to store all words with their frequency

    print(f"Beginning pagination, expect {.00163*max_results} second delay")

    # Iterate over every possible two-letter prefix (aa, ab, ac, ..., zz)
    for first_letter in string.ascii_lowercase:
        for second_letter in string.ascii_lowercase:
            pattern = f'{first_letter}{second_letter}?????'  # 7-letter pattern with first 2 letters fixed
            
            params = {
                'sp': pattern,  # Pattern for 7-letter words starting with first two letters
                'md': 'f',  # Request frequency data
                'max': 1000  # Maximum number of words per request
            }

            response = requests.get(ENDPOINT, params=params)

            if response.status_code == 200:
                data = response.json()

                # Filter words and frequency data
                for word_info in data:
                    word = word_info.get('word')
                    if re.match("^[a-zA-Z]+$", word):  # Ensure word is alphabetical
                        frequency = next(
                            (float(tag.split(":")[1]) for tag in word_info.get('tags', []) if tag.startswith('f:')),
                            None  # Use None if no frequency data is available
                        )
                        if frequency is not None:  # Only keep words with frequency data
                            all_words.append((word.upper(), frequency))

                # Stop once we've gathered enough words
                if len(all_words) >= max_results:
                    break

            else:
                print(f"Error: {response.status_code} for pattern {pattern}")
                break  # Stop if there's an error

        if len(all_words) >= max_results:
            break  # Stop iterating over the letter combinations once we have enough words

    # Sort the list of words by frequency in descending order
    all_words.sort(key=lambda x: x[1], reverse=True)

    # Return only the top words up to max_results
    return all_words[:max_results]


def update_words_if_needed():
    """Fetches 7-letter words and updates the database if the last update was over 24 hours ago."""
    tracker = UpdateTracker.query.first()
    now = datetime.now(timezone.utc)

    if tracker:
        last_update = datetime.fromisoformat(str(tracker.last_updated)).replace(tzinfo=timezone.utc)
        if now - last_update < timedelta(days=1):
            print("Words database was updated less than 24 hours ago. Skipping update.")
            return  # Skip update if less than 24 hours have passed
    else:
        # If no tracker exists, create one
        tracker = UpdateTracker(last_updated=now)
        db.session.add(tracker)
        db.session.commit()

    # Fetch new words and update the database
    words_with_frequency = get_seven_letter_words()
    if words_with_frequency:
        # Clear old words
        Word.query.delete()
        
        # Add new words to the database with frequency
        for word, frequency in words_with_frequency:
            db.session.add(Word(word=word.upper(), frequency=float(frequency)))

        # Update tracker timestamp
        tracker.last_updated = now
        db.session.commit()
        print(f"Database updated with {len(words_with_frequency)} 7-letter words.")
    else:
        print("No words retrieved, skipping database update.")

# Helper function to pick a random word within the top 2500 most frequent words
def get_random_word():
    # Retrieve the top 2500 words ordered by frequency in descending order
    top_words = Word.query.order_by(Word.frequency.desc()).limit(2500).all()
    
    # Randomly choose one word from this list
    if top_words:
        word = random.choice(top_words).word
        return word.upper()
    else:
        print("No words available in the database.")
        return None

@app.route('/')
def index():
    if 'target_word' not in session:
        session['target_word'] = get_random_word()
        session['guesses'] = []
    return render_template('index.html', guesses=session['guesses'])

@app.route('/get_attempts', methods=['GET'])
def get_attempts():
    # Return guesses and feedback stored in the session
    attempts = session.get('guesses', [])
    return jsonify({'attempts': attempts})

@app.route('/guess', methods=['POST'])
def guess():
    guess = request.json.get('guess', '').upper()

    # Initialize guesses in session if not present
    if 'guesses' not in session:
        session['guesses'] = []
    
    target_word = session.get('target_word', '')

    # Ensure guess length is 7 characters
    if len(guess) != 7:
        return jsonify({'error': 'Guess must be 7 letters long'}), 400

    feedback = ['gray'] * 7  # Initialize feedback with 'gray' for each letter

    # Track letters in target word that have already been matched
    target_letter_counts = {}
    for letter in target_word:
        target_letter_counts[letter] = target_letter_counts.get(letter, 0) + 1

    # First pass: Check for correct positions (green)
    for i in range(7):
        if guess[i] == target_word[i]:
            feedback[i] = 'green'
            target_letter_counts[guess[i]] -= 1  # Reduce count since we used this letter

    # Second pass: Check for incorrect positions (yellow)
    for i in range(7):
        if feedback[i] == 'gray' and guess[i] in target_letter_counts and target_letter_counts[guess[i]] > 0:
            feedback[i] = 'yellow'
            target_letter_counts[guess[i]] -= 1  # Reduce count for matched letters

    # Check if the guess matches the target word
    game_over = False
    win = False
    # Add the guess to the session
    session['guesses'].append({'guess': guess, 'feedback': feedback})
    session.modified = True  # Ensure the session update is saved
    if guess == target_word:
        game_over = True
        win = True
    else:
        
        # Check if the number of attempts has reached 9
        if len(session['guesses']) >= 9:
            game_over = True  # Game over due to too many attempts

    return jsonify({
        'attempts': session['guesses'],
        'game_over': game_over,
        'win': win
    })

@app.route('/reset', methods=['POST'])
def reset():
    session.pop('target_word', None)
    session['target_word'] = get_random_word()
    session['guesses'] = []
    return jsonify({'message': 'Game reset successfully'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Initialize tables
        update_words_if_needed()  # Perform initial update on start
    app.run(debug=True)