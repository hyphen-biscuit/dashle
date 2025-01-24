const guessForm = document.getElementById('guess-form');
const guessInput = document.getElementById('guess-input');
const attemptsContainer = document.getElementById('attemptsContainer');
const resetButton = document.getElementById('reset-button');
const popup = document.getElementById('popup');
const popupMessage = document.getElementById('popup-message');
const closePopupButton = document.getElementById('close-popup');
let currentRow = 0; // Track the current row
const maxCols = 7;  // Number of columns per row

function activateRow(rowIndex) {
    // Get the row and add inputs to each box if they don’t already exist
    const row = document.querySelectorAll('.attempt-row')[rowIndex];
    row.querySelectorAll('.letter-box').forEach((box, colIndex) => {
        if (!box.querySelector('input')) {
            const input = document.createElement('input');
            input.type = 'text';
            input.maxLength = 1;
            input.className = 'letter-input';
            input.style.width = '100%'; // Ensure it fills the box
            input.style.textAlign = 'center';

            box.appendChild(input);

            input.addEventListener('input', (e) => {
                if (e.target.value.length === 1 && colIndex < maxCols - 1) {
                    // Move to the next input in the row if there's a character
                    row.querySelectorAll('.letter-box')[colIndex + 1].querySelector('input').focus();
                }
            });

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace' && e.target.value === '' && colIndex > 0) {
                    // Move to the previous input in the row if the current one is empty
                    row.querySelectorAll('.letter-box')[colIndex - 1].querySelector('input').focus();
                } else if (e.key === 'Enter' && colIndex === maxCols - 1) {
                    // Submit the guess if "Enter" is pressed on the last input
                    submitGuess(row);
                    row.querySelectorAll('.letter-box')[rowIndex + 1].querySelector('input').focus();
                }
            });
        }
    });
}

function renderAttempts(attempts) {
    // Fill previous rows with guesses and feedback
    attempts.forEach((attempt, rowIndex) => {
        const row = document.querySelectorAll('.attempt-row')[rowIndex];
        row.querySelectorAll('.letter-box').forEach((box, colIndex) => {
            box.textContent = attempt.guess[colIndex];
            box.classList.add(attempt.feedback[colIndex]); // Apply color feedback classes
        });
    });
    // Activate the next empty row for the current guess
    activateRow(attempts.length);
}

function updateKeyboard(feedback) {
    // Feedback is an array of objects { letter: 'A', status: 'correct' | 'present' | 'absent' }
    feedback.forEach(({ letter, status }) => {
      const key = document.querySelector(`.key[data-key="${letter}"]`);
      if (key) {
        key.classList.remove('correct', 'present', 'absent');
        key.classList.add(status);
      }
    });
}

// Handle guess submission
function submitGuess(row) {
    const guess = Array.from(row.querySelectorAll('.letter-box input'))
        .map(input => input.value.toUpperCase())
        .join('');

    // Ensure all boxes have been filled with letters
    if (guess.length === maxCols) {
        fetch('/guess', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guess })
        })
        .then(response => response.json())
        .then(data => {
            renderAttempts(data.attempts);  // Refresh attempts
            if (data.game_over) {
                showPopup(data.game_over_message);  // Display win/lose message
            }
        })
        .catch(error => console.error('Error:', error));
    } else {
        alert("Please complete the word before submitting.");
    }
}

// Call activateRow with the first row as soon as the page loads
document.addEventListener('DOMContentLoaded', () => {
    activateRow(currentRow);

    // Fetch past guesses on load to fill in attempts and initialize the first row
    fetch('/get_attempts')
        .then(response => response.json())
        .then(data => {
            renderAttempts(data.attempts);
        });
});

// Hide the popup when "Close" button is clicked
closePopupButton.addEventListener('click', () => {
    popup.classList.add('hidden'); // Hide popup
});
function clearGrid() {
    const letterBoxes = document.querySelectorAll('.letter-box');

    letterBoxes.forEach(box => {
        box.textContent = '';      // Clear text content
        box.className = 'letter-box';  // Reset to only the base class, removing feedback classes
    }); 
}

// Update the reset button click handler
resetButton.addEventListener('click', async () => {
    await fetch('/reset', { method: 'POST' });
    clearGrid();  // Clear the grid visuals
    activateRow(0);  // Re-activate the first row for input
});

function showPopup(message) {
    popupMessage.textContent = message;
    popup.classList.remove('hidden');
}
