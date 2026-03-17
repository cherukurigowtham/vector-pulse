pub fn percentile(sorted: &[f64], pct: f64) -> f64 {
    if sorted.is_empty() { return 0.0; }
    if sorted.len() == 1 { return sorted[0]; }
    let rank = pct * (sorted.len() - 1) as f64;
    let lower = rank.floor() as usize;
    let upper = rank.ceil() as usize;
    if lower == upper {
        sorted[lower]
    } else {
        let weight = rank - lower as f64;
        sorted[lower] * (1.0 - weight) + sorted[upper] * weight
    }
}

pub fn median(sorted: &[f64]) -> f64 {
    percentile(sorted, 0.5)
}

pub fn robust_z_score(current: f64, sorted: &[f64]) -> f64 {
    if sorted.is_empty() { return 0.0; }
    let med = median(sorted);
    let deviations: Vec<f64> = sorted.iter().map(|value| (value - med).abs()).collect();
    let mut deviations_sorted = deviations;
    deviations_sorted.sort_by(|a, b| a.total_cmp(b));
    let mad = median(&deviations_sorted);
    if mad == 0.0 { return 0.0; }
    0.6745 * (current - med).abs() / mad
}

pub fn calculate_stats(data: &[f64]) -> (f64, f64) {
    if data.is_empty() { return (0.0, 0.0); }
    let n = data.len() as f64;
    let avg = data.iter().sum::<f64>() / n;
    let variance = data.iter().map(|x| (avg - x).powi(2)).sum::<f64>() / n;
    (avg, variance.sqrt())
}

pub fn is_anomaly_sigma(current: f64, avg: f64, std_dev: f64, threshold: f64) -> bool {
    if std_dev == 0.0 { return false; }
    (current - avg).abs() / std_dev > threshold
}

pub fn detect_amount_anomaly(history: &[f64], current: f64, threshold: f64) -> (bool, f64, f64) {
    if history.len() < 2 { return (false, 0.0, 0.0); }
    let (avg, std_dev) = calculate_stats(history);
    let sigma_outlier = if std_dev > 0.0 {
        (current - avg).abs() / std_dev > threshold
    } else {
        false
    };

    let mut sorted = history.to_vec();
    sorted.sort_by(|a, b| a.total_cmp(b));

    let q1 = percentile(&sorted, 0.25);
    let q3 = percentile(&sorted, 0.75);
    let iqr = q3 - q1;
    let iqr_outlier = if iqr > 0.0 {
        current < q1 - (1.5 * iqr) || current > q3 + (1.5 * iqr)
    } else {
        false
    };

    let robust_outlier = robust_z_score(current, &sorted) > threshold.max(3.5);
    (sigma_outlier || robust_outlier || iqr_outlier, avg, std_dev)
}
