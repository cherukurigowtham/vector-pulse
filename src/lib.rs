use std::collections::HashSet;

use pyo3::prelude::*;

const GENERIC_ADDRESS_TOKENS: &[&str] = &[
    "address",
    "area",
    "building",
    "city",
    "country",
    "district",
    "door",
    "floor",
    "house",
    "india",
    "lane",
    "layout",
    "locality",
    "near",
    "number",
    "opp",
    "opposite",
    "phase",
    "plot",
    "post",
    "road",
    "sector",
    "state",
    "street",
    "tower",
    "unit",
];

const LOW_SIGNAL_TOKENS: &[&str] = &[
    "and",
    "at",
    "beside",
    "by",
    "front",
    "in",
    "inside",
    "landmark",
    "mr",
    "mrs",
    "ms",
    "na",
    "nil",
    "nr",
    "of",
    "on",
    "the",
    "to",
];

fn canonical_token(token: &str) -> Option<String> {
    if token.is_empty() {
        return None;
    }

    if LOW_SIGNAL_TOKENS.contains(&token) {
        return None;
    }

    let mapped = match token {
        "apt" | "apartment" | "apartments" | "flat" | "suite" | "unit" => "unit",
        "fl" | "flr" | "floor" => "floor",
        "rd" | "road" => "road",
        "st" | "street" => "street",
        "ln" | "lane" => "lane",
        "blk" | "block" => "block",
        "sec" | "sector" => "sector",
        "ph" | "phase" => "phase",
        "twr" | "tower" => "tower",
        "bldg" | "building" => "building",
        "h" | "hno" | "house" | "house_no" | "number" => "house",
        "aptno" | "door" | "doorno" | "door_no" => "unit",
        "soc" | "society" => "society",
        "ngr" | "nagar" => "nagar",
        "layout" => "layout",
        "crossroad" | "cross" => "cross",
        "mainroad" | "main" => "main",
        "po" | "postoffice" => "post",
        "bengaluru" | "bangalore" => "bengaluru",
        "bombay" | "mumbai" => "mumbai",
        "calcutta" | "kolkata" => "kolkata",
        "madras" | "chennai" => "chennai",
        "pin" | "pincode" | "zipcode" | "zip" | "no" => return None,
        "opp" | "opposite" | "near" => return None,
        _ => token,
    };

    if mapped.chars().all(|ch| ch.is_ascii_digit()) {
        if mapped.len() >= 10 {
            return None;
        }
        if mapped.len() == 6 {
            return Some(format!("pin{}", mapped));
        }
        return Some(mapped.to_string());
    }

    if mapped.len() == 1 && !mapped.chars().all(|ch| ch.is_ascii_digit()) {
        return None;
    }

    Some(mapped.to_string())
}

fn tokenize_address(addr: &str) -> Vec<String> {
    let mut cleaned = String::with_capacity(addr.len());
    for ch in addr.chars().flat_map(|ch| ch.to_lowercase()) {
        if ch.is_ascii_alphanumeric() {
            cleaned.push(ch);
        } else {
            cleaned.push(' ');
        }
    }

    let mut tokens = Vec::new();
    for raw in cleaned.split_whitespace() {
        if let Some(token) = canonical_token(raw) {
            if tokens.last() != Some(&token) {
                tokens.push(token);
            }
        }
    }
    tokens
}

fn signal_tokens(tokens: &[String]) -> Vec<String> {
    let filtered: Vec<String> = tokens
        .iter()
        .filter(|token| !GENERIC_ADDRESS_TOKENS.contains(&token.as_str()))
        .cloned()
        .collect();

    if filtered.is_empty() {
        tokens.to_vec()
    } else {
        filtered
    }
}

fn percentile(sorted: &[f64], pct: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    if sorted.len() == 1 {
        return sorted[0];
    }
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

fn median(sorted: &[f64]) -> f64 {
    percentile(sorted, 0.5)
}

fn robust_z_score(current: f64, sorted: &[f64]) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let med = median(sorted);
    let deviations: Vec<f64> = sorted.iter().map(|value| (value - med).abs()).collect();
    let mut deviations_sorted = deviations;
    deviations_sorted.sort_by(|a, b| a.total_cmp(b));
    let mad = median(&deviations_sorted);
    if mad == 0.0 {
        return 0.0;
    }
    0.6745 * (current - med).abs() / mad
}

#[pyfunction]
fn calculate_stats(data: Vec<f64>) -> PyResult<(f64, f64)> {
    if data.is_empty() {
        return Ok((0.0, 0.0));
    }

    let n = data.len() as f64;
    let avg = data.iter().sum::<f64>() / n;
    let variance = data.iter().map(|x| (avg - x).powi(2)).sum::<f64>() / n;
    Ok((avg, variance.sqrt()))
}

#[pyfunction]
fn is_anomaly_sigma(current: f64, avg: f64, std_dev: f64, threshold: f64) -> PyResult<bool> {
    if std_dev == 0.0 {
        return Ok(false);
    }
    let z_score = (current - avg).abs() / std_dev;
    Ok(z_score > threshold)
}

#[pyfunction]
fn detect_amount_anomaly(history: Vec<f64>, current: f64, threshold: f64) -> PyResult<(bool, f64, f64)> {
    if history.len() < 2 {
        return Ok((false, 0.0, 0.0));
    }

    let (avg, std_dev) = calculate_stats(history.clone())?;
    let sigma_outlier = if std_dev > 0.0 {
        (current - avg).abs() / std_dev > threshold
    } else {
        false
    };

    let mut sorted = history;
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
    Ok((sigma_outlier || robust_outlier || iqr_outlier, avg, std_dev))
}

#[pyfunction]
fn calculate_trust_score(delivered: i32, total: i32) -> PyResult<f64> {
    if total == 0 {
        return Ok(50.0);
    }
    Ok((delivered as f64 / total as f64) * 100.0)
}

#[pyfunction]
fn evaluate_weighted_risk(
    velocity_flag: bool,
    sybil_flag: bool,
    anomaly_flag: bool,
    trust_score: f64,
    vpn_flag: bool,
) -> PyResult<f64> {
    let mut score = 0.0;

    if velocity_flag {
        score += 35.0;
    }
    if sybil_flag {
        score += 25.0;
    }
    if anomaly_flag {
        score += 20.0;
    }
    if vpn_flag {
        score += 15.0;
    }

    if trust_score < 30.0 {
        score += (30.0 - trust_score) * 0.5;
    }

    Ok(score.clamp(0.0, 100.0))
}

#[pyfunction]
fn normalize_address(addr: String) -> PyResult<String> {
    Ok(tokenize_address(&addr).join(" "))
}

#[pyfunction]
fn address_fingerprint(addr: String) -> PyResult<String> {
    let tokens = tokenize_address(&addr);
    if tokens.is_empty() {
        return Ok(String::new());
    }

    let mut signals = signal_tokens(&tokens);
    signals.sort();
    signals.dedup();

    Ok(signals.join("|"))
}

#[pyfunction]
fn address_match_score(left: String, right: String) -> PyResult<f64> {
    let left_tokens: HashSet<String> = signal_tokens(&tokenize_address(&left)).into_iter().collect();
    let right_tokens: HashSet<String> = signal_tokens(&tokenize_address(&right)).into_iter().collect();

    if left_tokens.is_empty() || right_tokens.is_empty() {
        return Ok(0.0);
    }

    let intersection = left_tokens.intersection(&right_tokens).count() as f64;
    let union = left_tokens.union(&right_tokens).count() as f64;
    Ok(((intersection / union) * 100.0).clamp(0.0, 100.0))
}

#[pyfunction]
fn evaluate_identity_cluster(
    shared_address_count: i32,
    shared_pin_count: i32,
    shared_subnet_count: i32,
) -> PyResult<(bool, f64)> {
    let mut score = 0.0;

    if shared_address_count > 1 {
        score += (shared_address_count.min(6) as f64 - 1.0) * 18.0;
    }
    if shared_pin_count > 2 {
        score += (shared_pin_count.min(8) as f64 - 2.0) * 5.0;
    }
    if shared_subnet_count > 1 {
        score += (shared_subnet_count.min(6) as f64 - 1.0) * 9.0;
    }

    let final_score = score.clamp(0.0, 100.0);
    Ok((final_score >= 30.0, final_score))
}

#[pyfunction]
fn is_gibberish_address(addr: String) -> PyResult<bool> {
    if addr.is_empty() {
        return Ok(false);
    }
    
    let letters: String = addr.chars()
        .filter(|c| c.is_ascii_alphabetic())
        .map(|c| c.to_ascii_lowercase())
        .collect();

    if letters.len() < 5 {
        return Ok(false);
    }
    
    let vowels = letters.chars().filter(|c| matches!(*c, 'a' | 'e' | 'i' | 'o' | 'u')).count();
    let consonants = letters.len() - vowels;
    
    if vowels == 0 && consonants >= 5 {
        return Ok(true);
    }
    
    if (vowels as f64) / (letters.len() as f64) > 0.8 && letters.len() > 5 {
        return Ok(true);
    }

    let mut max_repeat = 1;
    let mut current_repeat = 1;
    let mut last_char = ' ';
    
    for c in letters.chars() {
        if c == last_char {
            current_repeat += 1;
            if current_repeat > max_repeat {
                max_repeat = current_repeat;
            }
        } else {
            current_repeat = 1;
            last_char = c;
        }
    }
    
    if max_repeat >= 4 {
        return Ok(true);
    }
    
    Ok(false)
}

#[pyfunction]
fn is_suspicious_name(name: String) -> PyResult<bool> {
    if name.is_empty() {
        return Ok(false);
    }

    let trimmed = name.trim();
    if trimmed.len() <= 1 {
        return Ok(true);
    }

    let lower = trimmed.to_lowercase();
    if lower == "test" || lower == "fake" || lower.starts_with("test ") || lower.starts_with("fake ") {
        return Ok(true);
    }

    let letters: String = trimmed.chars()
        .filter(|c| c.is_ascii_alphabetic())
        .collect();

    if letters.len() < trimmed.chars().filter(|c| !c.is_whitespace()).count() {
        return Ok(true); 
    }

    let vowels = letters.chars().filter(|c| matches!(c.to_ascii_lowercase(), 'a' | 'e' | 'i' | 'o' | 'u')).count();
    let consonants = letters.len() - vowels;

    if vowels == 0 && consonants >= 4 {
        return Ok(true);
    }

    Ok(false)
}

#[pyfunction]
fn is_suspicious_phone(phone: String) -> PyResult<bool> {
    // Strip common prefixes
    let mut cleaned = phone.replace("+91", "").replace("-", "").replace(" ", "");
    if cleaned.starts_with("0") && cleaned.len() > 10 {
        cleaned.remove(0);
    }
    
    // Check length (assuming generic 10 digit standard for this test, can be expanded)
    if cleaned.len() < 7 || cleaned.len() > 15 {
        return Ok(true);
    }
    
    // Check if it's all digits
    if !cleaned.chars().all(|c| c.is_ascii_digit()) {
        return Ok(true);
    }

    // Check for identical digits (e.g. 9999999999)
    if cleaned.chars().all(|c| c == cleaned.chars().next().unwrap()) {
        return Ok(true);
    }
    
    // Check for sequential patterns
    if cleaned.contains("123456") || cleaned.contains("098765") {
        return Ok(true);
    }

    Ok(false)
}

#[pyfunction]
fn is_email_name_mismatch(name: String, email: String) -> PyResult<bool> {
    if name.is_empty() || email.is_empty() || !email.contains('@') {
        return Ok(false);
    }
    
    let local_part = email.split('@').next().unwrap_or("").to_lowercase();
    if local_part.is_empty() {
        return Ok(false);
    }
    
    let name_lower = name.to_lowercase();
    let name_parts: Vec<&str> = name_lower.split_whitespace()
        .filter(|p| p.len() > 2)
        .collect();
        
    if name_parts.is_empty() {
        return Ok(false);
    }
    
    // If ANY significant part of the name is in the email, it's NOT a mismatch
    let has_match = name_parts.iter().any(|part| local_part.contains(part));
    
    Ok(!has_match)
}

#[pyfunction]
fn has_poor_address_structure(address: String) -> PyResult<bool> {
    if address.is_empty() {
        return Ok(true);
    }
    
    // Check if the address contains at least one digit
    let has_digit = address.chars().any(|c| c.is_ascii_digit());
    
    Ok(!has_digit)
}

#[pymodule]
fn vector_pulse(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_stats, m)?)?;
    m.add_function(wrap_pyfunction!(is_anomaly_sigma, m)?)?;
    m.add_function(wrap_pyfunction!(detect_amount_anomaly, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_trust_score, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_weighted_risk, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_address, m)?)?;
    m.add_function(wrap_pyfunction!(address_fingerprint, m)?)?;
    m.add_function(wrap_pyfunction!(address_match_score, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_identity_cluster, m)?)?;
    m.add_function(wrap_pyfunction!(is_gibberish_address, m)?)?;
    m.add_function(wrap_pyfunction!(is_suspicious_name, m)?)?;
    m.add_function(wrap_pyfunction!(is_suspicious_phone, m)?)?;
    m.add_function(wrap_pyfunction!(is_email_name_mismatch, m)?)?;
    m.add_function(wrap_pyfunction!(has_poor_address_structure, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_address_collapses_variants() {
        let normalized = normalize_address("Flat No. 12, Green Heights Apartment, Sector-5, Bangalore 560001".into()).unwrap();
        assert_eq!(normalized, "unit 12 green heights unit sector 5 bengaluru pin560001");
    }

    #[test]
    fn fingerprint_handles_equivalent_addresses() {
        let left = address_fingerprint("Apartment 12 / Green Heights, Sector 5, Bengaluru - 560001".into()).unwrap();
        let right = address_fingerprint("Flat 12 Green Heights Sec 5 Bangalore 560001".into()).unwrap();
        assert_eq!(left, right);
    }

    #[test]
    fn address_match_score_rewards_shared_signal_tokens() {
        let score = address_match_score(
            "Flat 12 Green Heights Sector 5 Bangalore 560001".into(),
            "Apartment 12 Green Heights Sec 5 Bengaluru 560001".into(),
        )
        .unwrap();
        assert!(score >= 70.0);
    }

    #[test]
    fn detect_amount_anomaly_flags_clear_outlier() {
        let (is_outlier, avg, std_dev) =
            detect_amount_anomaly(vec![999.0, 1001.0, 1005.0, 998.0, 1002.0], 1499.0, 3.0).unwrap();
        assert!(is_outlier);
        assert!(avg > 0.0);
        assert!(std_dev >= 0.0);
    }

    #[test]
    fn detect_amount_anomaly_ignores_stable_nearby_values() {
        let (is_outlier, _, _) =
            detect_amount_anomaly(vec![999.0, 1001.0, 1005.0, 998.0, 1002.0], 1003.0, 3.0).unwrap();
        assert!(!is_outlier);
    }

    #[test]
    fn identity_cluster_scores_shared_signals() {
        let (flagged, score) = evaluate_identity_cluster(3, 4, 2).unwrap();
        assert!(flagged);
        assert!(score >= 30.0);
    }

    #[test]
    fn gibberish_detection_flags_nonsense() {
        assert!(is_gibberish_address("qwrtypsd".into()).unwrap());
        assert!(is_gibberish_address("aoieui".into()).unwrap());
        assert!(is_gibberish_address("zzzz street".into()).unwrap());
        assert!(!is_gibberish_address("Main Street Bengaluru".into()).unwrap());
    }

    #[test]
    fn suspicious_name_detection() {
        assert!(is_suspicious_name("John123".into()).unwrap());
        assert!(is_suspicious_name("Xyzklm".into()).unwrap());
        assert!(is_suspicious_name("A".into()).unwrap());
        assert!(is_suspicious_name("test user".into()).unwrap());
        assert!(!is_suspicious_name("Rahul Sharma".into()).unwrap());
    }

    #[test]
    fn suspicious_phone_detection() {
        assert!(is_suspicious_phone("9999999999".into()).unwrap());
        assert!(is_suspicious_phone("1234567890".into()).unwrap());
        assert!(is_suspicious_phone("abc".into()).unwrap());
        assert!(is_suspicious_phone("987654".into()).unwrap()); // Too short
        assert!(!is_suspicious_phone("+919876543210".into()).unwrap());
        assert!(!is_suspicious_phone("9876543210".into()).unwrap());
    }

    #[test]
    fn email_name_mismatch_detection() {
        assert!(!is_email_name_mismatch("Rahul Kumar".into(), "rahulkumar99@gmail.com".into()).unwrap());
        assert!(!is_email_name_mismatch("Rahul Kumar".into(), "rahul.k@gmail.com".into()).unwrap());
        assert!(is_email_name_mismatch("Rahul Kumar".into(), "jason.bourne.x@yahoo.com".into()).unwrap());
    }

    #[test]
    fn poor_address_structure_detection() {
        assert!(has_poor_address_structure("Near the big temple".into()).unwrap());
        assert!(has_poor_address_structure("Main Market, MG Road".into()).unwrap());
        assert!(!has_poor_address_structure("Flat 12, Main Market".into()).unwrap());
        assert!(!has_poor_address_structure("Plot No 45 Section B".into()).unwrap());
    }
}
