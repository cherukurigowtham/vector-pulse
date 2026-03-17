use std::collections::HashSet;

pub const GENERIC_ADDRESS_TOKENS: &[&str] = &[
    "address", "area", "building", "city", "country", "district", "door", "floor", "house", "india",
    "lane", "layout", "locality", "near", "number", "opp", "opposite", "phase", "plot", "post",
    "road", "sector", "state", "street", "tower", "unit",
];

pub const LOW_SIGNAL_TOKENS: &[&str] = &[
    "and", "at", "beside", "by", "front", "in", "inside", "landmark", "mr", "mrs", "ms", "na",
    "nil", "nr", "of", "on", "the", "to",
];

pub fn canonical_token(token: &str) -> Option<String> {
    if token.is_empty() { return None; }
    if LOW_SIGNAL_TOKENS.contains(&token) { return None; }

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
        if mapped.len() >= 10 { return None; }
        if mapped.len() == 6 { return Some(format!("pin{}", mapped)); }
        return Some(mapped.to_string());
    }

    if mapped.len() == 1 && !mapped.chars().all(|ch| ch.is_ascii_digit()) {
        return None;
    }

    Some(mapped.to_string())
}

pub fn tokenize_address(addr: &str) -> Vec<String> {
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

pub fn signal_tokens(tokens: &[String]) -> Vec<String> {
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

pub fn jaccard_similarity(left: &str, right: &str) -> f64 {
    let left_tokens: HashSet<String> = signal_tokens(&tokenize_address(left)).into_iter().collect();
    let right_tokens: HashSet<String> = signal_tokens(&tokenize_address(right)).into_iter().collect();

    if left_tokens.is_empty() || right_tokens.is_empty() { return 0.0; }

    let intersection = left_tokens.intersection(&right_tokens).count() as f64;
    let union = left_tokens.union(&right_tokens).count() as f64;
    ((intersection / union) * 100.0).clamp(0.0, 100.0)
}

pub fn is_gibberish(addr: &str) -> bool {
    if addr.is_empty() { return false; }
    
    let letters: String = addr.chars()
        .filter(|c| c.is_ascii_alphabetic())
        .map(|c| c.to_ascii_lowercase())
        .collect();

    if letters.len() < 5 { return false; }
    
    let vowels = letters.chars().filter(|c| matches!(*c, 'a' | 'e' | 'i' | 'o' | 'u')).count();
    let consonants = letters.len() - vowels;
    
    if vowels == 0 && consonants >= 5 { return true; }
    if (vowels as f64) / (letters.len() as f64) > 0.8 && letters.len() > 5 { return true; }

    let mut max_repeat = 1;
    let mut current_repeat = 1;
    let mut last_char = ' ';
    
    for c in letters.chars() {
        if c == last_char {
            current_repeat += 1;
            max_repeat = max_repeat.max(current_repeat);
        } else {
            current_repeat = 1;
            last_char = c;
        }
    }
    
    max_repeat >= 4
}

pub fn has_poor_structure(address: &str) -> bool {
    if address.is_empty() { return true; }
    !address.chars().any(|c| c.is_ascii_digit())
}
