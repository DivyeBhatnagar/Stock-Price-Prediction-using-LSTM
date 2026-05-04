"""
lstm_model.py
=============
Defines the LSTM architecture for stock price forecasting.

Architecture
------------
Input  → LSTM(128) → Dropout(0.2)
       → LSTM(64)  → Dropout(0.2)
       → Dense(32) → Dense(horizon)

Optional: Attention mechanism over LSTM outputs.

Author  : Stock-Prediction AI Pipeline
Version : 1.0.0
"""

import numpy as np
import tensorflow as tf
from tensorflow.keras import Model, Input
from tensorflow.keras.layers import (
    LSTM, Dense, Dropout, BatchNormalization,
    Bidirectional, MultiHeadAttention, LayerNormalization,
    GlobalAveragePooling1D, Reshape, Multiply, Permute,
    Flatten, Lambda, Attention, Conv1D, MaxPooling1D
)
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import (
    EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
)
from tensorflow.keras.regularizers import l2
import tensorflow.keras.backend as K
from typing import Tuple, Optional
import os


def _binary_focal_loss(alpha: float = 0.6, gamma: float = 2.0):
    """
    Binary focal loss to address class imbalance and focus on hard examples.
    """
    def loss(y_true, y_pred):
        y_true = tf.cast(y_true, tf.float32)
        y_pred = tf.clip_by_value(y_pred, K.epsilon(), 1.0 - K.epsilon())
        p_t = y_true * y_pred + (1.0 - y_true) * (1.0 - y_pred)
        alpha_factor = y_true * alpha + (1.0 - y_true) * (1.0 - alpha)
        modulating_factor = tf.pow(1.0 - p_t, gamma)
        return tf.reduce_mean(-alpha_factor * modulating_factor * tf.math.log(p_t))

    return loss


# ─────────────────────────────────────────────
# HELPER: Custom Attention Layer
# ─────────────────────────────────────────────

class TemporalAttention(tf.keras.layers.Layer):
    """
    Self-attention mechanism that weighs each time-step of the LSTM output.
    Helps the model focus on the most informative past time-steps.
    """

    def __init__(self, units: int, **kwargs):
        super().__init__(**kwargs)
        self.units = units
        self.W = Dense(units, use_bias=False)
        self.V = Dense(1, use_bias=False)

    def call(self, encoder_output):
        # encoder_output: (batch, time, features)
        score = tf.nn.tanh(self.W(encoder_output))  # (batch, time, units)
        attention_weights = tf.nn.softmax(self.V(score), axis=1)  # (batch, time, 1)
        context = attention_weights * encoder_output              # (batch, time, features)
        context = tf.reduce_sum(context, axis=1)                  # (batch, features)
        return context, tf.squeeze(attention_weights, axis=-1)

    def get_config(self):
        config = super().get_config()
        config.update({"units": self.units})
        return config


# ─────────────────────────────────────────────
# MODEL FACTORY
# ─────────────────────────────────────────────

def build_lstm_model(
    window_size: int,
    n_features: int,
    forecast_horizon: int = 1,
    lstm_units: Tuple[int, ...] = (256, 128, 64),
    dropout_rate: float = 0.2,
    learning_rate: float = 1e-3,
    use_attention: bool = True,
    use_bidirectional: bool = False,
    use_multi_task: bool = True,
    output_mode: Optional[str] = None,
    use_cnn: bool = False,
    cnn_filters: Tuple[int, ...] = (64, 32),
    cnn_kernel_size: int = 3,
) -> Model:
    """
    Build and compile the LSTM model.

    Parameters
    ----------
    window_size       : Number of past time-steps (look-back)
    n_features        : Number of input features per time-step
    forecast_horizon  : Number of future days to predict
    lstm_units        : Tuple defining units in each LSTM layer
    dropout_rate      : Fraction of neurons to drop
    learning_rate     : Adam optimiser learning rate
    use_attention     : Whether to apply temporal attention
    use_bidirectional : Wrap LSTM in Bidirectional wrapper

    Returns
    -------
    Compiled Keras Model
    """
    inputs = Input(shape=(window_size, n_features), name="price_input")
    x = inputs

    # ── Optional CNN Front-End ────────────────
    if use_cnn:
        for i, filters in enumerate(cnn_filters):
            x = Conv1D(filters, kernel_size=cnn_kernel_size, activation="relu", padding="same",
                       name=f"conv1d_{i+1}")(x)
            x = BatchNormalization(name=f"conv_bn_{i+1}")(x)
            x = MaxPooling1D(pool_size=2, name=f"conv_pool_{i+1}")(x)
            x = Dropout(dropout_rate / 2, name=f"conv_dropout_{i+1}")(x)

    # ── LSTM Stack ────────────────────────────
    for i, units in enumerate(lstm_units):
        is_last_lstm = (i == len(lstm_units) - 1)
        # If we use attention, the last LSTM must return sequences
        return_seq = (not is_last_lstm) or use_attention

        lstm_layer = LSTM(
            units,
            return_sequences=return_seq,
            kernel_regularizer=l2(1e-4),
            recurrent_regularizer=l2(1e-4),
            name=f"lstm_{i+1}"
        )

        if use_bidirectional:
            x = Bidirectional(lstm_layer, name=f"bilstm_{i+1}")(x)
        else:
            x = lstm_layer(x)

        x = BatchNormalization(name=f"bn_{i+1}")(x)
        x = Dropout(dropout_rate, name=f"dropout_{i+1}")(x)

    # ── Temporal Attention ────────────────────
    if use_attention:
        # Custom attention over the last LSTM sequence
        attention_layer = TemporalAttention(units=lstm_units[-1], name="temporal_attention")
        x, _ = attention_layer(x)          # x: (batch, features)
    # If no attention and last LSTM is not returning sequences, x is already (batch, features)

    # ── Fully-Connected Head ──────────────────
    x = Dense(128, activation="relu", kernel_regularizer=l2(1e-4), name="dense_1")(x)
    x = Dropout(dropout_rate / 2, name="dropout_head")(x)
    x = Dense(64, activation="relu", kernel_regularizer=l2(1e-4), name="dense_2")(x)
    x = Dropout(dropout_rate / 4, name="dropout_head2")(x)

    if output_mode is None:
        output_mode = "multi" if use_multi_task else "regression"

    if output_mode == "direction":
        direction_output = Dense(1, activation="sigmoid", name="direction_output")(x)
        outputs = direction_output
    else:
        # Output: predict `forecast_horizon` scaled Close prices
        price_output = Dense(forecast_horizon, activation="linear", name="price_output")(x)
        if output_mode == "multi":
            direction_output = Dense(1, activation="sigmoid", name="direction_output")(x)
            outputs = [price_output, direction_output]
        else:
            outputs = price_output

    model = Model(inputs, outputs, name="StockLSTM")

    # ── Compile ───────────────────────────────
    if output_mode == "multi":
        model.compile(
            optimizer=Adam(learning_rate=learning_rate, clipnorm=1.0),
            loss={
                "price_output": "huber",
                "direction_output": _binary_focal_loss(alpha=0.6, gamma=2.0),
            },
            loss_weights={
                "price_output": 1.0,
                "direction_output": 0.7,
            },
            metrics={
                "price_output": ["mae"],
                "direction_output": [
                    "accuracy",
                    tf.keras.metrics.AUC(name="auc"),
                    tf.keras.metrics.Precision(name="precision"),
                    tf.keras.metrics.Recall(name="recall"),
                ],
            },
        )
    elif output_mode == "direction":
        model.compile(
            optimizer=Adam(learning_rate=learning_rate, clipnorm=1.0),
            loss=_binary_focal_loss(alpha=0.6, gamma=2.0),
            metrics=[
                "accuracy",
                tf.keras.metrics.AUC(name="auc"),
                tf.keras.metrics.Precision(name="precision"),
                tf.keras.metrics.Recall(name="recall"),
            ],
        )
    else:
        model.compile(
            optimizer=Adam(learning_rate=learning_rate, clipnorm=1.0),
            loss="huber",           # Huber loss is robust to outliers
            metrics=["mae"]
        )

    model.summary()
    return model


def build_simple_lstm(
    window_size: int,
    n_features: int,
    forecast_horizon: int = 1,
) -> Model:
    """
    Lightweight single-LSTM baseline for quick benchmarking.
    """
    inputs = Input(shape=(window_size, n_features))
    x = LSTM(64, return_sequences=False)(inputs)
    x = Dropout(0.2)(x)
    outputs = Dense(forecast_horizon, activation="linear")(x)

    model = Model(inputs, outputs, name="SimpleLSTM")
    model.compile(optimizer=Adam(1e-3), loss="mse", metrics=["mae"])
    return model


# ─────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────

def get_callbacks(
    checkpoint_path: str,
    patience: int = 25,
    min_lr: float = 1e-7
) -> list:
    """
    Standard training callbacks:
      - EarlyStopping  : Halt when val_loss stops improving
      - ReduceLROnPlateau : Lower LR when plateau detected
      - ModelCheckpoint   : Save best weights
    """
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    return [
        EarlyStopping(
            monitor="val_loss",
            patience=patience,
            restore_best_weights=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=patience // 3,
            min_lr=min_lr,
            verbose=1
        ),
        ModelCheckpoint(
            filepath=checkpoint_path,
            monitor="val_loss",
            save_best_only=True,
            verbose=1
        )
    ]


# ─────────────────────────────────────────────
# SAVE / LOAD
# ─────────────────────────────────────────────

def save_model(model: Model, path: str) -> None:
    """Save the Keras model in the native .keras format."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    model.save(path)
    print(f"[Model] Saved → {path}")


def load_model(path: str) -> Model:
    """Load a saved Keras model, registering custom layers."""
    model = tf.keras.models.load_model(
        path,
        custom_objects={
            "TemporalAttention": TemporalAttention,
            "loss": _binary_focal_loss(alpha=0.6, gamma=2.0),
        }
    )
    print(f"[Model] Loaded ← {path}")
    return model


# ─────────────────────────────────────────────
# QUICK SANITY CHECK
# ─────────────────────────────────────────────

if __name__ == "__main__":
    WINDOW     = 60
    N_FEATURES = 16   # matches FEATURE_COLS in data_pipeline.py
    HORIZON    = 1

    model = build_lstm_model(WINDOW, N_FEATURES, HORIZON)
    dummy_input = np.random.rand(8, WINDOW, N_FEATURES).astype(np.float32)
    dummy_output = model.predict(dummy_input, verbose=0)
    print(f"Dummy output shape: {dummy_output.shape}")   # (8, 1)
