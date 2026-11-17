
import pickle
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODEL_PATH = BASE / "job_model.pkl"

with open(MODEL_PATH, "rb") as file:
    model = pickle.load(file)

tests = [
    (
        "Test 1 - Registration fee",
        "Pay a registration fee to get this internship. "
        "Guaranteed selection today."
    ),
    (
        "Test 2 - Genuine-style internship",
        "ABC Technologies is hiring Python interns. "
        "Students will work on real software projects. "
        "Apply through our official careers website."
    ),
    (
        "Test 3 - Task recharge",
        "Earn daily by completing online tasks. "
        "Recharge your account to unlock more tasks "
        "and withdraw your earnings."
    ),
    (
        "Test 4 - Suspicious OTP request",
        "You are selected for a remote job. "
        "Send your bank PIN and OTP to verify your account."
    ),
    (
        "Test 5 - Software developer vacancy",
        "We are hiring a software developer. "
        "Required skills include Python, SQL and Git. "
        "The selected candidate will attend an interview."
    ),
]

for name, text in tests:
    prediction = int(model.predict([text])[0])
    probabilities = model.predict_proba([text])[0]
    classes = list(model.classes_)
    fake_index = classes.index(1)
    fake_probability = probabilities[fake_index] * 100

    print("\n" + name)
    print("Prediction:", "Fake" if prediction == 1 else "Genuine")
    print(f"Estimated fake probability: {fake_probability:.2f}%")
