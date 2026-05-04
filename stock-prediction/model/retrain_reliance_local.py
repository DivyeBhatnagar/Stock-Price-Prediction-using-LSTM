import os
import json
import time
import joblib
import numpy as np
from sklearn.preprocessing import MinMaxScaler

from data_pipeline import (
    load_raw_data,
    add_technical_indicators,
    FEATURE_COLS,
    normalize_ticker,
    create_sequences,
    split_data,
    inverse_transform_close,
    LOG_RETURN_COL_IDX,
)
from lstm_model import build_lstm_model, get_callbacks, save_model
from train import evaluate_model, _plot_training_history, _plot_predictions


def main():
    ticker = normalize_ticker("RELIANCE.NS")
    root = os.path.abspath("..")
    model_dir = os.path.join(root, "backend", "models")
    ticker_dir = os.path.join(model_dir, ticker)
    os.makedirs(ticker_dir, exist_ok=True)

    scaler_path = os.path.join(ticker_dir, "scaler.pkl")
    model_path = os.path.join(ticker_dir, "model.keras")
    config_path = os.path.join(ticker_dir, "config.json")
    ckpt_path = os.path.join(ticker_dir, "checkpoint.keras")

    start_time = time.time()
    print(f"Training direct-from-cache: {ticker}")

    df_raw = load_raw_data(ticker, data_dir=os.path.join(root, "data", "stocks"))
    df_feat = add_technical_indicators(df_raw)

    split_ratio = 0.80
    window = 60
    horizon = 1

    data = df_feat[FEATURE_COLS].values
    n_train = int(len(data) * split_ratio)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(data[:n_train])
    joblib.dump(scaler, scaler_path)
    scaled = scaler.transform(data)

    X, y = create_sequences(scaled, window, LOG_RETURN_COL_IDX, horizon)
    X_train, X_test, y_train, y_test = split_data(X, y, split_ratio)

    y_train_lr = inverse_transform_close(scaler, y_train, LOG_RETURN_COL_IDX, len(FEATURE_COLS)).reshape(-1, 1)
    y_test_lr = inverse_transform_close(scaler, y_test, LOG_RETURN_COL_IDX, len(FEATURE_COLS)).reshape(-1, 1)
    y_train_dir = (y_train_lr > 0).astype(np.float32)
    y_test_dir = (y_test_lr > 0).astype(np.float32)

    n_features = X_train.shape[2]
    model = build_lstm_model(
        window_size=window,
        n_features=n_features,
        forecast_horizon=horizon,
        lstm_units=(256, 128, 64),
        dropout_rate=0.15,
        learning_rate=1e-3,
        use_attention=True,
        use_bidirectional=True,
        use_multi_task=True,
    )

    callbacks = get_callbacks(ckpt_path, patience=25)
    history = model.fit(
        X_train,
        {"price_output": y_train, "direction_output": y_train_dir},
        validation_data=(X_test, {"price_output": y_test, "direction_output": y_test_dir}),
        epochs=50,
        batch_size=32,
        callbacks=callbacks,
        verbose=1,
        shuffle=False,
    )

    train_time = time.time() - start_time
    n_train_seqs = len(X_train)
    test_prev_closes = df_feat["Close"].values[
        n_train_seqs + window - 1 : n_train_seqs + window - 1 + len(X_test)
    ]

    metrics = evaluate_model(
        model,
        X_test,
        y_test,
        scaler,
        n_features,
        horizon,
        test_prev_closes,
        y_test_dir,
    )
    print("\nFinal metrics:")
    print(json.dumps(metrics, indent=2))

    config = {
        "ticker": ticker,
        "window_size": window,
        "forecast_horizon": horizon,
        "n_features": n_features,
        "feature_cols": FEATURE_COLS,
        "split_ratio": split_ratio,
        "multi_task": True,
        "epochs_trained": len(history.history["loss"]),
        "metrics": metrics,
        "train_time_sec": round(train_time, 1),
        "model_path": model_path,
        "scaler_path": scaler_path,
    }

    save_model(model, model_path)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    _plot_training_history(history, ticker_dir, ticker)
    _plot_predictions(model, X_test, y_test, scaler, df_feat, n_features, horizon, ticker, ticker_dir, test_prev_closes)

    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
