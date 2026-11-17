
import pickle
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "data" / "fake_job_postings.csv"
MODEL_PATH = BASE / "job_model.pkl"

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_PATH}"
    )

df = pd.read_csv(DATA_PATH)

# Remove duplicate job advertisements
df = df.drop_duplicates()

# Remove rows with missing or invalid labels
df = df[df["fraudulent"].isin([0, 1])]

print("Rows after removing duplicates:", len(df))
print("Missing values before text processing:")
print(df.isnull().sum())

if "fraudulent" not in df.columns:
    raise ValueError("Dataset must contain 'fraudulent' column.")

text_columns = [
    "title",
    "company_profile",
    "description",
    "requirements",
    "benefits",
    "employment_type",
    "required_experience",
    "required_education",
    "industry",
    "function",
    "location",
]

available = [c for c in text_columns if c in df.columns]

df["text"] = (
    df[available]
    .fillna("")
    .astype(str)
    .agg(" ".join, axis=1)
    .str.strip()
)

df = df[(df["text"] != "") & df["fraudulent"].isin([0, 1])]
X = df["text"]
y = df["fraudulent"].astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

model = Pipeline([
    ("tfidf", TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=100000,
        sublinear_tf=True
    )),
    ("classifier", LogisticRegression(
        max_iter=1000,
        class_weight="balanced"
    ))
])

model.fit(X_train, y_train)
predictions = model.predict(X_test)

print("\nUNSEEN TEST DATA RESULTS")
print("Training examples:", len(X_train))
print("Testing examples:", len(X_test))
print("\nClassification report:")
print(classification_report(
    y_test,
    predictions,
    labels=[0, 1],
    target_names=["Genuine", "Fake"],
    zero_division=0
))

print("Confusion matrix:")
print(confusion_matrix(y_test, predictions, labels=[0, 1]))

# After evaluation, train the final model on all labelled data.
model.fit(X, y)

with open(MODEL_PATH, "wb") as file:
    pickle.dump(model, file)

print("\nFinal model saved to:", MODEL_PATH)
print("Dataset rows used:", len(df))
print("Fake examples:", int((y == 1).sum()))
print("Genuine examples:", int((y == 0).sum()))
