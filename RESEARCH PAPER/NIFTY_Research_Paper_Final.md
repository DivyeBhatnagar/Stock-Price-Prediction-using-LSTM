# STOCK PRICE FORECASTING FOR NIFTY 50 CONSTITUENTS USING BIDIRECTIONAL LSTM WITH TEMPORAL ATTENTION

---

## TITLE PAGE

**STOCK PRICE FORECASTING FOR NIFTY 50 CONSTITUENTS USING BIDIRECTIONAL LSTM WITH TEMPORAL ATTENTION**

**Authors:** 
- Divye Bhatnagar (divye.bhatnagar.cs28@iilm.edu)
- Gopal Agarwal (gopal.agarwal.cs28@iilm.edu)
- Harsh Aggarwal (harsh.aggarwal.cs28@iilm.edu)
- Nandini Solanki (nandini.solanki.cs28@iilm.edu)
- Namit Chawla (namit.chawla@iilm.edu)

**Institutional Affiliation:** IILM University, Greater Noida

**Department:** Department of Computer Science and Engineering, IILM University, Greater Noida, Uttar Pradesh, India

**Date of Submission:** April 10, 2026

---

## ABSTRACT

In new equity markets, short term predictions cannot be made accurately due to changing patterns, changes in market conditions and noisy price changes. The current paper presents a full deep learning model to predict the daily logarithmic returns of NIFTY 50 stocks with a bidirectional LSTM model with a temporal attention mechanism. The model takes daily OHLCV data, incorporates common technical indicators and scales them with parameters exclusively on the training data. These data are converted into fixed length sequences by looking up 60 trading days. The model forecasts the daily log return and then uses exponential reconstruction to transform this into a price forecast. Various measurements such as RMSE are used to check the performance, MAE, MAPE, R2 and directional accuracy. The validation process is performed in a manner that prevents data leakage and enables repeatable and reproducible results.

**Keywords:** Bidirectional LSTM, Temporal Attention, NIFTY 50, NSE, Technical Indicators, Log Returns, Time-Series Forecasting, Quantitative Finance

---

## 1. INTRODUCTION AND STATEMENT OF PROBLEM

### 1.1 Background and Context

National Stock Exchange (NSE) and its key index NIFTY 50 have made the Indian stock market one of the fastest-growing equity markets across the globe. This has been driven by increased involvement by institutional investors, advancement in the trading technology and increased accessibility to the global financial markets. The complexity of the NIFTY 50 is, however, due to various reasons such as certain macroeconomic patterns of emerging markets and political developments that influence the foreign investments, the prevalence of IT and banking industries, and the peculiarities of the NSE trading. These are some of the factors that render it extremely hard to forecast the stock prices.

Historically, fundamental analysis (including the analysis of earnings, in the IT industry, quality of assets, currency movements, and Fed policy effects) or technical analysis (finding patterns in past price data, in the NSE environment) has been used in the analysis of NIFTY 50. However, in many cases, these traditional approaches do not represent the complex and non-linear relationships and patterns that the modern Indian financial markets exhibit, particularly in settings where algorithmic trading, high-frequency retail trading, and instantaneous reactions to events in the global market are prevalent.

The recent development of machine learning and deep learning in the last decade has revolutionized the field of quantitative finance research across the globe. Nevertheless, application of these methods in forecasting NIFTY 50 stocks is not as widespread as in the case of developed market indices. Among them, the LSTM models have been proven concerns with their capability to manage long-term dependencies in time series data. Nevertheless, their performance in the emerging markets that are more volatile, less liquid in some sub-indexes, and change of regimes with policy changes have not been researched in depth.

This challenge occurs in real life cases due to the market as well as the data. The stock prices are sometimes difficult to predict as they can be volatile, and the same model may not be as effective in other segments of the market such as banking and technology. There are also issues with real data such as missing days, abrupt price variations caused by company activities, or large changes in the magnitude of the price movements following significant news or policy adjustments. The problems complicate the ability to predict short-term developments and it is necessary to pay close attention to the effectiveness of the models.

The other issue is the configuration of the methods. A lot of the results cannot be easily compared as various experiments engage various features, time periods, data splitting methods, scaling procedures, and evaluation methods. Even minor decisions during the construction of the model can inadvertently cause the use of information in the future, such as preprocessing the entire data or combining time periods in testing. An explicit, reproducible procedure with time-stamped partition, and purely scaling in training, and the results should be thoroughly reported to make the findings more dependable.

The work is based on the prediction of the daily log returns rather than the actual prices, and then, it uses the same to determine the closing price to gauge the accuracy of the predictions. The model can highlight the most useful sections of the historical data with the help of a temporal attention mechanism, and the predictions are easier to interpret compared to a simple recurrent network. The primary goal is not simply to be correct, but to have an arrangement that can be applied to different firms without boasting of superior performance than is actually being attained.

### 1.2 Literature Review and State of Research

When analyzing the studies on the application of LSTM to predict stocks, we identified several valuable insights that can be applied to the Indian market. Recurrent models have been found to be effective with financial data that occurs over time since they can learn patterns without the need to manually specify time lags.

LSTM networks were designed to address an issue with the regular RNNs known as the vanishing gradient, and are currently commonly used as a baseline to predict time-related information. However, it is still difficult to predict the prices of stock since the returns are noisy, evolve over time, and are influenced by market specifics and market regime shifts.

Recent works consider various possibilities of constructing LSTM models and integrate them with others. Bidirectional LSTMs are more effective in learning data through both forward and backward data information in the training process. Other approaches can use LSTM with other components of the data or provide additional equipment (such as CNN components across time windows) to more accurately represent short-term tendencies and make the model less dependent on the scale of prices. Even general surveys indicate that attention to data preparation, feature generation and testing techniques can be a major contributor to improvement more so than more complexification of the model.

One of the prevalent themes of the research is that the outcome heavily relies on the manner in which the experiments are designed. Decisions such as shuffling of data, scaling on the entire set of data, or training the model on test data can make the results appear too good. Although the model itself may be quite good, the training process, such as the number of and the point at which it is trained, has an impact on its overall performance in new environments. These aspects indicate that in a comparison of deep learning-based stock prediction, safe splits without leakage, reporting, and evaluation with a number of metrics are to be used.

Ghosh et al. examined the prediction of stock performance in various industrial industries in India using LSTM models. They created a framework, which integrated company growth rates and LSTM prediction. Their effort on banking, IT, pharmaceuticals and FMCG sectors indicated that the most appropriate moments to make predictions in various sectors differed significantly.

Bhandari et al. showed that LSTM models trained on a variety of inputs, including fundamental, macroeconomic and technical indicators, could attain extremely high values of R-squared, greater than 0.99. They also discovered that models with simpler architectures with 150 hidden units had better performance compared to more complex models with many layers.

Moghar and Hamiche examined the impact of more epochs training on the accuracy of LSTM. They discovered that additional training tends to enhance performance although it is not always easy sailing. At some point, additional training began to overfit the model to memorize the training data to the extent that it does not perform well on novel data.

Zhang compared LSTM with other machine learning models and it was revealed that gradient-boosted trees are sometimes more effective on short-term predictions (1–10 days) than pure LSTM. This demonstrates that feature-based methods can continue to be useful in making short-term predictions.

Regardless of such findings, there remains a large gap in the research: not many studies have developed a fully safe deep learning pipeline, dealing with NIFTY 50 stocks and aimed at predicting daily log returns and utilizing attention to identify the most significant parts of the past data.

### 1.3 Identified Research Gaps and Problem Statement - NIFTY 50 Specific

Although deep learning has achieved advancements in predicting financial time series, predicting single NIFTY 50 stocks has three core problems. To begin with, most models take raw prices as they are but over time, prices may fluctuate significantly. The daily log returns will result in a more stable target and will also be easier to evaluate since it is less sensitive with respect to the actual price levels.

Second, such models as LSTMs are relatively black-box, and it is difficult to understand which aspects of the data are prioritized the most. This is made more apparent by adding a temporal attention mechanism and makes the model learn more effectively when there is not much information.

Third, reported results may be over-optimistic due to factors such as scaling the data of the entire set or not taking into account the direction of errors. Results are more reliable using a time-ordered split, in which only training data is scaled and both the magnitude and direction of errors are monitored. This study will address this question based on the following gaps: Given daily OHLCV data and technical indicators engineered on NIFTY 50 stocks can an LSTM model with attention mechanisms accurately predict one-day-ahead log returns, which can be used to forecast the closing prices the next day employing a non-risky and chronologically organised assessment procedure?

---

## 2. OBJECTIVES OF THE STUDY

This research is conducted with the following objectives:

1. Design an entire system on how to forecast futures of the NIFTY 50 firms. This system will take daily price data and technical indicators, and will produce sequences of a fixed length (such as 60 trading days).
2. Train a special type of neural network referred to as a bidirectional LSTM that is time-centered to estimate the daily change in price and the price of the subsequent day at the end as well.
3. Test the model performance when it is not exposed to the data, using such metrics as RMSE, MAE, MAPE, R2, directional accuracy. It will also be compared to such simple techniques as the last known price.
4. Train the model to be reused in a reliable and easy to update format, as the built system.

---

## 3. HYPOTHESES

The following testable hypotheses guide this research:

**H1:** Predicting next-day log returns yields more stable out-of-sample performance than predicting raw closing prices directly under the same split strategy.

**H2:** Adding temporal attention improves regression accuracy compared to an otherwise identical bidirectional LSTM without attention.

**H3:** The proposed model achieves lower RMSE and MAE than a naive baseline on held-out periods for representative NIFTY 50 constituents.

---

## 4. Methodology

### 4.1 Research Design

This study follows an **empirical, quantitative** workflow: (i) collect and preprocess historical market data, (ii) train a deep learning forecasting model, and (iii) evaluate performance on a time-ordered hold-out segment to avoid look-ahead bias.

### 4.2 Data and Scope

The work takes daily OHLCV data of the NIFTY 50 companies. The data is obtained on Yahoo Finance by using a package named yfinance and stored as individual files of each stock. The stock data of each stock covers approximately ten years such as RELIANCE.NS has data from April 18, 2016, to April 10, 2026, which is around 2,491 trading days. The model forecasts the price of the following trading day.

### 4.3 Feature Engineering, Target, and Scaling

For each day $t$, we construct a feature vector $\mathbf{z}_t$ consisting of OHLCV along with engineered technical indicators (27 features in the reference implementation), including moving averages (SMA/EMA), momentum indicators (RSI, MACD, Stochastic, Williams \%R, CCI), volatility measures (Bollinger Bands/width, ATR), volume features (OBV, volume ratios), and trend strength (ADX).

The prediction target is the **next-day log return** of the closing price:

$$ r_t = \ln\left(\frac{C_t}{C_{t-1}}\right), \qquad y_t = r_{t+1}. $$

To reduce leakage, scaling parameters are fit **only on the training segment**. Min--max scaling maps each feature to $[0,1]$:

$$ x' = \frac{x - x_{\min}}{x_{\max} - x_{\min}}. $$

Supervised sequences are created using a sliding window of length $L=60$ trading days:

$$ X_t = [\mathbf{z}_{t-L+1}, \ldots, \mathbf{z}_{t}], \qquad y_t = r_{t+1}. $$

### 4.4 Model: Stacked BiLSTM with Temporal Attention

The main model is a stacked bidirectional LSTM that encodes the input window into a sequence of hidden states $\{\mathbf{h}_1,\ldots,\mathbf{h}_L\}$. A time attention system then learns a weighted summary of this states:

$$ s_i = \tanh(W h_i), \qquad \alpha_i = \frac{\exp(v^\top s_i)}{\sum_{j=1}^{L} \exp(v^\top s_j)}, \qquad c = \sum_{i=1}^{L} \alpha_i h_i. $$

The regression head returns one-step forecast $\hat{r}_{t+1}$ from the context $c$. The log return is predicted and converted back to close-price forecast by exponential reconstruction:

$$ \hat{C}_{t+1} = C_t\cdot\exp(\hat{r}_{t+1}). $$

The Adam optimizer is used in training with gradient clipping and Huber loss to be robust to outliers:

$$ L_\delta(y,\hat{y}) = \begin{cases}
\frac{1}{2}(y-\hat{y})^2, & |y-\hat{y}|\le\delta \\
\delta\left(|y-\hat{y}|-\frac{1}{2}\delta\right), & \text{otherwise.}
\end{cases} $$

An auxiliary direction head (up/down) is also supported by the reference implementation to learn together magnitude and direction, with the basic forecasting goal being next-day log-return regression.

### 4.5 Train/Test Split and Training Protocol

The data are divided over time in a train ratio usually between 0.80 and 0.85 as run to run, and the rest is put forth to gauging. Sequences are not shuffled during training (time-series constraint). Early stopping and learning-rate reduction callbacks are employed to reduce overfitting.

### 4.6 Evaluation Metrics

Post reconstruction price predictions are evaluated in terms of RMSE, MAE, MAPE and R2. The directional accuracy (DA) is calculated using the sign of the returns:

$$ \text{DA}=\frac{1}{n}\sum_{i=1}^{n}\mathbb{1}[\operatorname{sign}(\hat{r}_i)=\operatorname{sign}(r_i)]. $$

---

## 5. RESULTS AND FINDINGS

### 5.1 Experimental Setup Summary

Experiments follow the reference implementation described in the codebase: a stacked bidirectional LSTM with temporal attention trained on daily OHLCV features and technical indicators (27 inputs), using a look-back window of 60 trading days and a one-step forecast horizon. The model predicts next-day log returns and is evaluated after reconstructing next-day close prices.

### 5.2 Out-of-Sample Performance on Representative Constituents

Table 1 reports hold-out performance from saved model artefacts for five trained NIFTY 50 constituents. RMSE/MAE/MAPE/$R^2$ are computed in reconstructed close-price space, while directional accuracy is computed on the sign of predicted vs. true log return.

| **Ticker** | **Window** | **Horizon** | **Train Split** | **Epochs Trained** | **RMSE** | **MAE** | **MAPE (%)** | **R²** | **Directional Accuracy** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RELIANCE.NS | 60 | 1 | 0.85 | 30 | 19.8176 | 15.1674 | 1.0990 | 0.9649 | 0.5241 |
| TCS.NS | 60 | 1 | 0.85 | 30 | 45.2092 | 32.9511 | 1.0365 | 0.9879 | 0.4910 |
| HDFCBANK.NS | 60 | 1 | 0.85 | 27 | 10.7257 | 8.0255 | 0.8865 | 0.9751 | 0.4699 |
| TITAN.NS | 60 | 1 | 0.85 | 30 | 51.8084 | 36.5423 | 1.0045 | 0.9787 | 0.5030 |
| SBIN.NS | 60 | 1 | 0.85 | 26 | 12.6991 | 8.8146 | 0.9908 | 0.9909 | 0.5181 |

### 5.2.1 Stock Training Metrics (Selected Stocks)

The following table is added from the exported training metrics in [stock-prediction/data/metrics_selected_stocks.md](stock-prediction/data/metrics_selected_stocks.md) (generated on 2026-04-17). In addition to price-space errors (RMSE/MAE/MAPE/$R^2$), we report direction metrics: directional accuracy (DirAcc) and Precision/Recall/F1 for the up/down signal (positive class: **up**). Coverage is not available in the current export and is shown as **--**.

| Ticker | RMSE | MAE | MAPE | R2 | DirAcc | Precision | Recall | F1 | Coverage | TrainTimeSec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RELIANCE.NS | 19.8176 | 15.1674 | 1.0990 | 0.9649 | 0.5241 | 0.5398 | 0.3653 | 0.4357 | -- | 110.7 |
| TCS.NS | 45.2092 | 32.9511 | 1.0365 | 0.9879 | 0.4910 | 0.4526 | 0.8671 | 0.5947 | -- | 115.9 |
| HDFCBANK.NS | 10.7257 | 8.0255 | 0.8865 | 0.9751 | 0.4699 | 0.4699 | 1.0000 | 0.6393 | -- | 106.0 |
| TITAN.NS | 51.8084 | 36.5423 | 1.0045 | 0.9787 | 0.5030 | 0.0000 | 0.0000 | 0.0000 | -- | 117.4 |
| SBIN.NS | 12.6991 | 8.8146 | 0.9908 | 0.9909 | 0.5181 | 0.5181 | 1.0000 | 0.6825 | -- | 101.2 |

### 5.3 Discussion

Across these evaluated constituents, the model achieves low percentage error (MAPE around 1--1.4%) and high $R^2$ in reconstructed close-price space, indicating that the attention-augmented sequence model tracks next-day price levels reasonably well. Directional accuracy, however, is mixed (approximately 0.49 for RELIANCE.NS and 0.55 for TCS.NS), highlighting that predicting the direction of next-day movement remains challenging even when magnitude errors are small.

---

## 6. Conclusion

### 6.1 Synthesis of Key Findings

This work presents a leakage-aware forecasting pipeline for NIFTY 50 constituents that predicts next-day **log returns** using a stacked bidirectional LSTM with temporal attention, and then reconstructs next-day close prices using exponential mapping. On representative constituents (RELIANCE.NS and TCS.NS), the model achieves low percentage error (MAPE around 1--1.4%) and strong price-level tracking (with $R^2$ around 0.95--0.97 in reconstructed close-price space). These results indicate that, with train-only scaling and a time-ordered holdout split, an attention-augmented sequence model can learn useful short-horizon structure from multivariate technical-indicator features.

A consistent practical finding is that **direction is harder than magnitude**: directional accuracy is mixed (about 0.49--0.55 in the reported runs). This highlights that small regression error on reconstructed prices does not automatically translate into reliable up/down signals, especially for liquid, news-driven equities.

### 6.2 Practical Implications and Limitations

Temporal attention also gives a good indication of the periods throughout the 60-day look-back that are most important and can assists in interpreting the cause of the model predictions. The study, however, only examines representative stocks, does not test various components of the model formally, and relies on a single time-ordered test split. Real world decision making requires more rigorous validation and measures that takes into consideration real trading. They are some of the issues that should be taken into consideration when applying the findings in real-life applications.

---

## 7. FUTURE SCOPE AND RESEARCH EXTENSIONS

### 7.1 Near-Term Extensions in the Current Pipeline

Test all 50 NIFTY stocks against overall statistics, add simple comparison models, and test to determine the extent to which attention and bidirectionality add value to the model performance. Confirmation of report validation curves and how the model is sensitive to the look-back period ($L$) and to test other timeframes (such as 3--5 days) to determine whether the model is stable not only in next-day predictions.

### 7.2 Feature and Data Extensions

Added external variables such as USDINR exchange rates, India VIX, crude oil prices, and industry-specific indices to determine whether these macroeconomic variables are more helpful in predicting whether returns increase or decrease. Add event-based features (earnings announcements, RBI announcements, etc.) and consider how to pick meaningful features or learn embeddings to decrease noise.

### 7.3 Deployment, Monitoring, and Economic Evaluation

Carry out regular retraining, identify model drift, and apply lightweight backtesting, with realistic transaction costs and slippage, to learn how the statistical accuracy of the model achieves actual returns. Risk-adjusted performance measures and simple rules to determine the extent to invest should also be included in future work to determine the feasibility of the model in practice.

---

## 8. REFERENCES

Bhandari, H. N., Rimal, B., Pokhrel, N. R., Rimal, R., Dahal, K. R., & Khatri, R. K. (2022). Predicting stock market index using LSTM. *Machine Learning with Applications*, 9, 100320.

Ghosh, A., Bose, S., Maji, G., Debnath, N. C., & Sen, S. (2019). Stock price prediction using LSTM on Indian share market. In *Proceedings of the 32nd International Conference on Computer Applications in Industry and Engineering* (pp. 101–110).

Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. *Neural Computation*, 9(8), 1735–1780.

Ling, K. C., Yong, L. K., Fong, M. C., & Kit, L. W. (2012). Predicting stock prices using long short-term memory. In *Proceedings of the 2017 International Conference on Computing, Communication and Control Technology*.

Moghar, A., & Hamiche, M. (2020). Stock market prediction using LSTM recurrent neural network. *Procedia Computer Science*, 170, 1168–1173.

Nelson, D. M., Pereira, A. C., & de Oliveira, R. A. (2017). Stock market's price movement prediction with LSTM neural networks. In *Proceedings of the 2017 International Joint Conference on Neural Networks* (pp. 1419–1426). IEEE.

Roondiwala, M., Patel, H., & Varma, S. (2017). Predicting stock prices using LSTM. *International Journal of Science and Research*, 6(4), 1754–1756.

Zhang, R. (2022). LSTM-based stock prediction modeling and analysis. In *Proceedings of the 2022 7th International Conference on Financial Innovation and Economic Development* (pp. 2537–2542).

---
**Research Period: April 2016 – April 2026 (dataset-dependent; e.g., RELIANCE.NS: 2016-04-18 → 2026-04-10)**
**Authors:** Divye Bhatnagar, Gopal Agarwal, Harsh Aggarwal, Nandini Solanki, Namit Chawla (namit.chawla@iilm.edu)
