use pyo3::prelude::*;

mod stats;
mod address;
mod identity;
mod geo;

#[pyfunction]
fn calculate_stats(data: Vec<f64>) -> PyResult<(f64, f64)> {
    Ok(stats::calculate_stats(&data))
}

#[pyfunction]
fn is_anomaly_sigma(current: f64, avg: f64, std_dev: f64, threshold: f64) -> PyResult<bool> {
    Ok(stats::is_anomaly_sigma(current, avg, std_dev, threshold))
}

#[pyfunction]
fn detect_amount_anomaly(history: Vec<f64>, current: f64, threshold: f64) -> PyResult<(bool, f64, f64)> {
    Ok(stats::detect_amount_anomaly(&history, current, threshold))
}

#[pyfunction]
fn calculate_trust_score(delivered: i32, total: i32) -> PyResult<f64> {
    Ok(identity::calculate_trust_score(delivered, total))
}

#[pyfunction]
fn normalize_address(addr: String) -> PyResult<String> {
    Ok(address::tokenize_address(&addr).join(" "))
}

#[pyfunction]
fn address_fingerprint(addr: String) -> PyResult<String> {
    let tokens = address::tokenize_address(&addr);
    if tokens.is_empty() { return Ok(String::new()); }
    let mut signals = address::signal_tokens(&tokens);
    signals.sort();
    signals.dedup();
    Ok(signals.join("|"))
}

#[pyfunction]
fn address_match_score(left: String, right: String) -> PyResult<f64> {
    Ok(address::jaccard_similarity(&left, &right))
}

#[pyfunction]
fn evaluate_identity_cluster(
    shared_address_count: i32,
    shared_pin_count: i32,
    shared_subnet_count: i32,
) -> PyResult<(bool, f64)> {
    Ok(identity::evaluate_identity_cluster(shared_address_count, shared_pin_count, shared_subnet_count))
}

#[pyfunction]
fn is_gibberish_address(addr: String) -> PyResult<bool> {
    Ok(address::is_gibberish(&addr))
}

#[pyfunction]
fn is_suspicious_name(name: String) -> PyResult<bool> {
    Ok(identity::is_suspicious_name(&name))
}

#[pyfunction]
fn is_suspicious_phone(phone: String) -> PyResult<bool> {
    Ok(identity::is_suspicious_phone(&phone))
}

#[pyfunction]
fn is_email_name_mismatch(name: String, email: String) -> PyResult<bool> {
    Ok(identity::is_email_name_mismatch(&name, &email))
}

#[pyfunction]
fn has_poor_address_structure(address: String) -> PyResult<bool> {
    Ok(address::has_poor_structure(&address))
}

#[pyfunction]
fn haversine_distance(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> PyResult<f64> {
    Ok(geo::haversine_distance(lat1, lon1, lat2, lon2))
}

#[pyfunction]
fn evaluate_geo_velocity(
    lat1: f64,
    lon1: f64,
    ts1: f64,
    lat2: f64,
    lon2: f64,
    ts2: f64,
    speed_threshold: f64,
) -> PyResult<(bool, f64)> {
    Ok(geo::evaluate_geo_velocity(lat1, lon1, ts1, lat2, lon2, ts2, speed_threshold))
}

#[pymodule]
fn vector_pulse(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_stats, m)?)?;
    m.add_function(wrap_pyfunction!(is_anomaly_sigma, m)?)?;
    m.add_function(wrap_pyfunction!(detect_amount_anomaly, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_trust_score, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_address, m)?)?;
    m.add_function(wrap_pyfunction!(address_fingerprint, m)?)?;
    m.add_function(wrap_pyfunction!(address_match_score, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_identity_cluster, m)?)?;
    m.add_function(wrap_pyfunction!(is_gibberish_address, m)?)?;
    m.add_function(wrap_pyfunction!(is_suspicious_name, m)?)?;
    m.add_function(wrap_pyfunction!(is_suspicious_phone, m)?)?;
    m.add_function(wrap_pyfunction!(is_email_name_mismatch, m)?)?;
    m.add_function(wrap_pyfunction!(has_poor_address_structure, m)?)?;
    m.add_function(wrap_pyfunction!(haversine_distance, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_geo_velocity, m)?)?;
    Ok(())
}
