pub fn calculate_trust_score(delivered: i32, total: i32) -> f64 {
    if total == 0 { return 50.0; }
    (delivered as f64 / total as f64) * 100.0
}

pub fn is_suspicious_name(name: &str) -> bool {
    if name.is_empty() { return false; }
    let trimmed = name.trim();
    if trimmed.len() <= 1 { return true; }
    let lower = trimmed.to_lowercase();
    if lower == "test" || lower == "fake" || lower.starts_with("test ") || lower.starts_with("fake ") {
        return true;
    }
    let letters: String = trimmed.chars().filter(|c| c.is_ascii_alphabetic()).collect();
    if letters.len() < trimmed.chars().filter(|c| !c.is_whitespace()).count() {
        return true; 
    }
    let vowels = letters.chars().filter(|c| matches!(c.to_ascii_lowercase(), 'a' | 'e' | 'i' | 'o' | 'u')).count();
    let consonants = letters.len() - vowels;
    vowels == 0 && consonants >= 4
}

pub fn is_suspicious_phone(phone: &str) -> bool {
    let mut cleaned = phone.replace("+91", "").replace("-", "").replace(" ", "");
    if cleaned.starts_with('0') && cleaned.len() > 10 {
        cleaned.remove(0);
    }
    if cleaned.len() < 7 || cleaned.len() > 15 { return true; }
    if !cleaned.chars().all(|c| c.is_ascii_digit()) { return true; }
    if cleaned.chars().all(|c| c == cleaned.chars().next().unwrap()) { return true; }
    if cleaned.contains("123456") || cleaned.contains("098765") { return true; }
    false
}

pub fn is_email_name_mismatch(name: &str, email: &str) -> bool {
    if name.is_empty() || email.is_empty() || !email.contains('@') { return false; }
    let local_part = email.split('@').next().unwrap_or("").to_lowercase();
    if local_part.is_empty() { return false; }
    let name_lower = name.to_lowercase();
    let name_parts: Vec<&str> = name_lower.split_whitespace().filter(|p| p.len() > 2).collect();
    if name_parts.is_empty() { return false; }
    !name_parts.iter().any(|part| local_part.contains(part))
}

pub fn evaluate_identity_cluster(
    shared_address_count: i32,
    shared_pin_count: i32,
    shared_subnet_count: i32,
) -> (bool, f64) {
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
    (final_score >= 30.0, final_score)
}
