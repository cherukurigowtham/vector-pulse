use pyo3::prelude::*;

#[pyfunction]
fn calculate_stats(data: Vec<f64>) -> PyResult<(f64, f64)> {
    if data.is_empty() { return Ok((0.0, 0.0)); }
    let n = data.len() as f64;
    let avg = data.iter().sum::<f64>() / n;
    let variance = data.iter().map(|x| (avg - x).powi(2)).sum::<f64>() / n;
    Ok((avg, variance.sqrt()))
}

#[pyfunction]
fn is_anomaly_sigma(current: f64, avg: f64, std_dev: f64, threshold: f64) -> PyResult<bool> {
    if std_dev == 0.0 { return Ok(false); }
    let z_score = (current - avg).abs() / std_dev;
    Ok(z_score > threshold)
}

#[pyfunction]
fn calculate_trust_score(delivered: i32, total: i32) -> PyResult<f64> {
    if total == 0 { return Ok(50.0); } // Neutral for new users
    Ok((delivered as f64 / total as f64) * 100.0)
}

#[pymodule]
fn vector_pulse(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_stats, m)?)?;
    m.add_function(wrap_pyfunction!(is_anomaly_sigma, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_trust_score, m)?)?;
    Ok(())
}
