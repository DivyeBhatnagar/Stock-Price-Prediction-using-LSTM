import sys, json
import numpy as np
sys.path.insert(0, ".")
from data_pipeline import build_pipeline
from train import evaluate_model
from lstm_model import TemporalAttention   # registers custom layer
import tensorflow as tf

TICKER    = "RELIANCE.NS"
MODEL_DIR = "../backend/models/RELIANCE.NS"

pipeline = build_pipeline(
    ticker=TICKER,
    start_date="2016-03-12",
    window_size=60, forecast_horizon=1, split_ratio=0.85,
)

X_test           = pipeline["X_test"]
y_test           = pipeline["y_test"]
scaler           = pipeline["scaler"]
n_feat           = len(pipeline["feature_cols"])
test_prev_closes = pipeline.get("test_prev_closes")

model = tf.keras.models.load_model(
    f"{MODEL_DIR}/model.keras",
    custom_objects={"TemporalAttention": TemporalAttention},
    compile=False,
)
metrics = evaluate_model(model, X_test, y_test, scaler, n_feat, 1, test_prev_closes)
print(json.dumps(metrics, indent=2))
