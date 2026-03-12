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

#[pyfunction]
fn evaluate_weighted_risk(
    velocity_flag: bool,
    sybil_flag: bool,
    anomaly_flag: bool,
    trust_score: f64,
    vpn_flag: bool
) -> PyResult<f64> {
    let mut score = 0.0;
    
    if velocity_flag { score += 35.0; }
    if sybil_flag    { score += 25.0; }
    if anomaly_flag  { score += 20.0; }
    if vpn_flag      { score += 15.0; }
    
    // Low trust penalty: if trust < 30, add up to 20 points
    if trust_score < 30.0 {
        score += (30.0 - trust_score) * 0.5;
    }
    
    Ok(score.clamp(0.0, 100.0))
}

#[pyfunction]
fn normalize_address(addr: String) -> PyResult<String> {
    let mut normalized = addr.to_lowercase()
        .replace(".", "")
        .replace(",", "")
        .replace("-", " ")
        .replace("/", " ")
        .replace("#", "")
        .replace("  ", " ");
    
    // Simple Indian Address Consolidation
    normalized = normalized.replace("apartment", "apt")
        .replace("apartment", "apt")
        .replace("floor", "fl")
        .replace("road", "rd")
        .replace("street", "st")
        .replace("block", "blk")
        .replace("sector", "sec");

    Ok(normalized.trim().to_string())
}

#[pymodule]
fn vector_pulse(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_stats, m)?)?;
    m.add_function(wrap_pyfunction!(is_anomaly_sigma, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_trust_score, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_weighted_risk, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_address, m)?)?;
    Ok(())
}
