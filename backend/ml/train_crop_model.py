import pandas as pd
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "crop_recommendation.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "crop_rf.pkl")
LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")

def train_model():
    print("Loading data...")
    if not os.path.exists(DATA_PATH):
        print(f"Error: Data file not found at {DATA_PATH}")
        return

    df = pd.read_csv(DATA_PATH)

    # Drop N, P, K as requested
    df = df.drop(columns=['N', 'P', 'K'])
    
    # Features and Target
    # Remaining columns should be: temperature, humidity, ph, rainfall, label
    X = df[['temperature', 'humidity', 'rainfall', 'ph']]
    y = df['label']

    print(f"Features used: {list(X.columns)}")

    # Encode labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

    # Train model
    print("Training RandomForestClassifier (n_estimators=200)...")
    rf = RandomForestClassifier(n_estimators=200, random_state=42)
    rf.fit(X_train, y_train)

    # Evaluate
    y_pred = rf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"✅ Model Accuracy: {acc * 100:.2f}%")

    # Ensure model directory exists
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)

    # Save model and label encoder
    print(f"Saving model to {MODEL_PATH}...")
    joblib.dump(rf, MODEL_PATH)
    
    # Also save the label encoder so we can decode predictions later
    joblib.dump(le, LABEL_ENCODER_PATH)
    print(f"Saving label encoder to {LABEL_ENCODER_PATH}...")
    
    print("Done!")

if __name__ == "__main__":
    train_model()
